"""Save actual pre-iteration columns without changing the earlier row snapshot."""

import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
TRIAL = ROOT.parent / "VibeLensTrials/lifecycle-dialogue-20261031"
BASE = ROOT / "docs/review/dialogue-acceptance-20261031/iteration/original-v1-ready"
target = BASE / "authoritative-columns.json"
if target.exists():
    raise ValueError("The pre-iteration column snapshot already exists")
old_structure = json.loads((BASE / "sqlite-structure.json").read_text(encoding="utf-8"))
expected = next(
    row["sql"] for row in old_structure if row["type"] == "table" and row["name"] == "shares"
)
with sqlite3.connect(
    (TRIAL / "data/application.sqlite3").as_uri() + "?mode=ro", uri=True
) as connection:
    current = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='shares'"
    ).fetchone()[0]
    assert (
        current == expected
    ), "The native schema changed before the confirmation baseline was retained"
    names = [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    columns = {
        name: [
            row[1]
            for row in connection.execute('PRAGMA table_info("' + name.replace('"', '""') + '")')
        ]
        for name in names
    }
target.write_text(json.dumps(columns, indent=2) + "\n", encoding="utf-8")
print(json.dumps(columns))
