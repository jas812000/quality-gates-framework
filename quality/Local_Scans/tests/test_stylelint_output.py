"""Verify explicit Stylelint report output and failure handling."""

import json
from pathlib import Path
import subprocess  # nosec B404 - explicit argument vectors or test doubles
import tempfile
import unittest
from unittest.mock import patch

from quality.Local_Scans.checks.check_stylelint import run


class StylelintOutputTests(unittest.TestCase):
    """Regression coverage for Stylelint output."""

    def test_explicit_output_and_invalid_report(self):
        """Verify explicit output and invalid report."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, work, tools = (root / n for n in ("repo", "work", "tools"))

            repo.mkdir()
            (repo / "style.css").write_text("a {}", encoding="utf-8")

            exe = tools / "stylelint/node_modules/stylelint/bin/stylelint.mjs"
            exe.parent.mkdir(parents=True)
            exe.touch()

            for payload, expected in (
                ([{"warnings": []}], "completed"),
                ({}, "failed"),
            ):
                serialized_payload = json.dumps(payload)

                def execute(argv, content=serialized_payload, **_kwargs):
                    output = Path(argv[argv.index("--output-file") + 1])
                    output.write_text(content, encoding="utf-8")
                    return subprocess.CompletedProcess(argv, 2)

                with patch(
                    "quality.Local_Scans.checks.check_stylelint.subprocess.run",
                    side_effect=execute,
                ):
                    run(repo, work, tools)

                status = json.loads(
                    (work / "stylelint.status.json").read_text()
                )

                self.assertEqual(status["status"], expected)
                self.assertEqual(
                    (work / "stylelint.json").exists(),
                    expected == "completed",
                )
