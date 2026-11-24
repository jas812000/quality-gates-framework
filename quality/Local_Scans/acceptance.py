"""Real scanner acceptance using isolated synthetic projects, never production data."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess  # nosec B404 - fixed interpreter invocation
import sys
import tempfile
import zipfile

from quality.Local_Scans.reporting.report_execution import execute_report
from quality.Local_Scans.checks.java_native import run
from quality.Local_Scans.local_normalize import scanner_result_status
from quality.Local_Scans.local_pipeline import integrate
from quality.Local_Scans.run_local_checks import package
from quality.Local_Scans.scanner_registry import LOCAL_SCANNER_NAMES

SOURCE = Path(__file__).resolve().parents[2]
SECRET = "".join(map(chr, (65, 75, 73, 65, 81, 71, 84, 69, 83, 84, 55, 88, 52, 75, 57, 77, 50,
    80, 54, 90)))
# Synthetic, offline-only detector fixtures; never verify against a provider.
AWS_ID = "".join(map(chr, (65, 75, 73, 65, 55, 75, 51, 77, 57, 88, 50, 80, 54, 82, 52, 84, 56,
    86, 53, 87)))
AWS_KEY = "".join(map(chr, (97, 66, 55, 100, 69, 57, 102, 71, 50, 104, 74, 52, 107, 76, 54, 109,
    78, 56, 112, 81, 114, 83, 51, 116, 85, 53, 118, 87, 55, 120, 89, 57, 122, 65, 50, 98, 67,
        52, 100, 70)))
GITHUB_TOKEN = "".join(map(chr, (103, 104, 112, 95, 97, 66, 55, 100, 69, 57, 102, 71, 50, 104,
    74, 52, 107, 76, 54, 109, 78, 56, 112, 81, 114, 83, 51, 116, 85, 53, 118, 87, 55, 120, 89,
        57, 122, 65, 50, 98)))
SECRETS = (SECRET, AWS_ID, AWS_KEY, GITHUB_TOKEN)


def contains_secret(data):
    """Detect synthetic acceptance credentials in retained data."""
    return any(value.encode() in data for value in SECRETS)


def fixture(repo, clean=False):
    """Build a deliberately noncompliant, disposable Maven and web project."""
    shutil.copytree(SOURCE / "quality/Local_Scans/config", repo / "quality/Local_Scans/config")
    data = {
        "backend/pom.xml": (
            '<project xmlns="http://maven.apache.org/POM/4.0.'
            '0"><modelVersion>4.0.0</modelVersion><groupId>fi'
            'xture</groupId><artifactId>acceptance</artifactI'
            'd><version>1</version><properties><maven.compile'
            'r.source>17</maven.compiler.source><maven.compil'
            'er.target>17</maven.compiler.target></properties'
            '></project>'
        ),
        "backend/src/main/java/Fixture.java": (
            'public class Fixture {\n\tpublic boolean broken(St'
            'ring value) { return value.equals(value); }\n pub'
            'lic int unused() { int unused = 1; return 2; }\n}'
            '\n'
        ),
        "sample.py": 'import os\nimport subprocess\nsubprocess.call("echo fixture", shell=True)\n',
        ".pylintrc": '[MAIN]\n',
        "index.html": '<html><body><img src="x"><div id="x" id="y"></div></body></html>',
        "style.css": 'a { color: #zzzzzz; }\n',
        "detector_fixture.txt": (
            f"aws_access_key_id = {AWS_ID}\n"
            f"aws_secret_access_key = {AWS_KEY}\n"
            f"github_token = {GITHUB_TOKEN}\n"
        ),
        "Dockerfile": 'FROM alpine:3.18\nUSER root\n',
        "requirements.txt": 'urllib3==1.26.5\n',
        "credentials.env": 'AWS_ACCESS_KEY_ID=' + SECRET + '\n',
        "synthetic_credentials.py": 'aws_access_key_id = "' + SECRET + '"\n',
    }
    if clean:
        data = {
            "backend/pom.xml": data["backend/pom.xml"],
            "backend/src/main/java/fixture/Fixture.java": (
                'package fixture;\n\npublic class Fixture {\n    pub'
                'lic int value() {\n        return 1;\n    }\n}\n'
            ),
            "sample.py": (
                '"""Clean acceptance fixture."""\n\ndef value():\n  '
                '  """Return a constant."""\n    return 1\n'
            ),
            ".pylintrc": data[".pylintrc"],
            "index.html": (
                '<!DOCTYPE html>\n<html lang="en"><head><title>Fix'
                'ture</title></head><body><p>Fixture</p></body></'
                'html>\n'
            ),
            "style.css": "a {\n  color: #fff;\n}\n",
        }
    for name, text in data.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _validate_scanner_results(results, clean):
    """Validate scanner outcomes and Trivy coverage requirements."""
    checks = {}
    expected_status = "passed" if clean else "failed"

    for name in LOCAL_SCANNER_NAMES:
        result = results.get(name, {})
        checks[name] = bool(
            result
            and scanner_result_status(result) == expected_status
            and result.get("result_status") == scanner_result_status(result)
        )
        print(
            name,
            "PASS" if checks[name] else "FAIL",
            "findings:",
            result.get("violation_count", 0),
        )

    trivy = results.get("trivy", {})

    if clean:
        checks["trivy_clean_status"] = (
            scanner_result_status(trivy) == "passed"
            and "coverage" in trivy.get("metadata", {})
        )
    else:
        metadata = [
            finding.get("metadata", {})
            for finding in trivy.get("findings", [])
        ]
        checks["trivy_three_modes"] = (
            any(item.get("cve") for item in metadata)
            and {"Secrets", "Misconfigurations"}.issubset(
                {item.get("category") for item in metadata}
            )
        )

    return checks


def _validate_archive(archive, results):
    """Verify archive integrity, completeness and secret redaction."""
    required_files = {
        "local-report.html",
        "normalized.json",
        "diagnostics/scanner-status.json",
    } | {
        f"scanner-reports/{name}.json"
        for name in LOCAL_SCANNER_NAMES
    }

    with zipfile.ZipFile(archive) as bundle:
        return (
            bundle.testzip() is None
            and required_files.issubset(bundle.namelist())
            and all(
                json.loads(
                    bundle.read(f"scanner-reports/{name}.json")
                ) == results[name]
                for name in LOCAL_SCANNER_NAMES
            )
            and all(
                not contains_secret(bundle.read(name))
                for name in bundle.namelist()
            )
        )


def acceptance(base, clean=False):
    """Run all scanners against a positive or clean fixture."""
    repo, work, reports, tools = (
        base / name
        for name in ("repo", "work", "reports", "tools")
    )

    fixture(repo, clean=clean)
    work.mkdir()

    env = os.environ.copy()
    env.update(
        QUALITY_JAVA_SOURCE=str(repo / "backend/src/main/java"),
        QUALITY_MAVEN_DIR=str(repo / "backend"),
    )

    statuses = {
        key: {0: "passed", 1: "failed", 2: "error"}[
            run(name, repo, work, tools, env)
        ]
        for key, name in (
            ("CS_STATUS", "checkstyle"),
            ("PMD_STATUS", "pmd"),
            ("SB_STATUS", "spotbugs"),
        )
    }

    document = integrate(repo, work, reports, tools, statuses)
    results = {
        result["tool"]: result
        for result in document["results"]
    }

    checks = _validate_scanner_results(results, clean)

    env.update(
        WORK_DIR=str(work),
        REPO_ROOT=str(repo),
        GENERATED_AT="acceptance",
        SCAN_USER="fixture",
    )

    execute_report(SOURCE, env, statuses)

    archive = base / "report.zip"
    package(work, archive)

    checks["archive_security"] = _validate_archive(
        archive,
        results,
    )

    checks["retained_secret_security"] = all(
        not contains_secret(path.read_bytes())
        for folder in (work, reports)
        for path in folder.rglob("*")
        if path.is_file()
    )

    return checks


def retain_archive(source, destination):
    """Publish only validated, sanitized archives; never overwrite an export."""
    with zipfile.ZipFile(source) as bundle:
        if bundle.testzip() is not None or any(contains_secret(bundle.read(n))
            for n in bundle.namelist()):
            raise ValueError("Unsafe acceptance archive")
    created = False
    try:
        with destination.open("xb") as output:
            created = True
            with source.open("rb") as input_file:
                shutil.copyfileobj(input_file, output)
    except BaseException:
        if created:
            destination.unlink(missing_ok=True)
        raise
    print("Acceptance ZIP:", destination)


def main():
    """Run the acceptance command-line entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    downloads = (Path.home() / "Downloads").resolve()
    downloads.mkdir(exist_ok=True)
    report = args.report.resolve()
    if not report.is_relative_to(downloads):
        parser.error("Report must be under Downloads")
    checks = {}
    exports = {}
    try:
        with tempfile.TemporaryDirectory(prefix="qg-acceptance-", dir=downloads) as directory:
            base = Path(directory).resolve()
            checks = acceptance(base / "positive")
            if checks.get("archive_security") and checks.get("retained_secret_security"):
                destination = report.with_name(report.stem + "_positive.zip")
                retain_archive(base / "positive" / "report.zip", destination)
                exports["positive"] = str(destination)
            clean_checks = acceptance(base / "clean", clean=True)
            if (
                clean_checks.get("archive_security")
                    and clean_checks.get("retained_secret_security")
            ):
                destination = report.with_name(report.stem + "_clean.zip")
                retain_archive(base / "clean" / "report.zip", destination)
                exports["clean"] = str(destination)
            checks["acceptance_zip_exports"] = set(exports) == {"positive", "clean"}
            checks.update({"clean_" + key: value for key, value in clean_checks.items()})
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print("Acceptance infrastructure failure:", type(exc).__name__)
        checks["infrastructure"] = False
    report.write_text(json.dumps({"platform": sys.platform, "checks": checks,
        "archives": exports}, indent=2), encoding="utf-8")
    for name, passed in checks.items():
        print(name, "PASS" if passed else "FAIL")
    return 0 if checks and all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
