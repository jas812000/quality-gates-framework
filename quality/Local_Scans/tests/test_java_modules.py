"""Multi-module scanner orchestration without downloading scanner tools."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from defusedxml import ElementTree as ET

from quality.Local_Scans.java_modules import merge_reports, run_modules


class MultiModuleTests(unittest.TestCase):
    """Regression coverage for multi module."""
    def test_merges_checkstyle_files_from_both_modules(self):
        """Verify merges checkstyle files from both modules."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reports = []
            for i in range(2):
                path = root / f"{i}.xml"
                path.write_text(f'<checkstyle><file name="{i}.java"/></checkstyle>')
                reports.append(path)
            target = root / "merged.xml"
            merge_reports("checkstyle", reports, target)
            self.assertEqual(len(ET.parse(target).getroot().findall("file")), 2)

    def test_partial_scanner_error_is_not_clean(self):
        """Verify partial scanner error is not clean."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            modules = (root / "a", root / "b")
            for module in modules:
                (module / "src/main/java").mkdir(parents=True)
            def fake_run(scanner, _repo, work, _tools, _env):
                if "1" in work.parts:
                    return 2
                name = {"checkstyle": "checkstyle.xml", "pmd": "pmd.xml",
                    "spotbugs": "spotbugs.xml"}[scanner]
                (work / name).write_text('<checkstyle/>'
                    if name == 'checkstyle.xml' else '<pmd/>' if name == 'pmd.xml' else (
                    '<BugCollection><Errors errors="0" missingClasses'
                    '="0"/></BugCollection>'
                ))
                return 0
            with patch("quality.Local_Scans.java_modules.run_native", side_effect=fake_run):
                results = run_modules(root, root / "work", root / "tools", modules)
            self.assertEqual(results, {"checkstyle": "error", "pmd": "error", "spotbugs": "error"})
            self.assertFalse((root / "work/checkstyle.xml").exists())

    def test_spotbugs_rejects_analysis_errors(self):
        """Verify spotbugs rejects analysis errors."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / "sb.xml"
            report.write_text((
                '<BugCollection><Errors errors="1" missingClasses'
                '="0"/></BugCollection>'
            ))
            with self.assertRaises(ValueError):
                merge_reports("spotbugs", [report], root / "merged.xml")


if __name__ == "__main__":
    unittest.main()
