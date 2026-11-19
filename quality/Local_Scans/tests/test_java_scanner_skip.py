"""Java scanner staging preserves non-applicable status."""
import json
import tempfile
import unittest
from pathlib import Path
from quality.Local_Scans.local_pipeline import _stage_java_results


class JavaScannerSkipTests(unittest.TestCase):
    def test_no_java_marks_all_three_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / "stage"
            stage.mkdir()
            _stage_java_results(root, stage, {
                "CS_STATUS": "skipped",
                "PMD_STATUS": "skipped",
                "SB_STATUS": "skipped",
            })
            for name in ("checkstyle", "pmd", "spotbugs"):
                record = json.loads((stage / f"{name}.status.json").read_text())
                self.assertEqual(record["status"], "disabled")
