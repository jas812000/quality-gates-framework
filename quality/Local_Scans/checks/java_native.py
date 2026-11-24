"""Portable Java scanner execution using Java and Maven directly."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess  # nosec B404 - explicit argument vectors or test doubles
import tarfile
import tempfile
import urllib.request
from urllib.parse import urlsplit
import zipfile
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException


def download(path, url, checksum=None):
    """Download a validated release asset and verify its checksum when supplied."""
    if urlsplit(url).scheme != "https" or urlsplit(url).hostname != "github.com":
        raise ValueError("Unapproved scanner download URL")
    if not path.exists():
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temp = Path(stream.name)
            try:
                # HTTPS GitHub release URL validated
                with urllib.request.urlopen(url, timeout=120) as response:  # nosec B310
                    if urlsplit(response.geturl()).scheme != "https":
                        raise ValueError("Insecure download redirect")
                    shutil.copyfileobj(response, stream)
            except BaseException:
                stream.close()
                temp.unlink(missing_ok=True)
                raise
        temp.replace(path)
    if checksum and hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
        raise ValueError("Scanner checksum mismatch")


def extract(archive, tools):
    # Only regular files and directories; reject links and traversal.
    """Extract a tool archive while enforcing safe member paths."""
    with (zipfile.ZipFile(archive)
        if archive.suffix == ".zip" else tarfile.open(archive)) as bundle:
        if isinstance(bundle, zipfile.ZipFile):
            members = bundle.infolist()
        elif isinstance(bundle, tarfile.TarFile):
            members = bundle.getmembers()
        else:
            raise TypeError("Unsupported archive type")
        for member in members:
            name = member.filename if isinstance(member, zipfile.ZipInfo) else member.name
            target = tools / name
            if not target.resolve().is_relative_to(tools.resolve()) or target.is_symlink():
                raise ValueError("Unsafe scanner archive path")
            if isinstance(member, zipfile.ZipInfo):
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("Archive contains symbolic link")
            elif not (member.isfile() or member.isdir()):
                raise ValueError("Unsupported archive member")
        bundle.extractall(tools)


def execute(argv, cwd=None):
    """Run a resolved command with a bounded execution time."""
    # resolved Java/Maven argv, no shell
    return subprocess.run(  # nosec B603
        [str(x) for x in argv], cwd=cwd, check=False,
        timeout=900).returncode


def maven_command(module):
    # Windows uses the installed Maven command shim; POSIX preserves wrapper preference.
    """Resolve the Maven executable for the current platform."""
    wrapper = module / ("mvnw.cmd" if os.name == "nt" else "mvnw")
    executable = str(wrapper) if wrapper.is_file() else shutil.which("mvn")
    if not executable:
        raise OSError("Maven unavailable")
    return [executable]


def _run_checkstyle(java, source, config, tools, out):
    """Execute Checkstyle against Java source files."""
    jar = tools / "checkstyle-14.4.0-all.jar"

    download(
        jar,
        "https://github.com/checkstyle/checkstyle/releases/download/"
        "checkstyle-14.4.0/" + jar.name,
        "c0a521e54eabd1ece4ff7bd84cf231b012615745ed3aa4fb27ab0ca73097250c",
    )

    if not any(source.rglob("*.java")):
        raise ValueError("No Java sources")

    return execute([
        java,
        "-jar", jar,
        "-c", config / "checkstyle.xml",
        "-f", "xml",
        "-o", out,
        source,
    ])


def _run_pmd(java, source, config, tools, out):
    """Execute PMD against Java source files."""
    archive = tools / "pmd-dist-7.29.0-bin.zip"
    folder = tools / "pmd-bin-7.29.0"

    download(
        archive,
        "https://github.com/pmd/pmd/releases/download/"
        "pmd_releases%2F7.29.0/" + archive.name,
        "d27177c185b837fa57f097e482d1253468aa035379c5eb2671fa0a279109b179",
    )
    if not (folder / "lib").is_dir():
        extract(archive, tools)

    return execute([
        java,
        "-cp", folder / "lib/*",
        "net.sourceforge.pmd.cli.PmdCli",
        "check",
        "--dir", source,
        "--rulesets", config / "pmd-ruleset.xml",
        "--format", "xml",
        "--report-file", out,
    ])


def _prepare_spotbugs_classes(module, work):
    """Compile Java classes and generate the dependency classpath."""
    maven = maven_command(module)
    classpath_file = work / "spotbugs-classpath.txt"
    classpath_file.unlink(missing_ok=True)

    if execute(
        maven + ["--batch-mode", "-q", "-DskipTests", "compile"],
        module,
    ):
        raise ValueError("Maven compilation failed")

    classes = module / "target/classes"

    if not any(classes.rglob("*.class")):
        raise ValueError("No compiled classes")

    if execute(
        maven + [
            "--batch-mode",
            "-q",
            "dependency:build-classpath",
            "-Dmdep.outputFile=" + str(classpath_file),
        ],
        module,
    ) or not classpath_file.is_file():
        raise ValueError("Maven classpath failed")

    return classes, classpath_file.read_text().strip()


def _run_spotbugs(java, module, work, tools, out):
    """Execute SpotBugs against compiled Java classes."""
    archive = tools / "spotbugs-4.10.5.tgz"
    folder = tools / "spotbugs-4.10.5"

    if not (folder / "lib/spotbugs.jar").is_file():
        download(
            archive,
            "https://github.com/spotbugs/spotbugs/releases/download/"
            "4.10.5/" + archive.name,
            "cce3244900cc215ccd9f5a8db29ed9468fc47824faf662f4fad005343d96007e",
        )
        extract(archive, tools)

    classes, classpath = _prepare_spotbugs_classes(module, work)

    args = [
        java,
        "-jar", folder / "lib/spotbugs.jar",
        "-textui",
        "-exitcode",
        "-xml:withMessages",
        "-effort:max",
    ]

    if classpath:
        args += ["-auxclasspath", classpath]

    return execute(args + ["-output", out, classes])


def _validate_spotbugs(root, code):
    """Validate SpotBugs execution and analysis completeness."""
    errors = root.find("Errors")

    if (
        code not in (0, 1, 4)
        or errors is None
        or errors.get("errors") != "0"
        or errors.get("missingClasses") != "0"
    ):
        raise ValueError("SpotBugs analysis failed")


def _validate_result(scanner, out, code):
    """Validate scanner XML structure, findings and exit codes."""
    expected, finding = {
        "checkstyle": ("checkstyle", "error"),
        "pmd": ("pmd", "violation"),
        "spotbugs": ("BugCollection", "BugInstance"),
    }[scanner]

    root = ET.parse(out).getroot()

    if root.tag.rsplit("}", 1)[-1] != expected:
        raise ValueError("Invalid XML root")

    count = sum(
        element.tag.rsplit("}", 1)[-1] == finding
        for element in root.iter()
    )

    if scanner == "spotbugs":
        _validate_spotbugs(root, code)

    elif scanner == "pmd":
        if code != (4 if count else 0):
            raise ValueError("PMD execution mismatch")

    elif code != 0 and not count:
        raise ValueError("Checkstyle execution failed")

    return int(bool(count))


def run(scanner, repo, work, tools, env=None):
    """Execute the requested native Java scanner and validate its output."""
    env = os.environ if env is None else env

    work.mkdir(parents=True, exist_ok=True)
    tools.mkdir(parents=True, exist_ok=True)

    out = work / (scanner + ".xml")
    out.unlink(missing_ok=True)

    try:
        java = shutil.which("java")

        if not java:
            raise OSError("Java unavailable")

        source = Path(
            env.get("QUALITY_JAVA_SOURCE")
            or repo / "backend/src/main/java"
        )

        module = Path(
            env.get("QUALITY_MAVEN_DIR")
            or repo / "backend"
        )

        config = repo / "quality/Local_Scans/config"

        if scanner == "checkstyle":
            code = _run_checkstyle(java, source, config, tools, out)

        elif scanner == "pmd":
            code = _run_pmd(java, source, config, tools, out)

        elif scanner == "spotbugs":
            code = _run_spotbugs(java, module, work, tools, out)

        else:
            raise ValueError("Unknown scanner")

        return _validate_result(scanner, out, code)

    except (
        OSError,
        ValueError,
        ET.ParseError,
        DefusedXmlException,
        subprocess.SubprocessError,
        tarfile.TarError,
        zipfile.BadZipFile,
    ) as exc:
        out.unlink(missing_ok=True)
        print(f"ERROR: {scanner}: {exc}")
        return 2
