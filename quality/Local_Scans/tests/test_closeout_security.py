"""Final source discovery and release integrity regressions."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from quality.Local_Scans.checks import java_native, scan_files


class CloseoutSecurityTests(unittest.TestCase):
    """Verify external links and unverified PMD archives are rejected."""

    def test_source_discovery(self):
        """Keep regular sources and exclude generated trees and links."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "repo"
            root.mkdir()
            source = root / "valid.py"
            source.touch()
            (root / "target").mkdir()
            (root / "target" / "generated.py").touch()
            outside = base / "outside.py"
            outside.touch()
            try:
                (root / "link.py").symlink_to(outside)
                (root / "linked").symlink_to(base, target_is_directory=True)
            except OSError:
                pass  # Windows runners may prohibit creating links.
            self.assertEqual(scan_files.eligible_files(root, {".py"}), [str(source.resolve())])

    def test_reparse_entry(self):
        """Reject Windows reparse attributes without platform dependencies."""
        with patch.object(Path, "lstat") as info:
            info.return_value.st_mode = 0o100644
            info.return_value.st_file_attributes = 0x400
            self.assertFalse(scan_files.safe_entry(Path("fixture")))

    def test_pmd_checksum(self):
        """Reject a corrupted cached release before Java execution."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pmd-dist-7.29.0-bin.zip").write_bytes(b"invalid archive")
            (root / "pmd-bin-7.29.0" / "lib").mkdir(parents=True)
            with (patch.object(java_native, "execute") as execute,
                  patch.object(java_native.shutil, "which", return_value="java")):
                self.assertEqual(java_native.run("pmd", root, root / "work", root), 2)
                self.assertFalse((root / "work/pmd.xml").exists())
                execute.assert_not_called()
