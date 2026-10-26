"""Canonical maintained-source inventory for formatting, lint and AST review.

Third-party distributions, generated icons, installed example copies and frozen
evidence are excluded by identity. Keep all development checks on this same scope.
"""

import fnmatch
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "tools/source-scope.json"


def owned_sources(root=ROOT, config=None):
    """Return stable relative paths for each language, without following generated copies."""
    config = config or json.loads(CONFIG.read_text(encoding="utf-8"))
    groups = {}
    for kind in ("python", "javascript", "presentation"):
        matches = {
            path.relative_to(root).as_posix()
            for pattern in config[kind]
            for path in root.glob(pattern)
            if path.is_file()
        }
        groups[kind] = sorted(
            name
            for name in matches
            if not any(fnmatch.fnmatchcase(name, pattern) for pattern in config["exclude"])
        )
    return groups


def source_files():
    """Resolve the owned paths for existing formatter callers."""
    groups = owned_sources()
    return (
        [ROOT / name for name in groups["python"]],
        [ROOT / name for name in groups["javascript"] + groups["presentation"]],
    )


if __name__ == "__main__":
    print(json.dumps(owned_sources(), indent=2))
