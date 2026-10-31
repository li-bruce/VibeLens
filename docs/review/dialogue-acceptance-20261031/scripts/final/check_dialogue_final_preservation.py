"""Check old native rows/files/recordings after actual new-version operations."""

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
TRIAL = ROOT.parent / "VibeLensTrials/lifecycle-dialogue-20261031"
OUT = ROOT / "docs/review/dialogue-acceptance-20261031/iteration/original-v2-final-preservation-01.json"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    if OUT.exists():
        raise ValueError("Keep the earlier receipt; choose a new phase for a changed test")
    before = json.loads((TRIAL / "review/attempts/capture-viewer-mime-preservation-001.json").read_text(encoding="utf-8"))
    backup = (TRIAL / before["backup"] / "data/application.sqlite3").resolve()
    backup.relative_to(TRIAL.resolve())
    result = {"passed": False, "checks": []}
    try:
        with closing(sqlite3.connect(backup.as_uri() + "?mode=ro", uri=True)) as old, closing(
            sqlite3.connect((TRIAL / "data/application.sqlite3").as_uri() + "?mode=ro", uri=True)
        ) as current:
            for name, expected in before["tables"].items():
                quoted = '"' + name.replace('"', '""') + '"'
                query = "SELECT * FROM " + quoted + " ORDER BY id"
                previous = old.execute(query)
                columns = [column[0] for column in previous.description]
                rows = previous.fetchall()
                assert len(rows) == expected["rows"]
                assert sha(json.dumps(rows, ensure_ascii=False).encode()) == expected["sha256"]
                actual = current.execute(query)
                assert [column[0] for column in actual.description] == columns
                primary = columns.index("id")
                now = {row[primary]: row for row in actual.fetchall()}
                for row in rows:
                    assert now.get(row[primary]) == row, (name, row[primary])
                result["checks"].append({"name": name, "old_rows_unchanged": len(rows), "current_rows": len(now)})
        for label, directory, members in (
            ("attachments", TRIAL / "data/files", before["blobs"]),
            ("old recordings", TRIAL / "bo_stategraph/data/recordings", before["recordings"]),
        ):
            for name, expected in members.items():
                source = (directory / name).resolve()
                source.relative_to(directory.resolve())
                assert sha(source.read_bytes()) == expected, source.name
            result["checks"].append({"name": label, "old_files_unchanged": len(members)})
        for name, expected in before["baseline_hashes"].items():
            assert sha((TRIAL / name).read_bytes()) == expected, name
        result["checks"].append({"name": "All original change baselines remain byte-identical", "count": len(before["baseline_hashes"])})
        result["passed"] = True
    except Exception as error:
        result["error"] = repr(error)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    raise SystemExit(not result["passed"])


if __name__ == "__main__":
    main()
