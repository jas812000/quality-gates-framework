"""Run platform acceptance, retaining sanitized evidence in Downloads."""
import os
import shutil
import time
from pathlib import Path
import subprocess  # nosec B404 - explicit argument vectors or test doubles
import sys
from datetime import datetime


def resolve_command(argv):
    """Resolve PATH executables, including Windows command wrappers."""
    executable = shutil.which(argv[0])
    return [executable or argv[0], *argv[1:]]


def main():
    """Run the platform acceptance command-line entry point."""
    root = Path(__file__).resolve().parents[2]
    downloads = Path.home() / "Downloads"
    downloads.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        stamp = os.environ["GITHUB_RUN_ID"] + "-" + os.environ["GITHUB_RUN_ATTEMPT"]
        if not all(part.isdecimal() for part in stamp.split("-")):
            raise ValueError("Invalid run identifier")
    report = downloads / ("qg-platform-" + stamp + ".txt")
    checks = [(name, [name, *args]) for name, args in (
        ("java", ["-version"]), ("mvn", ["--version"]),
        ("node", ["--version"]), ("npm", ["--version"]),
        ("gitleaks", ["version"]), ("trivy", ["--version"]),
        ("trufflehog", ["--version"]) if shutil.which("trufflehog") else
        ("docker", ["info", "--format", "{{.OSType}}"]),
    )]
    for suite in ("shared", "CI", "Local_Scans"):
        checks.append((suite, [sys.executable, "-m", "unittest", "discover", "-s",
            f"quality/{suite}/tests", "-p", "test_*.py", "-q"]))
    checks.append(("launcher", ["cmd.exe", "/d", "/c",
        "quality\\Local_Scans\\run-local-checks.bat", "--help"] if os.name == "nt" else ["sh",
            "quality/Local_Scans/run-local-checks.sh", "--help"]))
    checks.append(("acceptance", [sys.executable, "-m", "quality.Local_Scans.acceptance",
        "--report", str(report.with_suffix(".json"))]))
    failed = 0
    with report.open("x", encoding="utf-8") as stream:
        for name, argv in checks:
            started = time.monotonic()
            try:
                # fixed command arguments
                result = subprocess.run(  # nosec B603
                    resolve_command(argv), cwd=root, capture_output=True,
                    text=True, errors="replace", timeout=3600 if name == "acceptance" else 600,
                        check=False)
                passed = result.returncode == 0 and (name != "docker"
                    or result.stdout.strip() == "linux")
                # Never persist arbitrary scanner output, which may contain secrets.
                stream.write(f"{name}: exit={result.returncode}\n")
            except (OSError, subprocess.TimeoutExpired) as exc:
                passed = False
                stream.write(f"{name}: {type(exc).__name__}\n")
            print(name, "PASS" if passed else "FAIL", flush=True)
            stream.write(f"{name}: {'PASS' if passed else 'FAIL'}\n")
            stream.write(f"{name}: duration_seconds={time.monotonic() - started:.2f}\n")
            stream.flush()
            failed += not passed
    print("Report:", report)
    return int(bool(failed))


if __name__ == "__main__":
    sys.exit(main())
