"""Archive controlled-fault diagnosis, unchanged contracts, and actual retests."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SKILL = Path((ROOT / "tooling/skill-path.txt").read_text(encoding="utf-8").strip())


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(name, args):
    started = time.perf_counter()
    result = subprocess.run([sys.executable, "-B", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    write(name, {"argv": args, "returncode": result.returncode, "duration_seconds": time.perf_counter() - started,
                 "stdout": result.stdout, "stderr": result.stderr})
    assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    return json.loads(result.stdout)


def main():
    accepted = read(".stategraph/diagnosis-03/accepted.json")
    red = read("review/diagnosis/red-browser/report.json")
    regression = read("review/diagnosis/green-regression/report.json")
    revoked = read("review/diagnosis/green-revocation/report.json")
    other = read("review/diagnosis/green-other-recipient/report.json")
    assert red["controlled_fault"] and red["reproduction_confirmed"] and not red["business_expectation_passed"]
    assert red["actual_stale_download_status"] == 200 and red["expected_stale_download_status"] == 403
    assert red["build_id"] != accepted["build_id"]
    for report in [regression, revoked]:
        assert report["valid"] and report["build_id_before"] == report["build_id_after"] == accepted["build_id"]
        assert not report["page_errors"]
    assert other["valid"] and other["build_id"] == accepted["build_id"] and not other["console_or_page_errors"]
    assert all(revoked["checks"].values()) and all(other["checks"].values())
    for report in [red, regression, revoked, other]:
        for item in report["screenshots"]:
            assert sha(ROOT / item["file"]) == item["sha256"]

    checked = command("post-browser-check.json", [str(SKILL / "scripts/change_sync.py"), "check", "--root", str(ROOT)])
    assert checked["status"] == "current" and checked["candidate_id"] == accepted["candidate_id"]
    architecture = command("architecture-check.json", [str(SKILL / "scripts/architecture_guard.py"), "check", "--root", str(ROOT)])
    assert architecture["valid"]
    protected = read("review/diagnosis/protected-before.json")
    changed = [path for path, value in protected.items() if not (ROOT / path).is_file() or sha(ROOT / path) != value]
    assert not changed, changed
    write("protected-after.json", {"valid": True, "protected_files": len(protected), "changed": changed,
                                   "tests_expectations_capture_and_observers_unchanged": True})
    baseline = read(".stategraph/diagnosis-03/baseline.json")
    assert sha(ROOT / "app/service.py") == baseline["files"]["app/service.py"]
    assert sha(ROOT / "tooling/build_model.py") == baseline["files"]["tooling/build_model.py"]
    write("source-repair.json", {"controlled_fault": True, "path": "app/service.py", "line": 141,
        "before_sha256": sha(OUT / "fault-source/app/service.py"), "after_sha256": sha(ROOT / "app/service.py"),
        "repair": "Compare shares.recipient_id with recipient_id, not actor.",
        "matches_pre_fault_baseline": True, "generator_matches_pre_fault_baseline": True,
        "observer_changes": [], "independent_assertion_changes": [], "diff": "app-service.diff"})

    old = read("review/diagnosis/red-model/project.json")["model"]
    current = read("bo_stategraph/project.json")["model"]
    assert old["machine"] == current["machine"] and old["policy"] == current["policy"]
    ids = lambda model, key: [item["id"] for item in model[key]]
    assert ids(old, "nodes") == ids(current, "nodes") and ids(old, "edges") == ids(current, "edges")
    write("graph-maintenance.json", {"valid": True, "stable_node_and_edge_ids": True, "state_declaration_unchanged": True,
        "policy_declaration_unchanged": True, "nodes": len(current["nodes"]), "edges": len(current["edges"]),
        "source_mapping_refreshed": True, "red_project_sha256": sha(OUT / "red-model/project.json"),
        "green_project_sha256": sha(ROOT / "bo_stategraph/project.json"), "native_inspect_verify_accept_check": "passed"})
    before_bind = read("review/diagnosis/sql-binding-before.json")
    after_bind = read("review/diagnosis/sql-binding-after.json")
    assert before_bind["real_driver_statements"][0]["compiled_parameters"][0]["recipient_id_1"] == "linzhou"
    assert after_bind["real_driver_statements"][0]["compiled_parameters"][0]["recipient_id_1"] == "xuning"
    assert before_bind["remaining_recipients"] == ["xuning"] and after_bind["remaining_recipients"] == []

    code = '''from pathlib import Path
import sys,json
root=Path.cwd();sys.path.insert(0,str(root/'observer_runtime'))
from bo_observer.protocol import validate_project,schema_check
from bo_observer.policy.projection import project
doc=json.loads((root/'bo_stategraph/project.json').read_text(encoding='utf-8'))
validate_project(doc)
assert project(doc['model'])==doc['model']
assert not hasattr(schema_check,'bo_maps_compat')
assert not any('bo_schema_compat' in key for key in sys.modules)
print(json.dumps({'valid':True,'native_protocol':True,'projection_idempotent':True,'schema_or_projection_shim_loaded':False}))
'''
    command("native-framework-check.json", ["-c", code])
    formal = json.loads(read("review/change-verify.json")["stdout"])
    assert all(item["status"] == "passed" for item in formal["reports"].values())
    unit = read(".stategraph/diagnosis-03/checks/test-0.json")
    unit_count = int(re.search(r"Ran (\d+) tests", unit["stderr"]).group(1))
    assert unit_count == 16 and formal["reports"]["business"]["assertions"] == {"required": 84, "executed": 84}
    evidence = read("review/evidence-checks.json")
    assert evidence["valid"] and len(evidence["checks"]) == 10
    red_formal = json.loads(read("review/diagnosis/red-verify.json")["stdout"])
    assert not red_formal["valid"]
    red_status = {key: item["status"] for key, item in red_formal["reports"].items()}

    recordings = []
    folders = ["red-browser", "green-regression", "green-revocation", "green-other-recipient"]
    for name in folders:
        folder = OUT / name
        summary = json.loads((folder / "recording-stop.json").read_text(encoding="utf-8"))
        path = ROOT / "bo_stategraph/data/recordings" / (summary["id"] + ".json")
        record = json.loads(path.read_text(encoding="utf-8"))
        assert len(record["events"]) == summary["events"] and not record["gaps"]
        assert record["build_id"] == (red["build_id"] if name == "red-browser" else accepted["build_id"])
        shutil.copy2(path, folder / "recording.json")
        recordings.append({"phase": name, "id": summary["id"], "events": summary["events"], "gaps": [], "sha256": sha(path), "file": (folder / "recording.json").relative_to(ROOT).as_posix()})
    failed_record = read("review/diagnosis/red-browser-attempt-01/recording-stop.json")
    failed_path = ROOT / "bo_stategraph/data/recordings" / (failed_record["id"] + ".json")
    shutil.copy2(failed_path, OUT / "red-browser-attempt-01/recording.json")
    shutil.copytree(ROOT / ".stategraph/diagnosis-03", OUT / "green-verification", dirs_exist_ok=True)
    for name in ["source-sync.json", "change-inspect.json", "change-verify.json", "change-accept.json", "change-check.json", "runtime-observations.json", "evidence-checks.json"]:
        shutil.copy2(ROOT / "review" / name, OUT / name)
    source = OUT / "repaired-source"
    source.mkdir(exist_ok=True)
    for name in ["project.json", "database-catalog.json", "databases.json", "runtime-version.json"]:
        shutil.copy2(ROOT / "bo_stategraph" / name, source / name)
    shutil.copy2(ROOT / "app/service.py", source / "service.py")
    files = []
    for directory in ["app", "bo_stategraph", "integrations", "static", "templates", "tooling", "tests", "observer_runtime"]:
        for path in (ROOT / directory).rglob("*"):
            if not path.is_file() or set(path.parts) & {"__pycache__", "node_modules"}:
                continue
            relative = path.relative_to(ROOT).as_posix()
            if relative.startswith(("bo_stategraph/data/", "bo_stategraph/config/views/", "bo_stategraph/config/control/")):
                continue
            files.append(path)
    for name in ["run.py", "README.md", "AGENTS.md", ".gitignore", "requirements.txt", "sync.json", "intent.json", "acceptance.json", "discovery.json", "mapping.json", "whitebox.json", "implementation.json", "behavior.json", "ownership.json", "manifest.json"]:
        files.append(ROOT / name)
    manifest = []
    with zipfile.ZipFile(source / "source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            relative = path.relative_to(ROOT).as_posix()
            archive.write(path, relative)
            manifest.append({"path": relative, "sha256": sha(path), "bytes": path.stat().st_size})
    write("repaired-source/source-manifest.json", {**accepted, "files": manifest, "source_zip_sha256": sha(source / "source.zip"), "private_runtime_data_included": False})
    health = json.load(urllib.request.urlopen("http://127.0.0.1:8853/api/bo/health", timeout=20))
    assert health["build_id"] == accepted["build_id"] and health["binding"]["status"] == "current"
    write("final-runtime-health.json", health)
    services = read("review/running-services.json")
    services.update(stage="accepted-green-controlled-diagnosis", accepted_build=accepted["build_id"], accepted_candidate=accepted["candidate_id"])
    (ROOT / "review/running-services.json").write_text(json.dumps(services, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    costs = {"scope": "Isolated controlled diagnosis; no business scope expansion.", "fault_provenance": "Supplied controlled fault after the existing diagnosis-03 begin; not a naturally discovered production defect.",
        "independent_red_unit_invocations": 1, "red_failures": 5, "red_native_verify_invocations": 1, "green_full_gate_invocations": 1,
        "red_browser_invocations": 2, "green_browser_invocations": 3, "dependency_installations": 0,
        "red_unit_seconds": read("review/diagnosis/red-tests-reproduced.json")["duration_seconds"],
        "green_gate_command_seconds": {name: read("review/" + name)["duration_seconds"] for name in ["source-sync.json", "change-inspect.json", "change-verify.json", "change-accept.json", "change-check.json"]},
        "failures_and_fixes": [
            {"record": "environment-initialization.json", "cause": "The independent source copy had no default SQLite file for metadata collection.", "resolution": "Initialize copy-local synthetic data through the ordinary application initializer."},
            {"record": "red-inspect-attempt-01.json", "cause": "The red candidate had no coding review yet.", "resolution": "Record the real diagnosis scope; retain native class handling and all original expectations."},
            {"record": "red-inspect-attempt-02-invalid-class-support.json", "cause": "An attempted class-level support entry was invalid because native implementation support covers functions.", "resolution": "Revert that mistaken project mapping attempt. The generator matches the pre-fault baseline; no validator or projection was patched."},
            {"record": "red-browser-attempt-01/failure.json", "cause": "The replay option was selected before asynchronous loading finished.", "resolution": "Wait for the actual revoke option, retain the failed attempt and repeat the real fault reproduction."}],
        "measurement_boundary": "Receipt durations measure commands. Unknown active developer effort is not estimated. Existing observer failure modes and negative evidence checks are retained."}
    write("development-costs.json", costs)
    screenshot_count = sum(len(report["screenshots"]) for report in [red, regression, revoked, other])
    result = {"valid": True, "controlled_fault": True, "finished_at": datetime.now(timezone.utc).isoformat(), **accepted,
        "root_cause": "The DELETE predicate compared recipient_id to actor instead of the selected recipient_id.",
        "business_source_fix": "app/service.py:141", "original_tests_unchanged": True, "original_expectations_unchanged": True, "observers_unchanged": True,
        "red_reports": red_status, "green_reports": formal["reports"], "application_tests": 16, "business_assertions": 84, "evidence_checks": 10,
        "browser": {"red_stale_download_status": 200, "green_stale_download_status": 403, "owner_download_preserved": True, "other_recipient_preserved": True, "reshare_restores_access": True, "screenshots": screenshot_count},
        "recordings": recordings, "graph_limit": "Recorded requested recipient_id is not the actual SQL driver bind; exact root cause required source and independent DBAPI binding evidence.",
        "protected_files_unchanged": len(protected), "application": "http://127.0.0.1:8852/", "graph": "http://127.0.0.1:8853/graph",
        "framework_status": "User-selected unreleased native candidate; no compatibility patch and no upstream release claim.", "current_failures": [],
        "isolation": "Only this copy's business source/data/services/artifacts were operated on. Original dependency executable is used by permission; no original investigation artifact, other trial/chat, or maintenance source was used for diagnosis.",
        "stopped_after_requested_diagnosis": True}
    write("final-acceptance.json", result)
    report = f"""# Controlled stale-page diagnosis

The supplied controlled fault is repaired in this isolated copy. The revocation DELETE compared the recipient column to the acting owner (`linzhou`) rather than the selected recipient (`xuning`). It therefore deleted zero rows, left the grant present, and the existing per-request read policy correctly continued to permit that recipient. The domain fix changes one expression in `app/service.py:141` from `actor` to `recipient_id`. It matches the pre-fault source baseline. No file, policy, state rule, observer, independent assertion, or test was weakened to obtain a pass.

This was an explicitly supplied controlled-fault test after `.stategraph/diagnosis-03` began, not a naturally discovered production defect. The original delivery and other trials/chats were not used for investigation. All source edits, services, synthetic data, and artifacts belong to this copy. Only the permitted original virtual-environment executable and selected Skill interfaces were used. Ports are 8852 and 8853.

## What the graph actually contributed

1. The state network and native witnesses showed private -> shared -> shared, with `has_recipients=true`, after the failed revoke. The state accurately reflected the surviving relationship; changing the state declaration would have hidden the real problem.
2. The rule network showed owner authority for revoke and, later, `is_owner=false`, `received_share=true`, and `read_allowed=true` for xuning. This explained the actual decision from current facts. It did not prove that revocation achieved its intended effect.
3. The data node `db_delete_share` returned rows=0; the revoke commit recorded `removed=false` and `grant_count=1`. An independent SQLite query confirmed the xuning grant remained. Native source/impact inspection connected the changed revoke function to its deletion, transaction, state update, and neighboring access behavior.
4. The recorded request field `recipient_id=xuning` did **not** establish the actual compiled SQL binding. Source inspection found `shares.recipient_id == actor`; an independent read-only SQLAlchemy execution listener captured the DBAPI value `linzhou`. After repair the driver value is `xuning` and the selected grant is absent. The exact variable error required source and driver evidence; it was not automatically diagnosed by the graph.

Ordered evidence and explicit limits are in `diagnosis-evidence.json`, `red-runtime/observations.json`, and `sql-binding-before.json` / `sql-binding-after.json`. The observer was not modified to manufacture a different result.

## Red evidence

The supplied original failures were independently reproduced: 5 failures in the unchanged 16 tests. A real headless browser kept the recipient DOM and original download link open, saw the owner's success notice, and downloaded the same bytes again with HTTP 200. Independent SQLite facts showed the relation remained. The real red recording was stopped and replayed, showing `removed=false` and shared -> shared.

The completed native red inspection passed after normal coding reconciliation. Red verify failed: mapping={red_status['mapping']}, state rules={red_status['state_rules']}, business={red_status['business']}, project checks={red_status['project_checks']}. The original revocation assertion stopped the observation command, so the not-run categories are not represented as passes. The separate diagnostic runtime evidence is a partial actual observation, not a substitute formal mapping pass.

## Repair and green verification

The existing begin baseline remains immutable. Normal source generation, scan, inspect, verify, accept, and check completed for candidate `{accepted['candidate_id']}` and build `{accepted['build_id']}`. Source mappings were refreshed; state and policy declarations and all node/edge IDs were retained.

Implementation mapping, state constraints, business rules, and project checks all passed separately. The unchanged 16 application tests, 84 business assertions across observation on/off/failing modes, and 10 evidence checks passed. The original concurrency, queue saturation, core-only export, retained-recipient, re-share, and missing-transition-witness checks remain in place.

The original browser regression passed 11 steps, and the original revocation browser check passed 12 steps. Its obsolete-recording fixture now points to this copy's **actual red-build recording**, preserving the original old-version hiding assertion without reading the original project's historical artifacts. A supplemental browser case revoked xuning while retaining zhoulan: xuning's unchanged old page returned 403, zhoulan and the owner downloaded identical bytes, and re-sharing restored xuning's download. Real rule events show those decisions at the correct file revision. Its shared -> shared transition is legitimate because one other recipient remains; `removed=true` and the independent grant rows distinguish it from the red failure. All four final recordings have no gaps and were actually replayed. {screenshot_count} screenshots are preserved, with no browser graph console/page errors in passing checks.

## Archive

- Original instruction, supplied baseline and red records: `request-original.txt`, `diagnosis-baseline-*.json`, `diagnosis-red-tests.json`.
- Original fault source and exact repair: `fault-source/`, `app-service.diff`, `source-repair.json`.
- Independent data and native graph evidence: `red-runtime/`, `sql-binding-*.json`, and their private copy-local SQLite fixtures.
- Red and green graph/verification snapshots: `red-model/`, `red-verification/`, `green-verification/`, copied CLI receipts, `runtime-observations.json`, `graph-maintenance.json`.
- Actual browser operations, screenshots, bytes, and raw recordings: `red-browser/`, `green-regression/`, `green-revocation/`, `green-other-recipient/`. The first replay-loading failure is preserved in `red-browser-attempt-01/`.
- Full repaired source and per-file hashes: `repaired-source/source.zip`, `repaired-source/source-manifest.json`.
- Contract/observer and begin-baseline integrity: `protected-before.json`, `protected-after.json`; {len(protected)} protected files remain unchanged.
- Environment setup, mapping attempts, fixes, retests, and measured command costs: `development-costs.json` and its referenced records. The invalid class-support mapping attempt was rejected and reverted; the generator is byte-identical to the pre-fault version. Native validators and projectors were never replaced.

## Run and boundary

Application: http://127.0.0.1:8852/ . Graph: http://127.0.0.1:8853/graph . Run the shared dependency executable with this copy as cwd and `-B run.py --port 8852 --graph-port 8853`. `FILE_SHARING_DB_URL=sqlite:///data/sharing.sqlite3` resolves within this copy. Demo accounts/password are unchanged. Final process ownership is recorded in this copy's `review/running-services.json`.

Current failures: none. This is local scripted acceptance of a controlled diagnosis, with initial design answers still explicitly simulated. No production, independent human, or upstream release acceptance is claimed. Revocation applies to new requests after commit; already downloaded copies and in-flight transfers are outside the stated requirement. No feature expansion, additional fault planting, publishing, or product-material export was performed. Work stops after this diagnosis.
"""
    (OUT / "final-review.md").write_text(report, encoding="utf-8")
    print(json.dumps({"valid": True, "controlled_fault": True, "build_id": accepted["build_id"], "application_tests": 16, "business_assertions": 84, "evidence_checks": 10, "screenshots": screenshot_count, "recordings": len(recordings), "protected_files": len(protected)}))


if __name__ == "__main__":
    main()
