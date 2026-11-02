"""Freeze actual evidence without accepting, editing or replaying business work."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def collect():
    for name, path in (("final-view.json", "/api/view"), ("final-export.json", "/api/stategraph/export"), ("final-recordings.json", "/api/recordings")):
        with urllib.request.urlopen("http://127.0.0.1:8983" + path, timeout=30) as response:
            save(name, json.load(response))
    listing = read(OUT / "final-recordings.json")
    assert not listing.get("active"), "Do not silently abandon an active recording"
    current = {}
    for summary in listing["recordings"]:
        with urllib.request.urlopen("http://127.0.0.1:8983/api/recordings/" + summary["id"], timeout=30) as response:
            value = json.load(response)
        filename = "raw-recording-" + summary["id"] + ".json"
        save(filename, value)
        current[summary["id"]] = {"file": filename, "events": len(value["events"]), "status": value["status"], "gaps": value["gaps"]}
    full = read(OUT / "actual-recording.json")
    focused = read(OUT / "focused-recording.json")
    assert read(OUT / ("raw-recording-" + full["id"] + ".json"))["events"] == full["events"]
    assert read(OUT / ("raw-recording-" + focused["id"] + ".json"))["events"] == focused["events"]
    verify = read(ROOT / "resume-first-integration-20261031/verification.json")
    live = read(OUT / "final-view.json")
    save("freeze-verification.json", {"disposition": "frozen_before_acceptance_by_explicit_request", "accept_performed": False,
        "accepted_json_exists": (ROOT / "resume-first-integration-20261031/accepted.json").exists(),
        "active_change": read(ROOT / ".stategraph/active.json"), "candidate_id": verify["candidate_id"],
        "build_id": live["manifest"]["build_id"], "binding_status": live["binding_status"],
        "four_category_receipt": {key: value["status"] for key, value in verify["reports"].items()},
        "closed_calls_in_normal_gate": verify["reports"]["mapping"]["invocation_closure"]["closed_calls"],
        "normal_gate_limit": "Configured complete-run scenarios pass; they do not establish focused recording invocation ownership or all Web acceptance items.",
        "live_events": len(live["events"]), "health": live["health"], "recordings": current,
        "full_recording_ownership": {key: value for key, value in read(OUT / "general-ownership-audit.json").items()
                                     if key not in ("checks", "point_checks", "root_event_ids")},
        "focused_evidence": read(OUT / "focused-capture-result.json"), "builder_audit": read(OUT / "builder-audit.json"),
        "business_user": "coordinating AI simulation; not independent human acceptance",
        "baseline_sha256": digest(ROOT / "resume-first-integration-20261031/baseline.json"),
        "latest_user_choice": "Allows local recordings to truthfully disclose missing ownership. This updates the acceptance criterion but does not explicitly revoke the prior freeze instruction."})
    print(json.dumps({"valid": True, "live_events": len(live["events"]), "recordings": current, "accept_performed": False}))

def archive():
    before = read(OUT / "integrity-before.json")
    changed = [name for name, value in before.items() if not (ROOT / name).is_file() or digest(ROOT / name) != value]
    assert not changed, changed
    save("integrity-after.json", {"valid": True, "protected_files": len(before), "changed": changed})
    assert not (ROOT / "resume-first-integration-20261031/accepted.json").exists()
    with sqlite3.connect(ROOT / "var/team-files.sqlite3") as origin, sqlite3.connect(OUT / "sqlite-snapshot.sqlite3") as target:
        origin.backup(target)
    source = []
    for directory in ("app", "tooling", "integrations", "observer_runtime", "bo_stategraph", "static", "templates", ".stategraph", "resume-first-integration-20261031"):
        source.extend(path for path in (ROOT / directory).rglob("*") if path.is_file() and "__pycache__" not in path.parts
                      and not path.relative_to(ROOT).as_posix().startswith(("bo_stategraph/config/views/", "bo_stategraph/config/control/")))
    source.extend(path for path in ROOT.iterdir() if path.is_file() and path.suffix not in (".env",))
    source.append(ROOT / "var/team-files.sqlite3")
    evidence = [path for path in OUT.rglob("*") if path.is_file() and "__pycache__" not in path.parts
                and path.name not in ("source-runtime-snapshot.zip", "freeze-manifest.json", "freeze-archive.stdout.log", "freeze-archive.stderr.log", "freeze-archive.command.json", "freeze-archive.result.json")]
    members = sorted(set(source + evidence))
    target = OUT / "source-runtime-snapshot.zip"
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as archive_file:
        for path in members:
            archive_file.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as archive_file:
        assert archive_file.testzip() is None
        assert not any(name.endswith("session-secret") or name.endswith(".env") for name in archive_file.namelist())
        assert "resume-first-integration-20261031/baseline.json" in archive_file.namelist()
    save("freeze-manifest.json", {"source_files": {path.relative_to(ROOT).as_posix(): digest(path) for path in source},
        "evidence_files": {path.relative_to(OUT).as_posix(): digest(path) for path in evidence},
        "archive": {"path": target.name, "sha256": digest(target), "files": len(members), "integrity_checked": True},
        "protected_files": len(before), "protected_changed": changed,
        "privacy_exclusions": ["session-secret and environment credentials", "root dependency cache", "personal view/control files remain on disk and in retained review snapshots", "older review trees remain intact and separately hashed"]})
    print(json.dumps({"valid": True, "protected_files": len(before), "archive_files": len(members), "archive_sha256": digest(target)}))

if __name__ == "__main__":
    collect() if sys.argv[1] == "collect" else archive()
