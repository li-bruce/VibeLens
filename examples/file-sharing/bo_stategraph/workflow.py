"""Project-local declaration driver and actual-storage projection."""

import json
from pathlib import Path
from .native_executor import BOExecutor
from app.predicates import operation_allowed, has_recipients


class FileWorkflow:
    def __init__(self, root: Path):
        self.project = json.loads((root / "bo_stategraph/project.json").read_text(encoding="utf-8"))
        self.machine = self.project["model"]["machine"]
        self.executor = BOExecutor(self.machine, {"operation_allowed": operation_allowed, "has_recipients": has_recipients})

    def step(self, state: str, event: str, context: dict, allowed: bool):
        return self.executor.step(state, event, context, {"allowed": allowed})


def file_context(row: dict):
    return {name: row[name] for name in ("owner_id", "filename", "size", "grant_count")}


def machine_snapshot(rows: list, build_id: str):
    return {"configurations": [{"attempt": row["id"], "phase": row["state"],
        "state_revision": row["revision"], "revision": row["revision"], "param_version": 1,
        "run_build_id": build_id, "context": file_context(row), "journal": row["journal"]}
        for row in rows]}
