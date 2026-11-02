"""Freeze new real evidence and describe the shared causal-grouping defect."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def collect():
    for name, path in (("final-view.json", "/api/view"), ("final-export.json", "/api/stategraph/export"), ("final-recordings.json", "/api/recordings")):
        with urllib.request.urlopen("http://127.0.0.1:8983" + path, timeout=30) as response:
            save(name, json.load(response))
    recording = read(OUT / "actual-recording-recovered.json")
    timeline = read(OUT / "failure-timeline-timeline.json")
    events = {event["id"]: event for event in recording["events"]}
    roots = Counter(events.get(item["root"], {}).get("node", "unknown") for item in timeline["executions"])
    phantom = []
    for item in timeline["executions"]:
        event = events.get(item["root"], {})
        if event.get("node") != "http_request":
            phantom.append({"execution": item, "duration_ms": item["end"] - item["start"], "root_event": event})
    data = [event for event in recording["events"] if event["node"].startswith("db_")]
    issue = {"disposition": "shared_framework_gap_blocks_acceptance", "execution_count": len(timeline["executions"]),
        "roots_by_node": dict(roots), "bands": timeline["groups"], "rows": len(timeline["rows"]),
        "non_http_root_count": len(phantom), "phantom_root_examples": phantom,
        "recording": {"id": recording["id"], "events": len(recording["events"]), "gaps": recording["gaps"]},
        "data_events": len(data), "data_events_with_parent": sum(bool(event.get("parent_call_id")) for event in data),
        "boundary": "Rows and gestures were exercised, but phase=decision facts without an invocation lifecycle or native parent must not become long execution intervals. General record/policy causal ownership requires a canonical repair; never infer it from timestamps.",
        "repairs_allowed_here": False}
    save("shared-causal-grouping-gap.json", issue)
    live = read(OUT / "final-view.json")
    verify = read(ROOT / "resume-first-integration-20261031/verification.json")
    save("freeze-verification.json", {"disposition": "frozen_before_acceptance_pending_shared_causal_grouping_repair",
        "accept_performed": False, "accepted_json_exists": (ROOT / "resume-first-integration-20261031/accepted.json").exists(),
        "active_change": read(ROOT / ".stategraph/active.json"), "candidate_id": verify["candidate_id"],
        "build_id": live["manifest"]["build_id"], "binding_status": live["binding_status"],
        "four_category_receipt": {key: value["status"] for key, value in verify["reports"].items()},
        "four_category_limit": "Configured gates pass. They do not cover the shared record/policy parent and execution-group defect.",
        "live_events": len(live["events"]), "health": live["health"],
        "business_browser": read(OUT / "browser-flow.json"), "recording_receipt": read(OUT / "browser-recording-receipt.json"),
        "native_api_comparison": read(OUT / "native-api-comparison.json"),
        "parent_audit": {key: value for key, value in read(OUT / "runtime-parent-audit.json").items() if key not in ("parent_checks", "transaction_exception_examples")},
        "shared_gap": {key: value for key, value in issue.items() if key != "phantom_root_examples"},
        "core_export_execution": read(OUT / "core-execution.json"),
        "business_user": "coordinating AI simulation, not independent human acceptance",
        "baseline_sha256": digest(ROOT / "resume-first-integration-20261031/baseline.json")})
    print(json.dumps({"executions": len(timeline["executions"]), "root_nodes": dict(roots), "bands": timeline["groups"], "rows": len(timeline["rows"]), "data_parents": sum(bool(event.get("parent_call_id")) for event in data)}))

def archive():
    before = read(OUT / "integrity-before.json")
    changed = [name for name, value in before.items() if not (ROOT / name).is_file() or digest(ROOT / name) != value]
    assert not changed, changed
    save("integrity-after.json", {"valid": True, "protected_files": len(before), "changed": changed})
    source = []
    for directory in ("app", "tooling", "integrations", "observer_runtime", "bo_stategraph", "static", "templates", ".stategraph", "resume-first-integration-20261031"):
        source.extend(path for path in (ROOT / directory).rglob("*") if path.is_file() and "__pycache__" not in path.parts
            and not path.relative_to(ROOT).as_posix().startswith(("bo_stategraph/config/views/", "bo_stategraph/config/control/")))
    source.extend(path for path in ROOT.iterdir() if path.is_file())
    source.append(ROOT / "var/team-files.sqlite3")
    source = sorted(set(source))
    target = OUT / "source-runtime-snapshot.zip"
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as archive_file:
        for path in source:
            archive_file.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as archive_file:
        assert archive_file.testzip() is None
        assert not any(name.endswith("session-secret") for name in archive_file.namelist())
    save("freeze-manifest.json", {"source_files": {path.relative_to(ROOT).as_posix(): digest(path) for path in source},
        "archive": {"path": target.name, "sha256": digest(target), "files": len(source)},
        "new_evidence": {path.name: digest(path) for path in OUT.iterdir() if path.is_file() and path.name != "freeze-manifest.json"},
        "protected_files": len(before), "protected_changed": changed,
        "privacy_exclusions": ["session-secret", "dependency cache", "personal view/control files; retained separately in this local review", "historical review directories"]})
    print(json.dumps({"valid": True, "protected_files": len(before), "archive_files": len(source), "archive_sha256": digest(target)}))

if __name__ == "__main__":
    collect() if sys.argv[1] == "collect" else archive()
