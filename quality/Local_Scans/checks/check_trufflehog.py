
"""Run the local TruffleHog filesystem scan."""

import json
import shutil
import stat
import subprocess  # nosec B404 - scanner timeout handling
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from quality.Local_Scans.checks.scanner_runner import run_scanner_to_file, write_status


IMAGE = "trufflesecurity/trufflehog:3.82.6"


def _unsafe_path(path):
    """Exclude symbolic links and Windows reparse points from snapshots."""
    return path.is_symlink() or bool(
        getattr(path.lstat(), "st_file_attributes", 0)
        & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def _stage_source(root: Path, temporary: str) -> tuple[Path, Path]:
    """Create a filtered scan snapshot and exclusion rules."""
    staging = Path(temporary) / "source"
    excluded_dirs = {
        ".git", ".idea", ".venv", "venv", "node_modules",
        "__pycache__", "target", "build", "dist", ".pytest_cache",
    }

    def ignore_generated(directory, names):
        relative = Path(directory).relative_to(root)
        excluded = {name for name in names if name in excluded_dirs}
        if relative.parts[:2] == ("quality", "Local_Scans"):
            excluded.update(name for name in names if name in {"reports", "tools"})
        if relative.parts == ("quality",):
            excluded.update(name for name in names if name == "analysis")
        return excluded

    def ignore_unsafe(directory, names):
        excluded = ignore_generated(directory, names)
        excluded.update(
            name for name in names
            if _unsafe_path(Path(directory) / name)
        )
        return excluded

    shutil.copytree(root, staging, ignore=ignore_unsafe)
    exclude = Path(temporary) / "exclude.txt"
    patterns = [
        r"(^|/)\.git(/|$)",
        r"(^|/)quality/analysis(/|$)",
        r"(^|/)quality/Local_Scans/reports(/|$)",
        r"(^|/)quality/Local_Scans/tools(/|$)",
        r"(^|/)target(/|$)",
        r"(^|/)node_modules(/|$)",
        r"(^|/)\.venv(/|$)",
        r"(^|/)__pycache__(/|$)",
        r"(^|/)dist(/|$)",
        r"(^|/)build(/|$)",
        r"(^|/)\.idea(/|$)",
    ]
    exclude.write_text("\n".join(patterns) + "\n", encoding="utf-8")

    return staging, exclude


def _failure_category(stderr):
    """Return fixed diagnostic labels only; never retain scanner stderr."""
    message = (stderr or b"").lower()
    for marker, category in (
        (b"not supported", "unsupported platform or operation"),
        (b"trufflehog updater", "scanner supervisor error"),
        (b"unknown flag", "unsupported option"),
        (b"unknown long flag", "unsupported option"),
        (b"access is denied", "access denied"),
        (b"permission denied", "access denied"),
        (b"cannot find", "path unavailable"),
        (b"no such file", "path unavailable"),
        (b"panic:", "scanner panic"),
        (b"fatal", "scanner fatal error"),
    ):
        if marker in message:
            return category
    return "unclassified scanner error"


def run(repo_root, work_dir):
    """Scan a filtered snapshot using native TruffleHog or Docker."""
    root = Path(repo_root).resolve()
    work = Path(work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)

    output = work / "trufflehog.jsonl"
    output.unlink(missing_ok=True)

    try:
        with TemporaryDirectory(prefix="quality-trufflehog-") as temporary:
            # Docker filesystem scanning must never traverse Git object storage.
            # The scanner's exclude-paths option is not a reliable way to
            # exclude .git from a filesystem walk, so stage a filtered copy.
            staging, exclude = _stage_source(root, temporary)

            native = shutil.which("trufflehog")
            docker = shutil.which("docker")
            if native is None and docker is None:
                raise OSError("Docker executable unavailable")

            command = [
                docker, "run", "--rm",
                "-v", f"{staging}:/repo:ro",
                "-v", f"{exclude}:/run/quality-exclude.txt:ro",
                IMAGE,
                "filesystem", "/repo",
                "--exclude-paths", "/run/quality-exclude.txt",
                "--json",
                "--no-verification",
            ]

            if native:
                # Relative scan roots avoid Windows drive-letter interpretation.
                # The snapshot already excludes generated and unsafe paths.
                command = [native, "filesystem", ".", "--json", "--no-verification", "--no-update"]
                if sys.platform == "win32":
                    # The upstream supervisor is not portable to Windows.
                    command.append("--local-dev")
                completed = run_scanner_to_file(
                    command, output, cwd=staging, capture_diagnostics=True,
                )
            else:
                completed = run_scanner_to_file(
                    command, output, capture_diagnostics=True,
                )

        valid = completed.returncode == 0

        if valid:
            try:
                with output.open(encoding="utf-8") as stream:
                    for line in stream:
                        if line.strip():
                            if not isinstance(json.loads(line), dict):
                                valid = False
                                break
            except (OSError, ValueError, UnicodeError):
                valid = False

        if valid:
            write_status(work, "trufflehog", "completed", 0)
            return

        output.unlink(missing_ok=True)
        write_status(
            work,
            "trufflehog",
            "failed",
            completed.returncode,
            ("TruffleHog execution failed: " + _failure_category(completed.stderr)
             if completed.returncode else "TruffleHog JSONL was invalid"),
        )

    except (OSError, subprocess.SubprocessError):
        output.unlink(missing_ok=True)
        write_status(
            work,
            "trufflehog",
            "failed",
            reason="Docker or TruffleHog execution unavailable",
        )



if __name__ == "__main__":
    from quality.Local_Scans.checks.cli import invoke_scanner

    invoke_scanner(run, "quality.Local_Scans.checks.check_trufflehog")
