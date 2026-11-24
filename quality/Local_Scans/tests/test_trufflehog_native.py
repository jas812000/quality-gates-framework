"""Native TruffleHog snapshot and failure regression tests."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from quality.Local_Scans.checks import check_trufflehog as scanner


class NativeTruffleHogTests(unittest.TestCase):
    """Verify native execution and strict output handling."""

    def exercise(self, code, payload, stderr=b"", platform="darwin"):
        """Run a synthetic scanner response against a filtered snapshot."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo with spaces"
            root.mkdir()
            (root / "sample.txt").write_text("fixture", encoding="utf-8")
            (root / ".git").mkdir()
            work = Path(directory) / "work"

            def execute(command, output, **kwargs):
                expected = ["filesystem", ".", "--json", "--no-verification", "--no-update"]
                if platform == "win32":
                    expected.append("--local-dev")
                self.assertEqual(command[1:], expected)
                self.assertTrue((kwargs["cwd"] / "sample.txt").is_file())
                self.assertFalse((kwargs["cwd"] / ".git").exists())
                self.assertTrue(kwargs["capture_diagnostics"])
                output.write_text(payload, encoding="utf-8")
                return subprocess.CompletedProcess(command, code, stderr=stderr)

            with patch.object(scanner.sys, "platform", platform), patch.object(scanner.shutil, "which", side_effect=lambda name: name), patch.object(scanner, "run_scanner_to_file", side_effect=execute):
                scanner.run(root, work)
            status = json.loads((work / "trufflehog.status.json").read_text())
            return status, (work / "trufflehog.jsonl").exists()

    def test_clean(self):
        """Empty successful JSONL is valid."""
        self.assertEqual(self.exercise(0, ""), ({"status": "completed", "exit_code": 0}, True))

    def test_positive(self):
        """Valid JSONL remains available for normalization."""
        self.assertTrue(self.exercise(0, '{}\n')[1])

    def test_invalid(self):
        """Invalid JSONL is removed."""
        self.assertEqual(self.exercise(0, 'invalid')[0]["status"], "failed")
        self.assertFalse(self.exercise(0, 'invalid')[1])

    def test_failure(self):
        """Nonzero exit remains a failure; raw diagnostics never persist."""
        status, exists = self.exercise(1, '{}', b'access is denied private fixture')
        self.assertFalse(exists)
        self.assertEqual(status["status"], "failed")
        self.assertEqual(status["reason"], "TruffleHog execution failed: access denied")

    def test_windows_supervisor_bypass(self):
        """Windows scans bypass the unsupported process supervisor."""
        self.assertTrue(self.exercise(0, "", platform="win32")[1])
        self.assertTrue(self.exercise(0, "{}\n", platform="win32")[1])
        self.assertFalse(self.exercise(1, "", platform="win32")[1])
