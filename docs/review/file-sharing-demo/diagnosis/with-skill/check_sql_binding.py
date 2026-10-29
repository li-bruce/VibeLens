"""Capture the real DBAPI DELETE bindings without changing application observers."""

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
from sqlalchemy import event

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.web import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["before", "after"])
    args = parser.parse_args()
    out = ROOT / "review/diagnosis"
    database = out / ("sql-binding-" + args.phase + ".sqlite3")
    assert not database.exists()
    app = create_app(ROOT, database)
    service = app.extensions["sharing"]
    statements = []

    def capture(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("DELETE FROM SHARES"):
            statements.append({"sql": statement, "dbapi_parameters": list(parameters),
                               "compiled_parameters": context.compiled_parameters, "executemany": executemany})

    event.listen(service.store.engine, "before_cursor_execute", capture)
    row = service.upload("linzhou", "binding-check.txt", b"Independent DBAPI fixture.\n")
    service.share("linzhou", row["id"], "xuning")
    result = service.revoke("linzhou", row["id"], "xuning")
    event.remove(service.store.engine, "before_cursor_execute", capture)
    with closing(sqlite3.connect(database)) as connection:
        remaining = connection.execute("SELECT recipient_id FROM shares WHERE file_id=?", (row["id"],)).fetchall()
    report = {"phase": args.phase, "controlled_fault": True, "file_id": row["id"], "actor": "linzhou", "requested_recipient": "xuning",
              "real_driver_statements": statements, "remaining_recipients": [value[0] for value in remaining], "state": result["state"],
              "boundary": "Read-only SQLAlchemy execution listener in this diagnostic harness; application and observer code are unmodified."}
    (out / ("sql-binding-" + args.phase + ".json")).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    service.store.engine.dispose()


if __name__ == "__main__":
    main()
