"""Java scanner scripts must honor the launcher's Python interpreter."""
import subprocess
import unittest
from pathlib import Path


CHECKS = Path(__file__).resolve().parents[1] / "checks"


class JavaPythonInterpreterTests(unittest.TestCase):
    def test_shell_syntax(self):
        for name in ("check_pmd.sh", "check_spotbugs.sh"):
            with self.subTest(name=name):
                result = subprocess.run(
                    ["sh", "-n", str(CHECKS / name)],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_scripts_do_not_require_hardcoded_python3(self):
        for name in ("check_pmd.sh", "check_spotbugs.sh"):
            with self.subTest(name=name):
                script = (CHECKS / name).read_text(encoding="utf-8")
                self.assertIn('"${PYTHON_CMD}"', script)
                self.assertIn("run_python()", script)
                self.assertNotIn("command -v python3", script)
                self.assertNotIn("python3 - ", script)
