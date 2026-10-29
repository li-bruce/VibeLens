"""Observe the supplied controlled fault without editing business or observer code."""

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "red-runtime"
sys.path[:0] = [str(ROOT), str(ROOT / "observer_runtime"), str(ROOT / "tooling")]
from app.web import create_app
from integrations.bo_adapter import BOTrace
from bo_observer.graph.behavior_model import capture
from bo_observer.protocol import validate_event, validate_snapshot
from bo_stategraph import BOStateGraph
from bo_stategraph.workflow import machine_snapshot
from scenarios import login_client, csrf


def main():
    OUT.mkdir(exist_ok=True)
    database = OUT / "trial.sqlite3"
    assert not database.exists(), "retain_previous_database_instead_of_overwriting"
    project = json.loads((ROOT / "bo_stategraph/project.json").read_text(encoding="utf-8"))
    build = capture(ROOT, project["model"])["build_id"]
    trace = BOTrace(ROOT, capacity=4096, sink=lambda value, kind: validate_event(value, project, build) if kind == "events" else validate_snapshot(value, project, build))
    app = create_app(ROOT, database, bo_trace=trace, bo_data=trace.data)
    service = app.extensions["sharing"]
    owner, _ = login_client(app, "linzhou")
    recipient, _ = login_client(app, "xuning")
    row = service.upload("linzhou", "controlled-diagnosis.txt", b"Controlled diagnosis fixture.\n")
    file_id = row["id"]
    service.share("linzhou", file_id, "xuning")
    old_url = f"/files/{file_id}/download"
    before_download = recipient.get(old_url)

    def facts():
        with closing(sqlite3.connect(database)) as connection:
            row = connection.execute("SELECT owner_id,filename,state,revision,sha256,journal FROM files WHERE id=?", (file_id,)).fetchone()
            grants = connection.execute("SELECT file_id,recipient_id FROM shares WHERE file_id=? ORDER BY recipient_id", (file_id,)).fetchall()
        return {"owner_id": row[0], "filename": row[1], "state": row[2], "revision": row[3], "sha256": row[4], "journal": json.loads(row[5]), "grants": [list(value) for value in grants]}

    before = facts()
    revoked = owner.post(f"/files/{file_id}/revoke", data={"csrf": csrf(owner), "recipient_id": "xuning"})
    success_shown = "共享已取消" in owner.get("/").get_data(as_text=True)
    after = facts()
    after_download = recipient.get(old_url)
    own_download = owner.get(old_url)
    trace.close()
    actual = service.store.snapshots()
    machine = machine_snapshot(actual, build)
    graph = BOStateGraph(project["model"], build_id=build, mode="drive", instance_provider=lambda: machine)
    graph.bo_require_definition(service.workflow.executor.bo_definition)
    public = graph.bo_export(runtime={"machine": machine})
    payload = {"controlled_fault": True, "build_id": build, "file_id": file_id, "before": before, "after": after,
        "http": {"before_download": before_download.status_code, "revoke": revoked.status_code, "success_notice_shown": success_shown,
                 "stale_download_after_revoke": after_download.status_code, "owner_download_after_revoke": own_download.status_code,
                 "stale_bytes_match_prior_download": after_download.data == before_download.data},
        "events": trace.events, "state_snapshots": trace.snapshots, "policy_evaluations": trace.evaluations,
        "public_export": public, "observer_errors": {"adapter": trace.errors, "transport": trace.probe.bo_errors, "dropped": trace.probe.bo_dropped, "data": trace.data.bo_errors}}
    (OUT / "observations.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    selected = [event for event in trace.events if event["node"] in {"revoke", "db_delete_share", "db_revoke_state", "policy:is_recipient", "policy:read_allowed", "download"}]
    summary = {key: payload[key] for key in ["controlled_fault", "build_id", "file_id", "before", "after", "http", "observer_errors"]}
    summary["relevant_runtime_events"] = [{key: event.get(key) for key in ["id", "node", "phase", "entity", "inputs", "outputs", "revision"]} for event in selected]
    summary["actual_native_states"] = [item["state"] for item in trace.snapshots]
    summary["actual_native_guards"] = [item["guards"] for item in trace.snapshots]
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    service.store.engine.dispose()
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
