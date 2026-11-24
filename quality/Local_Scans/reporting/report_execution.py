"""Shared subprocess execution for local quality report generation."""

import subprocess  # nosec B404 - fixed interpreter invocation
import sys
from pathlib import Path


def execute_report(
    cwd: Path,
    env: dict[str, str],
    statuses: dict[str, str],
) -> None:
    """Generate the local report using the supplied execution environment."""
    report_env = env.copy()
    report_env.update(statuses)
    report_env["FAILED"] = str(
        list(statuses.values()).count("failed")
    )

    subprocess.run(  # nosec B603
        [
            sys.executable,
            "-m",
            "quality.Local_Scans.reporting.generate_report",
        ],
        cwd=cwd,
        env=report_env,
        check=True,
        timeout=120,
    )
