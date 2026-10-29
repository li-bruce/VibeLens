"""Audit preservation and collect this round's receipts without nested archives."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
read = lambda path: json.loads(path.read_text(encoding="utf-8-sig"))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

before, parity = read(OUT / "before.json"), read(OUT / "parity.json")
rows = [{"path": name, "before": old, "after": sha(ROOT / name),
         "byte_identical": old == sha(ROOT / name)} for name, old in before["source_files"].items()]
changed = [row["path"] for row in rows if not row["byte_identical"]]
assert sorted(changed) == sorted(["bo_stategraph/runtime-version.json", "manifest.json", "ownership.json",
                                  "static/graph/conversation-controls.js", "static/graph/viewer.js",
                                  "review/implementation-version.json"]), changed
for group in ("protected_files", "protected_test_files", "old_raw_recordings"):
    assert all(sha(ROOT / name) == old for name, old in before[group].items()), group
model = read(ROOT / "bo_stategraph/project.json")["model"]
declarations = {}
for part, old in before["declaration_hashes"].items():
    data = json.dumps(model[part], ensure_ascii=False, sort_keys=True, indent=2).encode()
    assert hashlib.sha256(data).hexdigest() == old, part
    (OUT / ("after-" + part + ".json")).write_bytes(data)
    declarations[part] = {"before": old, "after": old, "byte_identical": True}
write("byte-comparison.json", {"files": rows, "changed_files": changed,
      "protected_files_unchanged": len(before["protected_files"]),
      "original_test_scripts_unchanged": len(before["protected_test_files"]),
      "declarations": declarations, "project_byte_identical": True})

for name, original in before["history_archives"].items():
    assert sha(ROOT / name) == original["sha256"], name
saved = OUT / before["new_archive"]["path"]
assert sha(saved) == before["new_archive"]["sha256"]
with zipfile.ZipFile(saved) as archive:
    assert not any(name.lower().endswith(".zip") for name in archive.namelist())
    for name, old in before["evidence_files"].items():
        assert hashlib.sha256(archive.read(name)).hexdigest() == old, name
        if name.startswith(("review/framework-upgrade-3458366/", ".stategraph/framework-upgrade-3458366/")):
            assert sha(ROOT / name) == old, name
write("preservation-check.json", {"status": "passed", "historical_archives_unchanged": len(before["history_archives"]),
      "old_raw_recordings_unchanged": len(before["old_raw_recordings"]),
      "previous_receipts_preserved": len(before["evidence_files"]), "nested_zip_members": 0,
      "references": "previous-evidence-index.json", "previous_receipt_archive": before["new_archive"],
      "note": "Shared latest/gate pointers advance; their previous bytes are in the receipt archive. Historical ZIPs stay in place."})
for name in ("architecture", "scan", "inspect", "verify", "accept", "check"):
    shutil.copyfile(ROOT / "review" / ("gate-" + name + ".json"), OUT / ("gate-" + name + ".json"))
verify, accepted, checked = [read(OUT / ("gate-" + name + ".json")) for name in ("verify", "accept", "check")]
assert all(x["valid"] for x in (verify, accepted, checked))
assert verify["candidate_id"] == accepted["candidate_id"] == checked["candidate_id"]
change = ROOT / ".stategraph/framework-upgrade-3052e03"
observations = json.loads(read(change / "checks/observations.json")["stdout"])
tests = read(change / "checks/test-0.json")
assert tests["exit_code"] == 0 and "35 passed" in tests["stdout"]
assert len(observations["runs"]) == 84
assert verify["reports"]["business"]["assertions"] == {"required": 282, "executed": 282}
browser, audit, keyboard, details, controls = [read(OUT / name) for name in (
    "browser-native/report.json", "evidence-checks.json", "keyboard-source-acceptance.json",
    "keyboard-details.json", "controls/report.json")]
assert all(x["status"] == "passed" for x in (browser, audit, keyboard, details, controls))
source_selection = read(OUT / "controls/source-selection-report.json")
assert source_selection["status"] == "passed" and source_selection["advanced_details_enabled"]
assert source_selection["last_authorized_replay_restored"]
assert source_selection["observer_control_business_event_delta"] == 0
assert len(audit["checks"]) == 10
assert observations["build_id"] == browser["build_id"] == audit["build_id"] == parity["after_build"] == controls["build_id"]
assert all(row["byte_identical"] for row in read(OUT / "unchanged-test-copies.json").values())
version = read(ROOT / "bo_stategraph/runtime-version.json")
assert all(sha(ROOT / name) == old for name, old in version["files"].items())
post = read(OUT / "post-upgrade-plan.json")
assert post["valid"] and not post["changes"] and not post["conflicts"]
source = ROOT.parent / "vibelens-control-fix"
head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
assert head == parity["canonical_revision"]
assert not subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True)
bundle = OUT / "upgraded-source.zip"
if not bundle.exists():
    with zipfile.ZipFile(bundle, "x", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(before["source_files"]):
            assert not name.startswith(("bo_stategraph/config/control/", "bo_stategraph/config/views/conversations/"))
            archive.write(ROOT / name, name)
with zipfile.ZipFile(bundle) as archive:
    assert not any(name.lower().endswith(".zip") for name in archive.namelist())
    assert all(hashlib.sha256(archive.read(name)).hexdigest() == sha(ROOT / name) for name in before["source_files"])
summary = {"status": "independent_project_acceptance_passed", "canonical_revision": head,
    "candidate_id": checked["candidate_id"], "build_id": parity["after_build"],
    "native_upgrade": True, "shims": False, "reports": {key: row["status"] for key, row in verify["reports"].items()},
    "formal_command": ".venv/Scripts/python.exe -B -X utf8 tooling/check.py --accept",
    "pytest": 35, "pytest_seconds": float(re.search(r"35 passed in ([0-9.]+)s", tests["stdout"]).group(1)),
    "scenario_mode_runs": 84, "assertions": 282,
    "mapping_witnesses": verify["reports"]["mapping"]["witnesses"],
    "projection_checks": verify["reports"]["mapping"]["projection_checks"],
    "enabled_mode_events": sum(len(run["events"]) for run in observations["runs"] if run["mode"] == "on"),
    "evidence_counterexamples": len(audit["checks"]), "keyboard_source_acceptance": keyboard["status"],
    "keyboard_details": details["status"], "native_controls": controls["status"],
    "explicit_source_control": source_selection["status"],
    "scripted_user_not_human_confirmation": True, "recording_id": browser["recording_id"],
    "recorded_events": browser["event_count"], "recorded_frames": browser["last_flush_response"]["enqueued_snapshots"],
    "drain_seconds": browser["drain_wait_seconds"], "errors_dropped_gaps": [0, 0, 0],
    "observer_generated_business_events": controls["observer_control_business_event_delta"],
    "source_bundle": {"file": bundle.name, "sha256": sha(bundle), "files": len(before["source_files"])},
    "privacy": "Local raw evidence only; controls/ and private control/view config contain session secrets. No public evidence export was prepared. Main archive must exclude private config and redact tokens using hashes/fingerprints.",
    "performance": "No real-time throughput acceptance; historical drains 363.125, 53.775 and 121.584 seconds remain preserved.",
    "upstream_receipt": "upstream-receipt-check.json; clean HEAD, full log and 240 Skill hashes verified separately.",
    "checked_at": datetime.now(timezone.utc).isoformat()}
write("summary.json", summary)
print(json.dumps({key: summary[key] for key in ("status", "candidate_id", "build_id", "pytest_seconds", "drain_seconds")}))
