"""Run Java scanners for all discovered Maven modules and merge validated XML."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from quality.project_discovery import discover_maven_modules

SCANNERS = {
    "checkstyle": ("check_checkstyle.sh", "checkstyle.xml"),
    "pmd": ("check_pmd.sh", "pmd.xml"),
    "spotbugs": ("check_spotbugs.sh", "spotbugs.xml"),
}


def merge_reports(scanner: str, reports: list[Path], destination: Path) -> None:
    """Merge XML from completed modules, rejecting unexpected report structures."""
    expected = {"checkstyle": "checkstyle", "pmd": "pmd", "spotbugs": "BugCollection"}[scanner]
    roots = []
    for path in reports:
        root = ET.parse(path).getroot()
        if root.tag.rsplit("}", 1)[-1] != expected:
            raise ValueError(f"Unexpected {scanner} XML root in {path}")
        roots.append(root)
    if not roots:
        raise ValueError("No scanner reports to merge")
    merged = roots[0]
    if scanner == "spotbugs":
        for root in roots:
            errors = root.find("Errors")
            if errors is None or errors.get("errors") != "0" or errors.get("missingClasses") != "0":
                raise ValueError("SpotBugs reported analysis errors or missing classes")
        for root in roots[1:]:
            for child in root:
                if child.tag.rsplit("}", 1)[-1] == "BugInstance":
                    merged.append(child)
    else:
        for root in roots[1:]:
            for child in root:
                merged.append(child)
    destination.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(merged).write(destination, encoding="utf-8", xml_declaration=True)


def run_modules(repo: Path, work: Path, tools: Path, modules: tuple[Path, ...] | None = None) -> dict[str, str]:
    """Execute every scanner on every module; partial execution is an error."""
    repo, work, tools = repo.resolve(), work.resolve(), tools.resolve()
    if modules is None:
        modules = discover_maven_modules(repo)
    results = {}
    for scanner, (script, report_name) in SCANNERS.items():
        reports = []
        codes = []
        for index, module in enumerate(modules):
            module_work = work / "java-modules" / str(index) / scanner
            module_work.mkdir(parents=True, exist_ok=True)
            env = os.environ.copy()
            env["QUALITY_MAVEN_DIR"] = str(module)
            env["QUALITY_JAVA_SOURCE"] = str(module / "src" / "main" / "java")
            command = ["sh", str(repo / "quality" / "Local_Scans" / "checks" / script), str(repo), str(module_work), str(tools)]
            code = subprocess.run(command, env=env, check=False, stdout=sys.stderr).returncode
            codes.append(code)
            report = module_work / report_name
            if code in (0, 1) and report.is_file():
                reports.append(report)
        if not modules:
            results[scanner] = "skipped"
        elif any(code not in (0, 1) for code in codes) or len(reports) != len(modules):
            results[scanner] = "error"
        else:
            try:
                merge_reports(scanner, reports, work / report_name)
            except (OSError, ET.ParseError, ValueError) as exc:
                print(f"ERROR: {scanner} report aggregation failed: {exc}", file=sys.stderr)
                results[scanner] = "error"
            else:
                results[scanner] = "failed" if 1 in codes else "passed"
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("work", type=Path)
    parser.add_argument("tools", type=Path)
    args = parser.parse_args()
    result = run_modules(args.repo, args.work, args.tools)
    for name, status in result.items():
        print(f"{name}={status}")
    if "error" in result.values():
        sys.exit(2)
    if "failed" in result.values():
        sys.exit(1)


if __name__ == "__main__":
    main()
