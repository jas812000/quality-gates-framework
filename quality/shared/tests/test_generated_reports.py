"""Regression tests for generated report validation."""
import json
from pathlib import Path
import tempfile
import unittest

from quality.shared.reporting.validate_generated import ReportCSS, render_reports, scanner_outcome


class GeneratedReportTests(unittest.TestCase):
    """Verify rendering, CSS extraction and fail-closed scanner outcomes."""

    def test_renderers(self):
        """All three report variants contain complete HTML and CSS."""
        reports = render_reports()
        self.assertEqual(set(reports), {"local", "ci-summary", "ci-diagnostic"})
        for html in reports.values():
            self.assertTrue(html.startswith("<!DOCTYPE html>"))
            self.assertTrue(html.endswith("</html>"))
            parser = ReportCSS()
            parser.feed(html)
            self.assertIn("box-sizing", parser.stylesheet())
        self.assertNotIn("Synthetic finding", reports["ci-summary"])
        self.assertIn("Synthetic finding", reports["local"])

    def test_inline_css(self):
        """Include inline declarations in extracted CSS."""
        parser = ReportCSS()
        parser.feed('<style>a { color: red; }</style><p style="color: blue;">x</p>')
        self.assertIn(".inline-1 {\ncolor: blue;\n}", parser.stylesheet())

    def test_missing_css(self):
        """Missing styles are not silently accepted."""
        with self.assertRaises(ValueError):
            ReportCSS().stylesheet()

    def test_outcomes(self):
        """Missing, skipped and malformed reports fail closed."""
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            status = work / "htmlhint.status.json"
            report = work / "htmlhint.json"
            self.assertEqual(scanner_outcome(work, "htmlhint"), ("ERROR", 0))
            status.write_text(json.dumps({"status": "disabled"}), encoding="utf-8")
            self.assertEqual(scanner_outcome(work, "htmlhint"), ("ERROR", 0))
            status.write_text(json.dumps({"status": "completed"}), encoding="utf-8")
            for data, expected in (([], ("PASS", 0)), ([{"messages": [{}]}], ("FAIL", 1)),
                                   ([{}], ("ERROR", 0))):
                report.write_text(json.dumps(data), encoding="utf-8")
                self.assertEqual(scanner_outcome(work, "htmlhint"), expected)
