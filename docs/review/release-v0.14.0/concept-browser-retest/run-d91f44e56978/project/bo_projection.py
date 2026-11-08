"""Read complete native grant snapshots without executing application policy."""

import sqlite3
import json
from contextlib import closing


def bo_native_state(database, build_id):
    """Read the actual persisted grant identity, activity and revision in one query."""
    with closing(sqlite3.connect(database)) as connection:
        rows = connection.execute(
            "SELECT file_id, recipient, active, revision FROM grants"
        ).fetchall()
    return {
        "configurations": [
            {
                "attempt": json.dumps([file_id, recipient], separators=(",", ":")),
                "phase": "active" if active else "inactive",
                "state_revision": revision,
                "run_build_id": build_id,
                "context": {},
            }
            for file_id, recipient, active, revision in rows
        ]
    }
