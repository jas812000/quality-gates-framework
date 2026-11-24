"""Optional project metadata must not override automatic source discovery."""
import json
import tempfile
import unittest
from pathlib import Path

from quality.project_config import load


class OptionalProjectConfigTests(unittest.TestCase):
    """Regression coverage for optional project config."""
    def test_project_name_only_does_not_force_epms_paths(self):
        """Verify project name only does not force epms paths."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "project.json"
            config.write_text(json.dumps({"project_name": "Sample"}), encoding="utf-8")
            values = load(root, config)
            self.assertEqual(values["java_source"], "")
            self.assertEqual(values["maven_project"], "")

    def test_explicit_java_paths_still_work(self):
        """Verify explicit java paths still work."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "project.json"
            config.write_text(json.dumps({"java_source": "app/src/main/java",
                "maven_project": "app"}), encoding="utf-8")
            values = load(root, config)
            self.assertEqual(Path(values["java_source"]).resolve(),
                (root / "app/src/main/java").resolve())
            self.assertEqual(Path(values["maven_project"]).resolve(), (root / "app").resolve())
