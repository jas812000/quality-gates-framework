"""Regression tests for platform release."""
import unittest
from unittest.mock import patch
from quality.Local_Scans.run_local_checks import scanner_exit_code
from quality.Local_Scans.platform_acceptance import resolve_command


class PlatformReleaseTests(unittest.TestCase):
    """Regression coverage for platform release."""
    def test_advisory_and_error_exit_codes(self):
        """Verify advisory and error exit codes."""
        result = {"metadata": {"status": "completed"}, "executed": True,
                  "artifact_present": True, "violation_count": 1}
        self.assertEqual(scanner_exit_code({"results": [result]}), 0)
        self.assertEqual(scanner_exit_code({"results": [dict(result, runtime_error=True)]}), 2)
        self.assertEqual(scanner_exit_code({"results": [dict(result, artifact_present=False)]}), 2)

    def test_executable_resolution(self):
        """Verify executable resolution."""
        with patch("quality.Local_Scans.platform_acceptance.shutil.which",
            return_value="C:/Program Files/npm.cmd"):
            self.assertEqual(resolve_command(["npm", "--version"]), ["C:/Program Files/npm.cmd",
                "--version"])
