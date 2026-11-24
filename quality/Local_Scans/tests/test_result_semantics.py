"""Regression tests for result semantics."""
import unittest
from quality.Local_Scans.local_normalize import scanner_result_status
from quality.Local_Scans.scanner_registry import LOCAL_SCANNER_NAMES
from quality.Local_Scans.reporting.render_report.report_sections import _scanner_status


class ResultSemanticsTests(unittest.TestCase):
    """Regression coverage for result semantics."""
    def test_all_scanners(self):
        """Verify all scanners."""
        for tool in LOCAL_SCANNER_NAMES:
            base = dict(tool=tool, executed=True, artifact_present=True, runtime_error=False,
                        violation_count=0, metadata={"status": "completed",
                            "coverage": {"secret": "unknown"}})
            for overrides, expected in [({}, "passed"), ({"violation_count": 1}, "failed"),
                                        ({"runtime_error": True}, "error"),
                                            ({"artifact_present": False}, "error"),
                                        ({"executed": False}, "error"),
                                            ({"metadata": {"status": "failed"}}, "error"),
                                        ({"executed": False, "artifact_present": False,
                                            "metadata": {"status": "disabled"}}, "disabled"),
                                        ({"executed": False, "artifact_present": False,
                                            "metadata": {"status": "disabled",
                                                "reason": ("No applicable Java Maven "
                                                "project detected")}},
                                                "skipped")]:
                with self.subTest(tool=tool, expected=expected):
                    result = dict(base, **overrides)
                    self.assertEqual(scanner_result_status(result), expected)
                    self.assertEqual(_scanner_status(result), expected)

    def test_no_source_targets(self):
        """Distinguish absent source targets from intentional disabling."""
        for tool, reason in (
            ("htmlhint", "No eligible HTML files were found"),
            ("stylelint", "No eligible CSS or SCSS files were found"),
            ("pylint", "No eligible Python files were found"),
            ("bandit", "No eligible Python files were found"),
        ):
            with self.subTest(tool=tool):
                result = dict(tool=tool, executed=False, artifact_present=False,
                              runtime_error=False, violation_count=0,
                              metadata={"status": "disabled", "reason": reason})
                self.assertEqual(scanner_result_status(result), "skipped")
                self.assertEqual(_scanner_status(result), "skipped")
                result["artifact_present"] = True
                self.assertEqual(scanner_result_status(result), "error")
