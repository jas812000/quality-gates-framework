"""Zero-configuration Maven discovery regression tests."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from quality.project_discovery import discover_java, discover_maven_modules


class JavaDiscoveryTests(unittest.TestCase):
    def _make_module(self, root, name):
        module = root / name
        source = module / "src/main/java"
        source.mkdir(parents=True)
        (module / "pom.xml").write_text("<project/>", encoding="utf-8")
        (source / "App.java").write_text("class App {}", encoding="utf-8")
        return module

    def test_root_maven(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_module(root, ".")
            layout = discover_java(root)
            self.assertEqual(layout.maven_project, root.resolve())
            self.assertFalse(layout.ambiguous)

    def test_backend_maven(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_module(root, "backend")
            layout = discover_java(root)
            self.assertEqual(layout.maven_project, (root / "backend").resolve())

    def test_no_java(self):
        with tempfile.TemporaryDirectory() as directory:
            layout = discover_java(Path(directory))
            self.assertIsNone(layout.java_source)
            self.assertFalse(layout.ambiguous)

    def test_multiple_modules_not_silently_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_module(root, "api")
            self._make_module(root, "service")
            layout = discover_java(root)
            self.assertTrue(layout.ambiguous)
            self.assertIsNone(layout.maven_project)
            self.assertEqual(len(layout.candidates), 2)

    def test_ignored_generated_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_module(root, "node_modules/dependency")
            self.assertIsNone(discover_java(root).java_source)

    def test_java_without_maven_is_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Example.java").write_text("class Example {}", encoding="utf-8")
            layout = discover_java(root)
            self.assertTrue(layout.unsupported_java)
            self.assertIsNone(layout.maven_project)

    def test_ignored_java_is_not_unsupported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "node_modules" / "Example.java"
            source.parent.mkdir()
            source.write_text("class Example {}", encoding="utf-8")
            self.assertFalse(discover_java(root).unsupported_java)


class MultiModuleDiscoveryTests(unittest.TestCase):
    _make_module = JavaDiscoveryTests._make_module
    def test_aggregator_and_two_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text("<project/>", encoding="utf-8")
            first = self._make_module(root, "api")
            second = self._make_module(root, "service")
            self.assertEqual(discover_maven_modules(root), (first.resolve(), second.resolve()))

    def test_nested_module_is_discovered_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = self._make_module(root, "parent")
            child = self._make_module(root, "parent/child")
            self.assertEqual(discover_maven_modules(root), (parent.resolve(), child.resolve()))

    def test_json_manifest_for_multiple_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_module(root, "api")
            self._make_module(root, "service")
            result = subprocess.run(
                [sys.executable, "-m", "quality.project_discovery", "--json", str(root)],
                capture_output=True, text=True, check=True,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "multiple")
            self.assertEqual(len(payload["modules"]), 2)
            self.assertTrue(all("java_source" in item for item in payload["modules"]))
