"""Regression checks for final security corrections."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from defusedxml.common import DefusedXmlException
from quality.Local_Scans.java_modules import merge_reports
from quality.Local_Scans.checks import check_python_scanners, java_native

class FinalSecurityTests(unittest.TestCase):
    """Regression coverage for final security."""
    def test_missing_pylint_config(self):
        """Verify missing pylint config."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.py").write_text("x = 1\n")
            with patch.object(check_python_scanners, "run_json_scanner") as scan:
                check_python_scanners.run_pylint(root, root / "work")
                self.assertFalse(any(arg.startswith("--rcfile") for arg in scan.call_args.args[1]))

    def test_entity_rejected(self):
        """Verify entity rejected."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "bad.xml"
            source.write_text((
                '<!DOCTYPE checkstyle [<!ENTITY x "bad">]><checks'
                'tyle>&x;</checkstyle>'
            ))
            with self.assertRaises(DefusedXmlException):
                merge_reports("checkstyle", [source], root / "out.xml")

    def test_non_https_download_rejected(self):
        """Verify non https download rejected."""
        with self.assertRaises(ValueError):
            java_native.download(Path("unused"), "file:///etc/passwd")
