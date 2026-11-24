"""Zero-configuration Maven discovery regression tests."""

import json
import subprocess  # nosec B404 - explicit argument vectors or test doubles
import sys
import tempfile
import unittest
from pathlib import Path

from quality.project_discovery import discover_java, discover_maven_modules


def make_module(root, name):
    """Create a Maven module with a minimal Java source file."""
    module = root / name
    source = module / "src/main/java"

    source.mkdir(parents=True)

    (module / "pom.xml").write_text("<project/>", encoding="utf-8")
    (source / "App.java").write_text("class App {}", encoding="utf-8")

    return module


class JavaDiscoveryTests(unittest.TestCase):
    """Regression coverage for Java discovery."""

    def test_root_maven(self):
        """Verify root Maven."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_module(root, ".")
            layout = discover_java(root)

            self.assertEqual(layout.maven_project, root.resolve())
            self.assertFalse(layout.ambiguous)

    def test_backend_maven(self):
        """Verify backend Maven."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_module(root, "backend")
            layout = discover_java(root)

            self.assertEqual(
                layout.maven_project,
                (root / "backend").resolve(),
            )

    def test_no_java(self):
        """Verify no Java."""
        with tempfile.TemporaryDirectory() as directory:
            layout = discover_java(Path(directory))

            self.assertIsNone(layout.java_source)
            self.assertFalse(layout.ambiguous)

    def test_multiple_modules_not_silently_selected(self):
        """Verify multiple modules not silently selected."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_module(root, "api")
            make_module(root, "service")
            layout = discover_java(root)

            self.assertTrue(layout.ambiguous)
            self.assertIsNone(layout.maven_project)
            self.assertEqual(len(layout.candidates), 2)

    def test_ignored_generated_directories(self):
        """Verify ignored generated directories."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_module(root, "node_modules/dependency")

            self.assertIsNone(discover_java(root).java_source)

    def test_java_without_maven_is_not_silently_skipped(self):
        """Verify Java without Maven is not silently skipped."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            (root / "Example.java").write_text(
                "class Example {}",
                encoding="utf-8",
            )

            layout = discover_java(root)

            self.assertTrue(layout.unsupported_java)
            self.assertIsNone(layout.maven_project)

    def test_ignored_java_is_not_unsupported(self):
        """Verify ignored Java is not unsupported."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "node_modules" / "Example.java"

            source.parent.mkdir()
            source.write_text("class Example {}", encoding="utf-8")

            self.assertFalse(discover_java(root).unsupported_java)


class MultiModuleDiscoveryTests(unittest.TestCase):
    """Regression coverage for multi-module discovery."""

    def test_aggregator_and_two_modules(self):
        """Verify aggregator and two modules."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            (root / "pom.xml").write_text(
                "<project/>",
                encoding="utf-8",
            )

            first = make_module(root, "api")
            second = make_module(root, "service")

            self.assertEqual(
                discover_maven_modules(root),
                (first.resolve(), second.resolve()),
            )

    def test_nested_module_is_discovered_once(self):
        """Verify nested module is discovered once."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            parent = make_module(root, "parent")
            child = make_module(root, "parent/child")

            self.assertEqual(
                discover_maven_modules(root),
                (parent.resolve(), child.resolve()),
            )

    def test_json_manifest_for_multiple_modules(self):
        """Verify JSON manifest for multiple modules."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            make_module(root, "api")
            make_module(root, "service")

            result = subprocess.run(  # nosec B603 - fixed command arguments
                [
                    sys.executable,
                    "-m",
                    "quality.project_discovery",
                    "--json",
                    str(root),
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            payload = json.loads(result.stdout)

            self.assertEqual(payload["status"], "multiple")
            self.assertEqual(len(payload["modules"]), 2)
            self.assertTrue(
                all("java_source" in item for item in payload["modules"])
            )
