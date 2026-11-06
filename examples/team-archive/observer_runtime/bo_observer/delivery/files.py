"""Enumerate maintained framework files without descending into package caches."""

import os
from pathlib import Path


def framework_files(root):
    """Use the same bounded dependency traversal for installation and fingerprints."""
    for directory, folders, names in os.walk(root, followlinks=False):
        folders[:] = sorted(
            name
            for name in folders
            if name
            not in {
                "node_modules",
                "__pycache__",
                ".git",
                ".venv",
                ".pytest_cache",
            }
            and not (Path(directory) / name).is_symlink()
        )
        for name in sorted(names):
            path = Path(directory) / name
            if path.suffix in {".py", ".mjs", ".json"} and not path.is_symlink():
                yield path
