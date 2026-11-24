
"""Normalize Local Quality Gate scanner results using existing CI parsers."""

import json
from datetime import datetime, timezone
from pathlib import Path

from quality.shared.scanner_status import scanner_is_disabled
from quality.shared.severity import aggregate_severity_counts

from quality.CI.gate.scanner_status import apply_scanner_status
from quality.CI.gate.schemas import base_tool_result
from quality.CI.gate.utils import (
    SEVERITY_ORDER,
    determine_max_severity,
)
from quality.Local_Scans.scanner_registry import LOCAL_SCANNERS


def normalize_local(raw_dir: Path, output_file: Path) -> dict:
    """Collect ten scanner results without enforcing CI policy."""
    raw_dir = Path(raw_dir)
    output_file = Path(output_file)

    results = []

    for scanner in LOCAL_SCANNERS:
        name = scanner["name"]
        parser = scanner["parser"]

        try:
            status_file = raw_dir / f"{name}.status.json"
            disabled = scanner_is_disabled(status_file)

            if disabled:
                result = base_tool_result(name)

                if (raw_dir / scanner["artifact"]).exists():
                    result["artifact_present"] = True
            else:
                result = parser(raw_dir)

            result = apply_scanner_status(
                name,
                result,
                raw_dir,
            )

        except Exception:  # pylint: disable=broad-except
            result = base_tool_result(name)
            result["runtime_error"] = True
            result["metadata"]["status"] = "failed"
            result["metadata"]["error"] = (
                "Local scanner normalization failed."
            )

        result["result_status"] = scanner_result_status(result)
        results.append(result)

    severity_counts = aggregate_severity_counts(results, SEVERITY_ORDER)

    document = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "advisory",
        "tool_count": len(results),
        "total_violations": sum(
            result["violation_count"] for result in results
        ),
        "severity_counts": severity_counts,
        "max_severity": determine_max_severity(severity_counts),
        "scanner_errors": sum(
            bool(result["runtime_error"]) for result in results
        ),
        "results": results,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(
        json.dumps(document, indent=2),
        encoding="utf-8",
    )

    return document


def summarize_local(document: dict) -> None:
    """Print advisory results without exposing raw scanner findings."""
    print()
    print("Local Quality Gate — Advisory Results")
    print("------------------------------------------")

    for result in document["results"]:
        name = result["tool"]
        status = scanner_result_status(result)
        count = result.get("violation_count", 0)

        reason = result.get("metadata", {}).get("reason")
        detail = f" — {reason}" if status in {"skipped", "disabled"} and reason else ""
        print(f"{name:14} {status:10} {count} finding(s){detail}")

    print("------------------------------------------")
    print(f"Total findings: {document['total_violations']}")
    print(f"Scanner errors: {document['scanner_errors']}")
    print("Mode: ADVISORY — findings do not block commits.")


def format_scanner_outcome(result: dict) -> str:
    """Format a scanner result from normalized status and finding count."""
    name = result["tool"]
    display = {
        "pylint": "Pylint", "bandit": "Bandit",
        "htmlhint": "HTMLHint", "stylelint": "Stylelint",
        "gitleaks": "Gitleaks", "trufflehog": "TruffleHog", "trivy": "Trivy",
    }.get(name, name)
    status = scanner_result_status(result)
    count = result.get("violation_count", 0)
    if status == "error":
        return f"{display}: error (scanner failed)."
    if status in ("disabled", "skipped"):
        reason = result.get("metadata", {}).get("reason")
        return f"{display}: {status}." + (f" {reason}" if reason else "")
    if status == "failed":
        return f"{display} completed. {count} findings detected."
    return f"{display} passed. No findings found."


def scanner_result_status(result: dict) -> str:
    """Classify normalized execution independently of coverage and policy."""
    metadata = result.get("metadata", {})
    status = metadata.get("status")

    if result.get("runtime_error"):
        return "error"

    if status == "disabled":
        if result.get("executed") or result.get("artifact_present"):
            return "error"

        skipped_reasons = {
            "No applicable Java Maven project detected",
            "No eligible HTML files were found",
            "No eligible CSS or SCSS files were found",
            "No eligible Python files were found",
        }

        return "skipped" if metadata.get("reason") in skipped_reasons else "disabled"

    if (
        status != "completed"
        or not result.get("executed")
        or not result.get("artifact_present")
    ):
        return "error"

    count = result.get("violation_count")

    if not isinstance(count, int) or count.__class__ is not int or count < 0:
        return "error"

    return "failed" if count else "passed"
