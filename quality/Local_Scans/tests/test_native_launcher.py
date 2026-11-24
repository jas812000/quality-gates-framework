"""Regression tests for native launcher."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from quality.Local_Scans.scanner_registry import LOCAL_SCANNER_NAMES
from quality.Local_Scans.tests.report_fixture import write_report_fixture
from quality.Local_Scans.run_local_checks import output_root, package
from quality.Local_Scans.checks.java_native import run



class NativeTests(unittest.TestCase):
    """Regression coverage for native."""
    def test_package_excludes_raw(self):
        """Verify package excludes raw."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in ("local-report.html", "normalized.json", "trivy.json"):
                (root / name).write_text("fixture")
            write_report_fixture(root)
            package(root, root / "out.zip")
            with zipfile.ZipFile(root / "out.zip") as bundle:
                self.assertEqual(set(bundle.namelist()), {"local-report.html",
                    "normalized.json",
                        "diagnostics/scanner-status.json"}
                            | {f"scanner-reports/{name}.json" for name in LOCAL_SCANNER_NAMES})

    def test_missing_java_is_error(self):
        """Verify missing java is error."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("quality.Local_Scans.checks.java_native.shutil.which", return_value=None):
                self.assertEqual(run("checkstyle", root, root / "work", root / "tools"), 2)

    def test_output_rejects_repository(self):
        """Verify output rejects repository."""
        with patch.dict(os.environ, {"QUALITY_OUTPUT_DIR": str(Path.cwd())}):
            with self.assertRaises(ValueError):
                output_root(Path.cwd())

    def test_collision_and_symlink(self):
        """Verify collision and symlink."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "Downloads").mkdir()
            with patch("pathlib.Path.home", return_value=root), patch.dict(os.environ,
                {"QUALITY_OUTPUT_DIR": ""}):
                self.assertNotEqual(output_root(root / "a/repo"), output_root(root / "b/repo"))
                link = root / "Downloads/link"
                try:
                    link.symlink_to(root, target_is_directory=True)
                except OSError:
                    self.skipTest("Symlink creation unavailable")
                with patch.dict(os.environ, {"QUALITY_OUTPUT_DIR": str(link / "reports")}):
                    with self.assertRaises(ValueError):
                        output_root(root / "repo")

    def test_package_missing_does_not_leave_archive(self):
        """Verify package missing does not leave archive."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            archive = root / "out.zip"
            (root / "local-report.html").write_text("fixture")
            with self.assertRaises(ValueError):
                package(root, archive)
            self.assertFalse(archive.exists())

    def test_package_rejects_symlink_artifact(self):
        """Verify package rejects symlink artifact."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "normalized.json").write_text("fixture")
            target = root / "target.html"
            target.write_text("fixture")
            try:
                (root / "local-report.html").symlink_to(target)
            except OSError:
                self.skipTest("Symlink creation unavailable")
            with self.assertRaises(ValueError):
                package(root, root / "out.zip")
            self.assertFalse((root / "out.zip").exists())
