"""Run Stylelint using the shared CI configuration."""

import json
import shutil
import subprocess  # nosec B404
from pathlib import Path

from quality.Local_Scans.checks.scanner_runner import write_status
from quality.Local_Scans.checks.scan_files import eligible_files


def _install_stylelint(tools):
    """Install Stylelint and its standard configuration."""
    try:
        npm = shutil.which("npm")

        if npm is None:
            raise OSError("npm executable unavailable")

        result = subprocess.run(  # nosec B603
            [
                npm,
                "install",
                "--prefix", str(tools),
                "--no-save",
                "--no-audit",
                "--no-fund",
                "stylelint",
                "stylelint-config-standard",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=900,
        )

        return result.returncode == 0

    except (OSError, subprocess.SubprocessError):
        return False


def _write_config(config):
    """Write the shared Stylelint configuration."""
    config.write_text(
        "module.exports = { "
        "extends: ['stylelint-config-standard'] "
        "};\n",
        encoding="utf-8",
    )


def _valid_report(data):
    """Validate the structure and integrity of a Stylelint report."""
    return (
        isinstance(data, list)
        and all(
            isinstance(item, dict)
            and isinstance(item.get("warnings"), list)
            and not item.get("parseErrors")
            and not item.get("invalidOptionWarnings")
            and not item.get("deprecations")
            for item in data
        )
    )


def _execute_scan(executable, files, config, output):
    """Execute Stylelint using an explicit JSON output file."""
    node = shutil.which("node")

    if not node:
        raise OSError("Node unavailable")

    return subprocess.run(  # nosec B603
        [
            node,
            str(executable),
            *files,
            "--config", str(config),
            "--formatter", "json",
            "--output-file", str(output),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=900,
    )


def _scan_and_record(work, executable, files, config):
    """Execute the scanner and record its validated outcome."""
    output = work / "stylelint.json"
    output.unlink(missing_ok=True)

    try:
        completed = _execute_scan(
            executable,
            files,
            config,
            output,
        )

        if completed.returncode in {0, 2} and _valid_report(
            json.loads(output.read_text(encoding="utf-8"))
        ):
            write_status(
                work,
                "stylelint",
                "completed",
                completed.returncode,
            )
            return

        reason = "Stylelint exit code or report validation failed"
        code = completed.returncode

    except (OSError, ValueError, TypeError, subprocess.SubprocessError):
        reason = "Stylelint execution or report read failed"
        code = None

    output.unlink(missing_ok=True)
    write_status(work, "stylelint", "failed", code, reason)


def run(repo_root, work_dir, tools_dir):
    """Scan CSS and SCSS files with Stylelint."""
    root = Path(repo_root).resolve()
    work = Path(work_dir).resolve()
    tools = Path(tools_dir).resolve() / "stylelint"

    work.mkdir(parents=True, exist_ok=True)

    files = eligible_files(root, {".css", ".scss"})

    if not files:
        (work / "stylelint.json").unlink(missing_ok=True)

        write_status(
            work,
            "stylelint",
            "disabled",
            reason="No eligible CSS or SCSS files were found",
        )
        return

    tools.mkdir(parents=True, exist_ok=True)

    executable = (
        tools / "node_modules" / "stylelint" / "bin" / "stylelint.mjs"
    )
    config = tools / "stylelint.config.cjs"

    if not executable.is_file() and not _install_stylelint(tools):
        write_status(
            work,
            "stylelint",
            "failed",
            reason="Stylelint installation failed",
        )
        return

    _write_config(config)
    _scan_and_record(work, executable, files, config)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 4:
        raise SystemExit(
            "Usage: python -m "
            "quality.Local_Scans.checks.check_stylelint "
            "REPO_ROOT WORK_DIR TOOLS_DIR"
        )

    run(sys.argv[1], sys.argv[2], sys.argv[3])
