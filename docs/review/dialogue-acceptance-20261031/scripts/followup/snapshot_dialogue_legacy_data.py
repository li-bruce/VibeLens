"""Retain synthetic pre-iteration rows and blob hashes through a read-only connection."""

import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
TRIAL = ROOT.parent / "VibeLensTrials/lifecycle-dialogue-20261031"
target = (
    ROOT
    / "docs/review/dialogue-acceptance-20261031/iteration/original-v1-ready/authoritative-rows.json"
)
if target.exists():
    raise ValueError("The immutable pre-iteration data sample already exists")
allowed = {
    "files": ["id", "owner_id", "filename", "size"],
    "shares": ["id", "file_id", "owner_id", "recipient_id", "reviewer_id", "state", "revision"],
    "journal": ["id", "share_id", "revision", "event", "before_state", "after_state"],
}
data = {
    "kind": "Synthetic actual rows retained before ordinary business iteration; excludes credentials and message text",
    "tables": {},
    "blobs": {},
}
with sqlite3.connect(
    (TRIAL / "data/application.sqlite3").as_uri() + "?mode=ro", uri=True
) as connection:
    connection.row_factory = sqlite3.Row
    for name, fields in allowed.items():
        columns = ", ".join('"' + field + '"' for field in fields)
        data["tables"][name] = [
            dict(row) for row in connection.execute(f'SELECT {columns} FROM "{name}" ORDER BY id')
        ]
for row in data["tables"]["files"]:
    path = (TRIAL / "data/files" / row["id"]).resolve()
    path.relative_to((TRIAL / "data/files").resolve())
    data["blobs"][row["id"]] = hashlib.sha256(path.read_bytes()).hexdigest()
target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
print(
    json.dumps(
        {
            "rows": {name: len(rows) for name, rows in data["tables"].items()},
            "blobs": len(data["blobs"]),
        }
    )
)
