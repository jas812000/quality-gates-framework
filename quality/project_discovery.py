"""Conservative, zero-configuration detection of Java Maven project layouts."""

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import shlex


EXCLUDED = frozenset({
    ".git", ".venv", "venv", "node_modules", "target", "build", "dist",
    "__pycache__", ".gradle", "quality",
})


@dataclass(frozen=True)
class JavaLayout:
    """Discovered Maven project and Java source directories, if unambiguous."""

    maven_project: Path | None
    java_source: Path | None
    candidates: tuple[Path, ...]
    unsupported_java: bool = False

    @property
    def ambiguous(self) -> bool:
        """Return whether discovery found multiple candidate modules."""
        return len(self.candidates) > 1


def discover_maven_modules(repo_root: Path) -> tuple[Path, ...]:
    """Find every Maven module containing production Java sources.

    The result is deterministic, ignores generated/vendor directories, and
    does not treat a parent aggregator POM as a source-bearing module.
    """
    root = Path(repo_root).resolve()
    modules = []
    for pom in root.rglob("pom.xml"):
        if any(part in EXCLUDED for part in pom.relative_to(root).parts[:-1]):
            continue
        module = pom.parent
        source = module / "src" / "main" / "java"
        if source.is_dir() and any(source.rglob("*.java")):
            modules.append(module)
    return tuple(sorted(set(modules)))


def discover_java(repo_root: Path) -> JavaLayout:
    """Detect one Maven module with Java sources; do not silently choose among many."""
    root = Path(repo_root).resolve()
    candidates = discover_maven_modules(root)
    if len(candidates) == 1:
        module = candidates[0]
        return JavaLayout(module, module / "src" / "main" / "java", candidates)
    if not candidates:
        # Do not silently mark Java scanners inapplicable when Java code exists
        # but there is no supported Maven project.
        unsupported = any(
            not any(part in EXCLUDED for part in source.relative_to(root).parts[:-1])
            for source in root.rglob("*.java")
        )
        return JavaLayout(None, None, candidates, unsupported_java=unsupported)
    return JavaLayout(None, None, candidates)


def main() -> None:
    """Emit shell-safe defaults for a launcher; preserve explicit overrides."""
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--shell", action="store_true")
    mode.add_argument("--json", action="store_true")
    parser.add_argument("repo", type=Path)
    args = parser.parse_args()
    layout = discover_java(args.repo)
    if args.json:
        print(json.dumps({
            "status": ("multiple" if layout.ambiguous else
                       "unsupported" if layout.unsupported_java else
                       "absent" if not layout.candidates else "found"),
            "modules": [
                {"maven_project": str(module),
                 "java_source": str(module / "src" / "main" / "java")}
                for module in layout.candidates
            ],
        }, sort_keys=True))
        return
    if layout.ambiguous:
        print("QUALITY_JAVA_DISCOVERY=ambiguous")
    elif layout.unsupported_java:
        print("QUALITY_JAVA_DISCOVERY=unsupported")
    elif layout.java_source is None:
        print("QUALITY_JAVA_DISCOVERY=absent")
    else:
        print("QUALITY_JAVA_DISCOVERY=found")
        print(f"QUALITY_JAVA_SOURCE={shlex.quote(str(layout.java_source))}")
        print(f"QUALITY_MAVEN_DIR={shlex.quote(str(layout.maven_project))}")


if __name__ == "__main__":
    main()
