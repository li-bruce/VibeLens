"""Corrupt only isolated copies of fresh evidence; retain the original checks."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "observer_runtime"))
sys.path.insert(0, str(ROOT))
from behavior_model import capture, check
from mapping_contract import assess
from bo_observer.workflow.observation_requirements import invocation_closure
from bo_observer.data.sync import synchronize
from tooling.observe import transition_witnesses

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def main():
    payload = read(OUT / "runtime-observations.json")
    model = read(ROOT / "bo_stategraph/project.json")["model"]
    plan = read(ROOT / "mapping.json")
    results = {}
    def mapping(value):
        return assess(value, required=True, plan=plan, model=model, build_id=payload["build_id"])
    results["clean_mapping"] = mapping(payload)
    assert results["clean_mapping"]["valid"]
    omitted = deepcopy(payload)
    del omitted["runs"][0]["projection"]["instances"][0]["observed"]["context"]["recipient_id"]
    results["missing_selected_recipient"] = mapping(omitted)
    assert not results["missing_selected_recipient"]["valid"]
    wrong = deepcopy(payload)
    wrong["runs"][0]["projection"]["instances"][0]["observed"]["revision"] += 50
    results["incorrect_revision"] = mapping(wrong)
    assert not results["incorrect_revision"]["valid"]
    reason_missing = deepcopy(payload)
    reason_run = next(run for run in reason_missing["runs"] if run["case"] == "rejection_reason")
    instance = next(item for item in reason_run["projection"]["instances"] if item["observed"]["context"]["rejection_reason"])
    del instance["observed"]["context"]["rejection_reason"]
    results["missing_selected_rejection_reason"] = mapping(reason_missing)
    assert not results["missing_selected_rejection_reason"]["valid"]
    reason_wrong = deepcopy(payload)
    reason_run = next(run for run in reason_wrong["runs"] if run["case"] == "rejection_reason")
    instance = next(item for item in reason_run["projection"]["instances"] if item["observed"]["context"]["rejection_reason"])
    instance["observed"]["context"]["rejection_reason"] = "Incorrect replacement"
    results["incorrect_rejection_reason"] = mapping(reason_wrong)
    assert not results["incorrect_rejection_reason"]["valid"]
    missing_exit = deepcopy(payload)
    run = missing_exit["runs"][0]
    run["events"] = [event for event in run["events"] if not (event["node"] == "upload_file" and event["phase"] == "return")]
    results["missing_invocation_exit"] = invocation_closure(missing_exit, required=True, model=model)
    assert not results["missing_invocation_exit"]["valid"]
    missing_owner = deepcopy(payload)
    point = next(event for event in missing_owner["runs"][0]["events"]
                 if event["node"].startswith("policy:") and event["phase"] == "decision")
    for key in ("parent_event_id", "parent_call_id", "depends_on"):
        point.pop(key, None)
    results["missing_internal_point_owner"] = invocation_closure(missing_owner, required=True, model=model)
    assert not results["missing_internal_point_owner"]["valid"]
    run = payload["runs"][0]
    actual_events = [event for event in run["events"] if event["node"] != "state_transition"]
    try:
        transition_witnesses(run["authority_snapshot"]["files"], actual_events)
        raise RuntimeError("Removed transition witness was not detected")
    except AssertionError as error:
        results["missing_native_transition"] = {"detected": True, "error": str(error)}

    scratch = OUT / ".tmp"
    scratch.mkdir(exist_ok=True)
    isolated = Path(tempfile.mkdtemp(prefix="isolated-source-and-schema-", dir=scratch))
    for name in set(model["source_files"]) | {model["intent"], "bo_stategraph/project.json", "bo_stategraph/databases.json", "bo_stategraph/database-catalog.json", "bo_stategraph/model-catalog.json", "tooling/export_models.py"}:
        source, target = ROOT / name, isolated / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    manifest = capture(isolated, model)
    assert check(isolated, model, manifest)["status"] == "current"
    source = isolated / "app/service.py"
    source.write_text(source.read_text(encoding="utf-8") + "\n# Isolated source drift counterexample.\n", encoding="utf-8")
    drift = check(isolated, model, manifest)
    assert drift["status"] == "stale" and "app/service.py" in drift["changed_files"]
    results["unsynchronized_source"] = drift
    shutil.copy2(ROOT / "app/service.py", source)
    database = isolated / "schema.sqlite3"
    with sqlite3.connect(ROOT / "var/team-files.sqlite3") as origin, sqlite3.connect(database) as target:
        origin.backup(target)
    old_url = os.environ.get("TEAM_FILES_DB_URL")
    old_pythonpath = os.environ.get("PYTHONPATH")
    os.environ["TEAM_FILES_DB_URL"] = "sqlite:///" + str(database)
    os.environ["PYTHONPATH"] = str(ROOT / "observer_runtime")
    try:
        prepared_schema = synchronize(isolated, update=True)
        assert prepared_schema["valid"], prepared_schema
        clean_schema = synchronize(isolated, update=False)
        assert clean_schema["valid"], clean_schema
        with sqlite3.connect(database) as db:
            db.execute("ALTER TABLE files ADD COLUMN isolated_audit_marker TEXT")
        changed_schema = synchronize(isolated, update=False)
        assert not changed_schema["valid"], changed_schema
        results["real_isolated_schema_change"] = {"clean": clean_schema, "altered": changed_schema,
            "statement": "ALTER TABLE files ADD COLUMN isolated_audit_marker TEXT", "production_database_modified": False}
    finally:
        if old_url is None:
            os.environ.pop("TEAM_FILES_DB_URL", None)
        else:
            os.environ["TEAM_FILES_DB_URL"] = old_url
        if old_pythonpath is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = old_pythonpath
    (OUT / "negative-controls.json").write_text(json.dumps({"valid": True, "basis": "Fresh real application observations; mutations are confined to copies.", "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"valid": True, "controls": list(results)}))

if __name__ == "__main__":
    main()
