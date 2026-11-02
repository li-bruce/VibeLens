"""Incremental file imports/re-exports without the optional function/call index."""

import ast
import subprocess
from pathlib import Path
from ..graph.behavior_model import contained, digest
from ..graph.code_structure import collect_file_references
from ..sources import SOURCE_SUFFIXES, parse_javascript


def file_units(root, paths, previous=None):
    """Reuse unchanged units; parser errors stay visible and source is never executed."""
    units, errors, pending = {}, [], []
    for name in sorted(set(paths)):
        try:
            raw = contained(root, name).read_bytes()
            if len(raw) > 2_000_000:
                raise ValueError("source exceeds 2 MB limit")
            fingerprint = digest(raw)
            if (previous or {}).get(name, {}).get("file_hash") == fingerprint:
                units[name] = previous[name]
                continue
            suffix = Path(name).suffix.lower()
            text = raw.decode("utf-8-sig")
            if suffix == ".py":
                units[name] = {
                    "language": "python",
                    "file_hash": fingerprint,
                    "file_references": collect_file_references(
                        name, ast.parse(text, filename=name)
                    ),
                    "symbols": {},
                    "imports": {},
                }
            elif suffix in SOURCE_SUFFIXES:
                pending.append({"path": name, "source": text, "file_hash": fingerprint})
            else:
                raise ValueError("no source adapter registered; file dependencies are incomplete")
        except (OSError, ValueError, SyntaxError, UnicodeError) as error:
            errors.append({"path": name, "error": str(error)})
    if pending:
        try:
            parsed = parse_javascript(
                [{"path": f["path"], "source": f["source"]} for f in pending], file_only=True
            )
            errors.extend(parsed["errors"])
            for file in pending:
                if file["path"] in parsed["units"]:
                    units[file["path"]] = {
                        **parsed["units"][file["path"]],
                        "file_hash": file["file_hash"],
                    }
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            errors.extend({"path": f["path"], "error": str(error)} for f in pending)
    return units, errors
