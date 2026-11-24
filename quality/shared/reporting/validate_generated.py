"""Validate synthetic generated reports independently of source scans."""
import argparse
from copy import deepcopy
from datetime import datetime
from html.parser import HTMLParser
import json
from pathlib import Path

from quality.CI.gate.schemas import base_tool_result
from quality.CI.gate.report.report_html import build_html_report
from quality.CI.gate.report.report_diagnostics import prepare_diagnostic_document
from quality.Local_Scans.reporting.report_html import build_html
from quality.Local_Scans.scanner_registry import LOCAL_SCANNER_NAMES
from quality.Local_Scans.checks import check_htmlhint, check_stylelint


class ReportCSS(HTMLParser):
    """Collect style blocks and inline declarations without executing markup."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_style = False
        self.blocks = []
        self.inline = []

    def handle_starttag(self, tag, attrs):
        if tag == "style":
            self.in_style = True
        self.inline.extend(value for key, value in attrs if key == "style" and value)

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False

    def handle_data(self, data):
        if self.in_style:
            self.blocks.append(data)

    def stylesheet(self):
        """Return embedded CSS and standalone rules for inline declarations."""
        if not self.blocks:
            raise ValueError("Report has no embedded stylesheet")
        return "\n\n".join(self.blocks + [
            f".inline-{index} {{\n{value}\n}}"
            for index, value in enumerate(self.inline, 1)
        ])


def render_reports():
    """Exercise every report renderer with synthetic findings and clean results."""
    results = [base_tool_result(name) for name in LOCAL_SCANNER_NAMES]
    for result in results:
        result.update(executed=True, artifact_present=True)
    result = next(item for item in results if item["tool"] == "pylint")
    result.update(violation_count=1, max_severity="low", findings=[{
        "file": "example.py", "line": 1, "column": 1, "severity": "low",
        "rule": "example-rule", "message": "Synthetic finding <example>",
    }])
    result["severity_counts"]["low"] = 1
    local = build_html({"generated_at": "fixture", "scan_user": "fixture",
                        "repo_root": "fixture", "normalized": {
                            "results": results, "total_violations": 1,
                            "scanner_errors": 0}})
    evaluated = {"overall_block": False, "blocking_results": [],
                 "non_blocking_results": [{"tool": item["tool"], "blocking": False,
                     "policy_violation": False, "reason": "", "normalized": item}
                     for item in results]}
    public = deepcopy(evaluated)
    for item in public["non_blocking_results"]:
        item["normalized"].update(findings=[], metadata={})
    env = {"event_name": "push", "run_number": "1", "run_id": "1",
           "sha": "a" * 40, "server_url": "https://github.com",
           "repository": "example/framework"}
    return {"local": local, "ci-summary": build_html_report(public, env),
            "ci-diagnostic": build_html_report(
                prepare_diagnostic_document(evaluated), env, link_findings=True)}


def write_reports(folder):
    """Write synthetic HTML and extracted CSS into a fresh output directory."""
    folder.mkdir(parents=True, exist_ok=False)
    for name, html in render_reports().items():
        parser = ReportCSS()
        parser.feed(html)
        parser.close()
        (folder / f"{name}.html").write_text(html, encoding="utf-8")
        (folder / f"{name}.css").write_text(parser.stylesheet(), encoding="utf-8")


def scanner_outcome(work, name):
    """Reject missing or incomplete scanner results; count reported findings."""
    try:
        status = json.loads((work / f"{name}.status.json").read_text(encoding="utf-8"))
        if status.get("status") != "completed":
            return "ERROR", 0
        data = json.loads((work / f"{name}.json").read_text(encoding="utf-8"))
        key = "messages" if name == "htmlhint" else "warnings"
        if not isinstance(data, list):
            return "ERROR", 0
        count = sum(len(item[key]) for item in data)
        return ("FAIL" if count else "PASS"), count
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return "ERROR", 0


def scan(folder, work, tools):
    """Use the existing scanners with isolated synthetic inputs."""
    check_htmlhint.run(folder, work)
    check_stylelint.run(folder, work, tools)
    return {name: scanner_outcome(work, name) for name in ("htmlhint", "stylelint")}


def main():
    """Run generated-report validation and positive detection controls."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path.home() / "Downloads")
    args = parser.parse_args()
    output = args.output.resolve() / datetime.now().strftime("qg-generated-%Y%m%d_%H%M%S_%f")
    reports = output / "reports"
    write_reports(reports)
    positive = output / "positive"
    positive.mkdir()
    (positive / "invalid.html").write_text('<div id="x"></div><div id="x"></div>', encoding="utf-8")
    (positive / "invalid.css").write_text('a { color: #gggggg; }', encoding="utf-8")
    actual = scan(reports, output / "results", output / "tools")
    control = scan(positive, output / "control", output / "tools")
    passed = all(state == "PASS" for state, _ in actual.values()) and all(
        state == "FAIL" and count > 0 for state, count in control.values())
    summary = {"generated": actual, "positive_control": control, "passed": passed}
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print("Report:", output)
    return int(not passed)


if __name__ == "__main__":
    raise SystemExit(main())
