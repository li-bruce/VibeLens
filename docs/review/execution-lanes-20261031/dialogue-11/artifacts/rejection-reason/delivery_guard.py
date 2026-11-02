"""Check the final live build, exact original text and preserved historical evidence."""
import hashlib
import json
from pathlib import Path
import sqlite3
from record_helpers import get, drained

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
def read(path): return json.loads(path.read_text(encoding="utf-8-sig"))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

verification = read(OUT / "verify-final.result.json")
assert verification["valid"] and all(r["status"] == "passed" for r in verification["reports"].values())
for name in ("negative-controls.json", "reason-concurrency.json", "migration-rehearsal.json", "schema-migration.json", "native-api-comparison.json"):
    assert read(OUT / name)["valid"], name
baseline = ROOT / "resume-first-integration-20261031/baseline.json"
assert sha(baseline) == "8544e5bd79f050e8ec314274b75d9e6aa903b2675a9a1f6ddb97bc6cca7d4e5b"
new_baseline = ROOT / ".stategraph/rejection-reason-20261101/baseline.json"
scope = read(new_baseline)
assert scope["id"] == "bfd9632113b00302ce0b0b0a9594864e3928b4a0e435d7d1867b73330908be81"
assert set(scope["requested_requirements"]) == {"R_REVIEW", "R_REASON"}
protected = read(OUT / "protected-before.json")
changed = [name for name, digest in protected.items() if not (ROOT / name).is_file() or sha(ROOT / name) != digest]
assert not changed, changed
migration = read(OUT / "schema-migration.json")
with sqlite3.connect(OUT / "before-schema.sqlite3") as before, sqlite3.connect(ROOT / "var/team-files.sqlite3") as after:
    for table, columns in migration["old_columns"].items():
        selection = ",".join('"' + name + '"' for name in columns)
        expected = {row[0]: row for row in before.execute("SELECT " + selection + " FROM " + table)}
        actual = {row[0]: row for row in after.execute("SELECT " + selection + " FROM " + table)}
        assert all(actual.get(key) == value for key, value in expected.items()), table
    legacy_rejected = [r[0] for r in before.execute("SELECT id FROM files WHERE state='rejected'")]
    assert all(after.execute("SELECT rejection_reason FROM files WHERE id=?", (fid,)).fetchone() == ("",) for fid in legacy_rejected)
    fixture = read(OUT / "final-browser-fixture.json")
    owner = read(OUT / "final-uploader-details-dom.json")
    rejected = after.execute("SELECT state,revision,rejection_reason FROM files WHERE id=?", (fixture["reject"]["id"],)).fetchone()
    approved = after.execute("SELECT state,revision,rejection_reason FROM files WHERE id=?", (fixture["approve"]["id"],)).fetchone()
assert rejected == ("rejected", 2, owner["reason"])
assert owner["reason"] == "  缺少签字页，请补齐附件 <原件>。  "
assert owner["account"].strip() == "alice" and owner["badge"] == "未通过" and owner["whiteSpace"] == "pre-wrap"
assert "&lt;原件&gt;" in owner["markup"] and approved == ("approved", 2, "")
empty = read(OUT / "final-browser-empty-reason.json")
assert empty["required"] and empty["valueMissing"] and empty["badge"] == "待审核"
approval = read(OUT / "final-browser-approved-card.json")
assert approval["before"]["value"] == "" and approval["after"]["badge"] == "已通过"
live = read(OUT / "final-live-reason.json")
recording = read(OUT / "final-actual-recording.json")
assert live["valid"] and recording["status"] == "stopped" and live["producer_settlement"]["flushed"]
assert live["build_id"] == recording["build_id"] and live["producer_pending_before_stop"] == 0
assert sha(Path(live["raw_recording_path"])) == live["raw_recording_sha256"]
older = read(OUT / "live-reason.json")
assert sha(Path(older["raw_recording_path"])) == older["raw_recording_sha256"]
events = {e["id"]: e for e in recording["events"]}
witnesses = read(OUT / "final-replay-witnesses.json")
assert [w["eventId"] for w in witnesses] == live["witness_ids"]
assert all(w["eventId"] in events for w in witnesses)
assert events[witnesses[0]["eventId"]]["inputs"]["reason"] == live["original_reason"]
assert events[witnesses[1]["eventId"]]["outputs"]["rejection_reason"] == live["original_reason"]
assert events[witnesses[-1]["eventId"]]["outputs"]["rejection_reason"] == live["original_reason"]
graph = read(OUT / "final-runtime-graph-dom.json")
assert any(n["id"] == "review_file" for n in graph["nodes"])
assert {r["id"] for r in graph["recordings"]} == {"", live["recording_id"]}
_, view = drained()
assert view["manifest"]["build_id"] == live["build_id"] and view["binding_status"]["status"] == "current"
before_ids = [e["id"] for e in view["events"]]
for route in ("/api/view", "/api/stategraph/export", "/api/code/graph?projection=all&limit=1500&depth=2", "/api/recordings/" + live["recording_id"]):
    get(route)
after_view = json.loads(get("/api/view"))
assert before_ids == [e["id"] for e in after_view["events"]]
assert sha(Path(live["raw_recording_path"])) == live["raw_recording_sha256"]
health = after_view["health"]
limited = read(OUT / "queue-limit-evidence.json")
assert limited["valid"] and limited["health"]["producer"]["dropped"] > 0
assert limited["health"]["producer"]["run_id"] != health["producer"]["run_id"]
(OUT / "settled-health.json").write_text(json.dumps(health, indent=2), encoding="utf-8")
assert health["errors"] == health["dropped"] == health["producer"]["errors"] == health["producer"]["dropped"] == 0
assert read(OUT / "gate11-readiness.json")["valid"]
result = {"valid": True, "candidate_id": verification["candidate_id"], "build_id": live["build_id"],
    "old_baseline_sha256": sha(baseline), "new_baseline_sha256": sha(new_baseline), "protected_files": len(protected),
    "protected_changed": changed, "all_preexisting_database_columns_and_bytes_unchanged": True,
    "legacy_reasons_not_invented": len(legacy_rejected), "browser_exact_reason_matches_sqlite": True,
    "current_recording_id": live["recording_id"], "interval_events": live["interval_events"],
    "closed_interval_calls": live["closed_interval_calls"], "raw_recording_unchanged": True,
    "observer_reads_added_zero_events": True, "health": health,
    "earlier_queue_limited_session": limited["health"],
    "limits": ["Bounded pre-start recording context retains historical ownership gaps.",
        "The rapid large-list GUI workload dropped 2701 observer events in the preceding session. Its counters/raw logs and correct business effects remain; the same-build restart does not repair those historical gaps.",
        "Actual HTTP recording and GUI fixtures are separate operations on the same final build.",
        "Earlier accepted geometry limitations remain; no new exhaustive viewer geometry claim.",
        "Business answers are coordinating-AI simulations, not independent human or production acceptance."]}
(OUT / "delivery-guard.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps({k: result[k] for k in ("valid", "candidate_id", "build_id", "protected_files", "observer_reads_added_zero_events")}))
