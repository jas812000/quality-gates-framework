"""Shared normalized report fixture for archive regression tests."""
import json
from quality.Local_Scans.scanner_registry import LOCAL_SCANNER_NAMES


def write_report_fixture(root):
    """Create normalized scanner results for archive tests."""
    results = [{"tool": name, "metadata": {"status": "disabled"},
                "violation_count": 0} for name in LOCAL_SCANNER_NAMES]
    (root / "normalized.json").write_text(json.dumps({"results": results}), encoding="utf-8")
