"""Verify real HTTP reason handling and retain a drained current-build recording."""
import hashlib
import html
import json
from pathlib import Path
import sqlite3
from http_matrix import Client
from record_helpers import get, post, drained

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
REASON = "  缺少签字页。\n请补齐附件 <原件>。  "

def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")

def main():
    clients = []
    for actor in ("alice", "ben", "cara", "dan"):
        clients.append(Client(actor))
        drained()
    a, b, c, d = clients
    fixture = {}
    for kind in ("reject", "approve"):
        name = "browser-reason-" + kind + "-20261101.txt"
        status, body = a.upload(name)
        assert status == 201
        fixture[kind] = {"filename": name, "id": json.loads(body)["id"]}
        drained()
    save("browser-fixture.json", fixture)
    before_raw, before = drained()
    save("live-build.json", {"build_id": before["manifest"]["build_id"], "binding_status": before["binding_status"]})
    started = post("/api/recordings/start", {"label": "Reject with original reason and approve without reason"})
    save("recording-start.json", started)
    checks = []
    def check(name, result, expected):
        status, body = result
        checks.append({"case": name, "status": status, "expected": expected})
        assert status == expected, checks[-1]
        return json.loads(body) if body.startswith(b"{") else body
    rejected = check("upload for rejection", a.upload("reason-recorded-20261101.txt"), 201)["id"]
    path = "/files/" + rejected
    check("empty reason", b.post(path + "/review", {"decision": "reject"}), 400)
    check("whitespace reason", b.post(path + "/review", {"decision": "reject", "reason": " \n "}), 400)
    check("unrelated reviewer", c.post(path + "/review", {"decision": "reject", "reason": REASON}), 403)
    rejected_result = check("verbatim rejection", b.post(path + "/review", {"decision": "reject", "reason": REASON}), 200)
    assert rejected_result["rejection_reason"] == REASON
    metadata = check("uploader details JSON", a.request(path), 200)
    assert metadata["rejection_reason"] == REASON
    page = check("uploader details HTML", a.request(path, headers={"Accept": "text/html"}), 200)
    assert ('<div class="reason-text">' + html.escape(REASON) + '</div>').encode() in page
    check("other actor cannot read reason", d.request(path), 403)
    check("closed rejection", b.post(path + "/review", {"decision": "reject", "reason": "Replacement"}), 409)
    approved = check("upload for approval", a.upload("reason-approve-recorded-20261101.txt"), 201)["id"]
    approved_result = check("approve without reason", b.post("/files/" + approved + "/review", {"decision": "approve"}), 200)
    assert approved_result["rejection_reason"] == ""
    _, before_stop = drained()
    stopped = post("/api/recordings/stop", {})
    save("recording-stop.json", stopped)
    raw = get("/api/recordings/" + stopped["id"])
    (OUT / "actual-recording.json").write_bytes(raw)
    recording = json.loads(raw)
    assert recording["status"] == "stopped" and recording["producer_settlement"]["flushed"]
    events = recording["events"]
    entries = {e["call_id"]: e for e in events if e["phase"] == "enter"}
    exits = {e["call_id"]: e for e in events if e["phase"] in ("return", "error", "exception", "commit", "change")}
    assert set(entries) <= set(exits)
    assert not [e for e in events if e.get("parent_call_id") and e["parent_call_id"] not in entries]
    interval_ids = {e["id"] for e in events}
    assert not [g for g in recording["ownership_gaps"] if g["event"] in interval_ids]
    review = next(e for e in entries.values() if e["node"] == "review_file" and e["inputs"].get("reason") == REASON and e["inputs"].get("actor") == "ben")
    result = exits[review["call_id"]]
    assert result["outputs"] == {"state": "rejected", "revision": 2, "rejection_reason": REASON}
    transition = next(e for e in entries.values() if e["node"] == "state_transition" and e["inputs"]["event"] == "reject")
    assert transition["inputs"]["before"] == "pending" and exits[transition["call_id"]]["outputs"]["after"] == "rejected"
    reason_check = next(e for e in events if e["node"] == "review_reason_check" and e.get("outputs", {}).get("rejection_reason") == REASON)
    assert reason_check["inputs"]["reason"] == REASON and reason_check["outputs"]["valid"] is True
    with sqlite3.connect(ROOT / "var/team-files.sqlite3") as db:
        db.row_factory = sqlite3.Row
        rows = [dict(db.execute("SELECT id,state,revision,rejection_reason,journal FROM files WHERE id=?", (fid,)).fetchone()) for fid in (rejected, approved)]
    assert [(r["state"], r["revision"], r["rejection_reason"]) for r in rows] == [("rejected", 2, REASON), ("approved", 2, "")]
    assert [s["event"] for s in json.loads(rows[0]["journal"])] == ["submit", "reject"]
    raw_path = ROOT / "bo_stategraph/data/recordings" / (stopped["id"] + ".json")
    evidence = {"valid": True, "build_id": recording["build_id"], "recording_id": stopped["id"], "file_id": rejected,
        "approved_file_id": approved, "original_reason": REASON, "checks": checks, "sqlite_rows": rows,
        "interval_events": len(events), "closed_interval_calls": len(entries), "interval_missing_parents": 0,
        "interval_ownership_gaps": 0, "prior_context_ownership_gaps": len(recording["ownership_gaps"]),
        "raw_gaps": recording["gaps"], "producer_settlement": recording["producer_settlement"],
        "producer_pending_before_stop": before_stop["health"]["producer"]["pending"],
        "raw_recording_path": str(raw_path), "raw_recording_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "witness_ids": [review["id"], reason_check["id"], transition["id"], exits[transition["call_id"]]["id"], result["id"]]}
    assert evidence["build_id"] == before["manifest"]["build_id"]
    save("live-reason.json", evidence)
    print(json.dumps({k: evidence[k] for k in ("valid", "build_id", "recording_id", "interval_events", "closed_interval_calls")}))

if __name__ == "__main__":
    main()
