"""Consume the canonical declaration in the actual native file workflow."""
import json
from .native_executor import BOExecutor
from app.predicates import operation_allowed

class FileWorkflow:
    def __init__(self, root):
        self.machine = json.loads((root / "bo_stategraph/project.json").read_text(encoding="utf-8-sig"))["model"]["machine"]
        self.executor = BOExecutor(self.machine, {"operation_allowed": operation_allowed})

    def step(self, state: str, event: str, context: dict, allowed: bool) -> dict:
        return self.executor.step(state, event, context, {"allowed": allowed})

def file_context(row: dict) -> dict:
    return {name: row[name] for name in ("uploader_id", "reviewer_id", "recipient_id", "size")}

def machine_snapshot(rows: list, build_id: str) -> dict:
    return {"configurations": [{"attempt": row["id"], "phase": row["state"],
        "state_revision": row["revision"], "revision": row["revision"], "param_version": 1,
        "run_build_id": build_id, "context": file_context(row), "journal": row["journal"]} for row in rows]}
