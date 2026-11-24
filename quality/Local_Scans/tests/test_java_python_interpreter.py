"""Java scanner scripts must honor the launcher's Python interpreter."""
import subprocess  # nosec B404 - explicit argument vectors or test doubles
import shutil
import unittest
from pathlib import Path


CHECKS = Path(__file__).resolve().parents[1] / "checks"


class JavaPythonInterpreterTests(unittest.TestCase):
    """Regression coverage for java python interpreter."""
    @unittest.skipUnless(shutil.which("sh"), "Legacy POSIX wrapper syntax")
    def test_shell_syntax(self):
        """Verify shell syntax."""
        for name in ("check_pmd.sh", "check_spotbugs.sh"):
            with self.subTest(name=name):
                result = subprocess.run(  # nosec B603 - fixed command arguments
                    [shutil.which("sh"), "-n", str(CHECKS / name)],
                    capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_scripts_do_not_require_hardcoded_python3(self):
        """Verify scripts do not require hardcoded python3."""
        for name in ("check_pmd.sh", "check_spotbugs.sh"):
            with self.subTest(name=name):
                script = (CHECKS / name).read_text(encoding="utf-8")
                self.assertIn('"${PYTHON_CMD}"', script)
                self.assertIn("run_python()", script)
                self.assertNotIn("command -v python3", script)
                self.assertNotIn("python3 - ", script)
