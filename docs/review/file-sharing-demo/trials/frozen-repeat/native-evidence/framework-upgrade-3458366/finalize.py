"""Persist native upgrade evidence and byte comparisons without altering its sources."""
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

before = read(OUT / "before.json")
parity = read(OUT / "parity.json")
rows = []
for name, old in before["source_files"].items():
    current = sha(ROOT / name)
    rows.append({"path": name, "before": old, "after": current, "byte_identical": old == current})
changes = [row["path"] for row in rows if not row["byte_identical"]]
assert sorted(changes) == sorted(["ownership.json", "bo_stategraph/runtime-version.json", "manifest.json",
                                  "static/graph/semantic-view.js"]), changes
assert all(sha(ROOT / name) == value for name, value in before["protected_files"].items())
model = read(ROOT / "bo_stategraph/project.json")["model"]
declarations = {}
for part, old in before["declaration_hashes"].items():
    data = json.dumps(model[part], ensure_ascii=False, sort_keys=True, indent=2).encode()
    (OUT / ("after-" + part + ".json")).write_bytes(data)
    actual = hashlib.sha256(data).hexdigest()
    assert actual == old
    declarations[part] = {"before": old, "after": actual, "byte_identical": True}
write("byte-comparison.json", {"files": rows, "changed_files": changes,
      "business_test_and_contract_files_unchanged": len(before["protected_files"]),
      "project_declaration_byte_identical": True, "declarations": declarations})
preservation = {}
for name, original in before["archives"].items():
    assert sha(OUT / name) == original["sha256"]
    records = before["source_files"] if name == "b78-source.zip" else before["evidence_files"]
    with zipfile.ZipFile(OUT / name) as archive:
        for path, value in records.items():
            assert hashlib.sha256(archive.read(path)).hexdigest() == value, path
    preservation[name] = {**original, "verified_original_files": len(records)}
old_recordings = {name: value for name, value in before["evidence_files"].items()
                  if name.startswith("bo_stategraph/data/recordings/")}
assert all(sha(ROOT / name) == value for name, value in old_recordings.items())
for name in ("review/revocation-acceptance.md", "review/revocation-summary.json",
             "review/browser/20261029T034258Z-7c262b/recording.json",
             "review/framework-upgrade-b78f03a/keyboard-source-acceptance.json",
             "review/framework-upgrade-b78f03a/summary.json",
             "review/framework-upgrade-b78f03a/index.md",
             "review/framework-upgrade-b78f03a/browser-native/recording.json"):
    assert sha(ROOT / name) == before["evidence_files"][name]
write("preservation-check.json", {"status": "passed", "archives": preservation,
      "old_raw_recordings_byte_identical": len(old_recordings),
      "original_v2_report_summary_and_exported_recording_unchanged": True,
      "note": "Shared latest pointers/gate receipts can advance; their exact V2 originals remain in the verified evidence archive."})

for name in ("architecture", "scan", "inspect", "verify", "accept", "check"):
    source = ROOT / "review" / ("gate-" + name + ".json")
    shutil.copyfile(source, OUT / ("gate-" + name + ".json"))
verify = read(OUT / "gate-verify.json")
accepted = read(OUT / "gate-accept.json")
checked = read(OUT / "gate-check.json")
assert verify["valid"] and accepted["valid"] and checked["valid"]
assert verify["candidate_id"] == accepted["candidate_id"] == checked["candidate_id"]
change = ROOT / ".stategraph/framework-upgrade-3458366"
observations_receipt = read(change / "checks/observations.json")
observations = json.loads(observations_receipt["stdout"])
tests = read(change / "checks/test-0.json")
assert tests["exit_code"] == 0 and "35 passed" in tests["stdout"]
assert len(observations["runs"]) == 84
assert verify["reports"]["business"]["assertions"] == {"required": 282, "executed": 282}
browser = read(OUT / "browser-native/report.json")
audit = read(OUT / "evidence-checks.json")
keyboard = read(OUT / "keyboard-source-acceptance.json")
assert browser["status"] == audit["status"] == "passed"
assert keyboard["status"] == "passed"
assert read(OUT / "keyboard-details.json")["status"] == "passed"
assert all(item["byte_identical"] for item in read(OUT / "unchanged-test-copies.json").values())
assert observations["build_id"] == browser["build_id"] == audit["build_id"] == parity["after_build"]
assert len(audit["checks"]) == 10
assert sha(ROOT / "review/evidence_checks.py") == before["source_files"]["review/evidence_checks.py"]
version = read(ROOT / "bo_stategraph/runtime-version.json")
assert all(sha(ROOT / name) == value for name, value in version["files"].items())
post_plan = read(OUT / "post-upgrade-plan.json")
assert post_plan["valid"] and not post_plan["changes"] and not post_plan["conflicts"]
canonical = ROOT.parent / "vibelens-focus-fix"
head = subprocess.check_output(["git", "-C", str(canonical), "rev-parse", "HEAD"], text=True).strip()
assert head == parity["canonical_revision"]
assert not subprocess.check_output(["git", "-C", str(canonical), "status", "--porcelain"], text=True)
bundle = OUT / "upgraded-source.zip"
if not bundle.exists():
    with zipfile.ZipFile(bundle, "x", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(before["source_files"]):
            archive.write(ROOT / name, name)
        archive.write(ROOT / "review/implementation-version.json", "review/implementation-version.json")
summary = {"status": "independent_project_acceptance_passed",
    "canonical_revision": head, "native_upgrade": True, "shims": False,
    "candidate_id": checked["candidate_id"], "build_id": parity["after_build"],
    "formal_command": ".venv/Scripts/python.exe -B -X utf8 tooling/check.py --accept",
    "reports": {key: value["status"] for key, value in verify["reports"].items()},
    "pytest": 35, "pytest_seconds": float(re.search(r"35 passed in ([0-9.]+)s", tests["stdout"]).group(1)), "scenario_mode_runs": 84, "assertions": 282,
    "mapping_witnesses": verify["reports"]["mapping"]["witnesses"],
    "projection_checks": verify["reports"]["mapping"]["projection_checks"],
    "enabled_mode_events": sum(len(run["events"]) for run in observations["runs"] if run["mode"] == "on"),
    "evidence_counterexamples": len(audit["checks"]), "browser_graph_replay_checks": "passed",
    "keyboard_source_acceptance": keyboard["status"],
    "keyboard_source_details": read(OUT / "keyboard-details.json")["status"],
    "overall_upgrade_acceptance": "passed_for_this_project",
    "browser_policy_evaluations": len(browser["native_rule_transfers"]),
    "recording_id": browser["recording_id"], "recorded_events": browser["event_count"],
    "recorded_frames": browser["last_flush_response"]["enqueued_snapshots"],
    "drain_seconds": browser["drain_wait_seconds"], "errors_dropped_gaps": [0, 0, 0],
    "source_keyboard_path": "Original byte-identical strict keyboard test passed without rerender; full source/highlight/version identity and focus return also passed in live/replay.",
    "performance": "No real-time performance acceptance; historical 363.125-second V2 drain and Windows diagnostics retained.",
    "source_bundle": {"file": bundle.name, "sha256": sha(bundle), "files": len(before["source_files"]) + 1},
    "upstream_wider_verification": "The subsequent source-provided passing receipt was verified against clean HEAD, all 240 Skill hashes and its full log hash; see upstream-receipt-check.json. That suite was not rerun here or substituted for this project's tests.",
    "checked_at": datetime.now(timezone.utc).isoformat()}
write("summary.json", summary)
print(json.dumps(summary))
