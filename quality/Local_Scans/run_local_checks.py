"""Native cross-platform Local Quality Gate entry point."""
import argparse
from datetime import datetime, timezone
import getpass
import json
import hashlib
import os
from pathlib import Path
import subprocess  # nosec B404 - explicit argument vectors or test doubles
import sys
import zipfile

from quality.Local_Scans.reporting.report_execution import execute_report
from quality.project_config import load
from quality.project_discovery import discover_java
from quality.Local_Scans.checks.java_native import run
from quality.Local_Scans.java_modules import run_modules
from quality.Local_Scans.local_pipeline import integrate
from quality.Local_Scans.local_normalize import scanner_result_status
from quality.Local_Scans.scanner_registry import LOCAL_SCANNER_NAMES


def safe_path(path):
    """Reject symlinks and Windows reparse points in existing ancestors."""
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("Unsafe local quality report output directory")
        if part.exists() and getattr(part.lstat(), "st_file_attributes", 0) & 0x400:
            raise ValueError("Unsafe local quality report output directory")
    return path.resolve()


def output_root(repo):
    """Resolve and validate the external report output directory."""
    downloads = safe_path(Path.home() / "Downloads")
    identity = hashlib.sha256(os.path.normcase(str(repo.resolve())).encode()).hexdigest()[:12]
    default = downloads / "quality-gates-reports" / (repo.name + "-" + identity)
    output = safe_path(Path(os.environ.get("QUALITY_OUTPUT_DIR") or default).absolute())
    if (
        output == downloads
            or not output.is_relative_to(downloads)
                or output.is_relative_to(repo) or repo.is_relative_to(output)
    ):
        raise ValueError("Unsafe local quality report output directory")
    return output


def package(work, archive):
    """Package validated scanner reports into a new archive."""
    names = ("local-report.html", "normalized.json")
    def checked(name):
        path = work / name
        if safe_path(path) != path.absolute() or not path.is_file():
            raise ValueError("Missing or unsafe report artifact")
        return path
    artifacts = {name: checked(name) for name in names}
    document = json.loads(artifacts["normalized.json"].read_text(encoding="utf-8"))
    results = document["results"]
    if len(results) != len(LOCAL_SCANNER_NAMES) or {r["tool"]
        for r in results} != set(LOCAL_SCANNER_NAMES):
        raise ValueError("Missing or duplicate scanner results")
    entries = {f"scanner-reports/{r['tool']}.json": json.dumps(r, indent=2) for r in results}
    entries["diagnostics/scanner-status.json"] = (
        json.dumps({r["tool"]: {"status": scanner_result_status(r),
            "execution_status": r.get("metadata", {}).get("status", "unknown"),
                "runtime_error": r.get("runtime_error"),
                    "violation_count": r.get("violation_count")} for r in results}, indent=2)
    )
    for name in ("checkstyle.xml", "pmd.xml", "spotbugs.xml", "spotbugs-classpath.txt",
        "spotbugs-unfiltered-baseline.xml"):
        path = work / name
        if path.exists() or path.is_symlink():
            artifacts["diagnostics/" + name] = checked(name)
    created = False
    try:
        with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as bundle:
            created = True
            for name, path in artifacts.items():
                bundle.write(path, name)
            for name, content in entries.items():
                bundle.writestr(name, content)
        with zipfile.ZipFile(archive) as bundle:
            if (
                bundle.testzip() is not None
                    or set(bundle.namelist()) != set(artifacts) | set(entries)
            ):
                raise ValueError("ZIP integrity failure")
    except BaseException:
        if created:
            archive.unlink(missing_ok=True)
        raise


def scanner_exit_code(document):
    """Advisory findings do not block; execution errors are not success."""
    return 2 if any(scanner_result_status(result) == "error"
                    for result in document["results"]) else 0


def _configure_project(repo):
    """Load project configuration and initialize the scanner environment."""
    config = Path(
        os.environ.get("QUALITY_CONFIG")
        or repo / "quality/project.json"
    )

    if config.is_file():
        try:
            data = load(repo, config)

        except (OSError, ValueError, TypeError):
            raise ValueError(
                "Unable to load Quality Gates project configuration."
            ) from None

        fields = {
            "JAVA_SOURCE": "java_source",
            "MAVEN_DIR": "maven_project",
            "SCAN_ROOT": "scan_root",
            "PYTHON_SOURCE": "python_source",
            "JS_SOURCE": "javascript_source",
            "PROJECT_NAME": "project_name",
            "JAVA_VERSION": "java_version",
        }

        for key, field in fields.items():
            os.environ["QUALITY_" + key] = data[field]

    os.environ.update(
        QUALITY_CONFIG=str(config),
        GITHUB_WORKSPACE=str(repo),
        PYTHONPATH=(
            str(repo)
            + os.pathsep
            + os.environ.get("PYTHONPATH", "")
        ),
    )


def _initialize_session(repo, output):
    """Create an isolated scan session and validate tool directory paths."""
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S-%f")

    session = output / ("run-" + stamp)
    work = session / "work"

    safe_path(session)
    work.mkdir(parents=True, exist_ok=False)
    safe_path(work)

    identity = hashlib.sha256(str(repo).encode()).hexdigest()[:12]
    tools = output / ("tools-" + identity)

    if not safe_path(tools).is_relative_to(output):
        raise ValueError("Unsafe tools directory")

    archive = output / ("local-quality-report-" + stamp + ".zip")

    return session, work, tools, archive


def _run_java_scanners(repo, work, tools):
    """Execute Java scanners using explicit or discovered Maven modules."""
    names = ("checkstyle", "pmd", "spotbugs")

    if (
        os.environ.get("QUALITY_JAVA_SOURCE")
        or os.environ.get("QUALITY_MAVEN_DIR")
    ):
        results = {
            name: {0: "passed", 1: "failed", 2: "error"}[
                run(name, repo, work, tools)
            ]
            for name in names
        }

    else:
        layout = discover_java(repo)

        if layout.unsupported_java:
            results = dict.fromkeys(names, "error")

        elif not layout.candidates:
            results = dict.fromkeys(names, "skipped")

        else:
            results = run_modules(
                repo,
                work,
                tools,
                layout.candidates,
            )

    statuses = {
        "CS_STATUS": results["checkstyle"],
        "PMD_STATUS": results["pmd"],
        "SB_STATUS": results["spotbugs"],
    }

    return statuses


def _generate_report(repo, work, statuses):
    """Initialize report metadata and generate the consolidated HTML report."""
    os.environ.update(
        statuses,
        WORK_DIR=str(work),
        REPO_ROOT=str(repo),
        GENERATED_AT=datetime.now(timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        ),
        SCAN_USER=getpass.getuser(),
        FAILED=str(list(statuses.values()).count("failed")),
    )

    execute_report(repo, os.environ.copy(), statuses)


def main(argv=None):
    """Run the Local Quality Gate command-line entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[2]

    try:
        output = output_root(repo)

        _configure_project(repo)

        session, work, tools, archive = _initialize_session(
            repo,
            output,
        )

        statuses = _run_java_scanners(repo, work, tools)

        document = integrate(
            repo,
            work,
            session,
            tools,
            statuses,
        )

        if (
            {result["tool"] for result in document["results"]}
            != set(LOCAL_SCANNER_NAMES)
            or len(document["results"]) != len(LOCAL_SCANNER_NAMES)
        ):
            raise ValueError("Missing scanner records")

        _generate_report(repo, work, statuses)

        package(work, archive)

        if not args.no_browser:
            subprocess.run(  # nosec B603
                [
                    sys.executable,
                    "-m",
                    "quality.Local_Scans.reporting.open_report",
                ],
                cwd=repo,
                check=False,
                timeout=30,
            )

        print("Report saved to:", archive)

        return scanner_exit_code(document)

    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
