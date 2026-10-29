"""Read the physical project tree without importing or executing application code.

The source inventory remains the authority for AST coverage. This inventory adds
directories and non-code files; it never turns an excluded source into covered code.
"""

import fnmatch
import os
import stat
from pathlib import Path

from ..graph.behavior_model import digest
from ..workflow.bo_sync import IGNORED

TEXT_SUFFIXES = {".json", ".toml", ".yaml", ".yml", ".html", ".css", ".sql", ".md", ".txt"}
MAX_TEXT_BYTES = 2_000_000


def inventory(root, config, source):
    """Enumerate declared roots, prune generated trees, and do not follow links.

    File identities use project-relative paths. Non-source text is hashed for
    invalidation, but its contents are neither exported nor sent to the agent.
    """
    root = Path(root).resolve()
    scope = config.get("source_scope", {})
    exclusions = scope.get("exclude", {})
    entries, text_files, excluded, errors = {}, {}, {}, []
    seen = set()

    def directory(name):
        path = Path(name)
        while True:
            key = path.as_posix()
            entries.setdefault(key, {"kind": "directory"})
            if key == ".":
                break
            path = path.parent

    def visit(path):
        name = path.relative_to(root).as_posix()
        if name in seen:
            return
        seen.add(name)
        if any(part in IGNORED for part in Path(name).parts):
            return
        # View preferences change while using the graph, not while coding.
        if any(
            name == prefix or name.startswith(prefix + "/")
            for prefix in ("bo_stategraph/config", "bo_stategraph/data")
        ):
            return
        reason = source["excluded"].get(name) or next(
            (v for pattern, v in exclusions.items() if fnmatch.fnmatchcase(name, pattern)), None
        )
        if reason:
            excluded[name] = reason
            return
        try:
            details = path.lstat()
            # Windows junctions need the reparse tag on Python 3.11, which has no
            # Path.is_junction(). Neither links nor junctions are traversed.
            junction = getattr(details, "st_reparse_tag", 0) == getattr(
                stat, "IO_REPARSE_TAG_MOUNT_POINT", -1
            )
            if stat.S_ISLNK(details.st_mode) or junction:
                target = path.resolve()
                directory(Path(name).parent)
                entries[name] = {
                    "kind": "symlink",
                    "target": (
                        target.relative_to(root).as_posix() if target.is_relative_to(root) else None
                    ),
                }
                return
            if not path.resolve().is_relative_to(root):
                raise ValueError("Project entry escapes its declared root")
            if path.is_dir():
                directory(name)
                with os.scandir(path) as children:
                    for child in sorted(children, key=lambda item: item.name):
                        visit(Path(child.path))
            elif path.is_file():
                directory(Path(name).parent)
                size = details.st_size
                fact = {"kind": "file", "bytes": size}
                if name in source["files"]:
                    fact["hash"] = source["files"][name]
                    text_files[name] = fact["hash"]
                elif path.suffix.lower() in TEXT_SUFFIXES and size <= MAX_TEXT_BYTES:
                    raw = path.read_bytes()
                    try:
                        raw.decode("utf-8-sig")
                    except UnicodeError:
                        pass
                    else:
                        fact["hash"] = digest(raw)
                        text_files[name] = fact["hash"]
                entries[name] = fact
        except (OSError, ValueError) as exc:
            errors.append({"path": name, "error": str(exc)})

    directory(".")
    for prefix in scope.get("roots", ["."]):
        # Validate the lexical path before resolving a link, so links stay entries.
        start = Path(os.path.abspath(root / prefix))
        if not start.is_relative_to(root):
            raise ValueError("Project scope escapes project")
        visit(start)
    return {
        "entries": dict(sorted(entries.items())),
        "text_files": text_files,
        "readable_files": {
            p: value
            for p, value in text_files.items()
            if p in source["files"]
            or Path(p).suffix.lower() in {".html", ".css", ".sql"}
            or Path(p).name in {"package.json", "pyproject.toml"}
        },
        "excluded": dict(sorted(excluded.items())),
        "errors": errors,
    }
