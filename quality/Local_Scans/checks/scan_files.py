
"""Shared source-file discovery for Local Quality Gate scanners."""

import os
import stat
from pathlib import Path


EXCLUDED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".dart_tool",
    "build",
    "dist",
    "target",
}

EXCLUDED_PATH_PREFIXES = (
    ("quality", "Local_Scans", "reports"),
    ("quality", "Local_Scans", "tools"),
    ("quality", "analysis"),
)


def safe_entry(path):
    """Reject links, reparse points and non-regular filesystem entries."""
    info = path.lstat()
    return not (stat.S_ISLNK(info.st_mode) or
                getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def eligible_files(repo_root, suffixes):
    """Return regular source files without following links or generated trees."""
    root = Path(repo_root).resolve()
    extensions = {suffix.lower() for suffix in suffixes}
    files = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        parent = Path(directory)
        dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRECTORIES
                   and (parent / name).relative_to(root).parts not in EXCLUDED_PATH_PREFIXES
                   and safe_entry(parent / name)]
        for name in names:
            path = parent / name
            if path.suffix.lower() in extensions and safe_entry(path) and path.is_file():
                files.append(str(path))
    return sorted(files)
