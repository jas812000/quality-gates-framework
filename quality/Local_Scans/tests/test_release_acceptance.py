"""Negative execution and report isolation acceptance tests."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import subprocess  # nosec B404 - explicit argument vectors or test doubles
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from quality.Local_Scans.checks.scanner_runner import ScannerValidation, run_json_scanner
from quality.Local_Scans.local_normalize import normalize_local, format_scanner_outcome
from quality.Local_Scans.tests.report_fixture import write_report_fixture
from quality.Local_Scans.run_local_checks import package




class ReleaseAcceptanceTests(unittest.TestCase):
    """Regression coverage for release acceptance."""
    def test_execution_failures_never_report_clean(self):
        """Verify execution failures never report clean."""
        cases = [(0, "invalid"), (0, ""), (9, "[]"), (0, "{}"),
                 FileNotFoundError(), subprocess.TimeoutExpired("fixture", 1)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for case in cases:
                with self.subTest(case=case):
                    def execute(command, output, case=case, **_kwargs):
                        if isinstance(case, Exception):
                            raise case
                        code, text = case
                        output.write_text(text, encoding="utf-8")
                        return subprocess.CompletedProcess(command, code)
                    (root / "pylint.json").write_text("[]", encoding="utf-8")
                    with patch("quality.Local_Scans.checks.scanner_runner.run_scanner_to_file",
                        side_effect=execute):
                        self.assertFalse(run_json_scanner("pylint", ["fixture"], root,
                            "pylint.json", ScannerValidation({0}, lambda data: isinstance(data,
                                list))))
                    self.assertFalse((root / "pylint.json").exists())
                    self.assertEqual(
                        json.loads((root / "pylint.status.json").read_text())["status"],
                        "failed",
                    )
                    result = next(r for r in normalize_local(root,
                        root / "normalized.json")["results"] if r["tool"] == "pylint")
                    self.assertTrue(result["runtime_error"])
                    self.assertIn("error", format_scanner_outcome(result))

    def test_parallel_archives_do_not_overwrite(self):
        """Verify parallel archives do not overwrite."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in ("local-report.html", "normalized.json"):
                (root / name).write_text("fixture", encoding="utf-8")
            write_report_fixture(root)
            archive = root / "out.zip"
            def attempt(_):
                try:
                    package(root, archive)
                    return True
                except FileExistsError:
                    return False
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sorted(pool.map(attempt, range(2))), [False, True])
            with zipfile.ZipFile(archive) as bundle:
                self.assertIsNone(bundle.testzip())

    def test_trivy_unknown_coverage_passes(self):
        """Verify trivy unknown coverage passes."""
        result = {"tool": "trivy", "metadata": {"status": "completed"}, "violation_count": 0,
            "executed": True, "artifact_present": True}
        self.assertIn("passed", format_scanner_outcome(result))
