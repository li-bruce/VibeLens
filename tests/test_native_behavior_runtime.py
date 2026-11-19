"""Real SQLite actions and the existing producer exercise behavior witnesses.

Deliberate mutations affect captured evidence, never the independently read
application results. These are automated fixtures, not dialogue acceptance.
"""

from copy import deepcopy
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

from test_native_behavior_bindings import binding_fixture, source
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.behavior.native_runtime import assess_runtime
from bo_observer.sources import scan

ROOT = Path(__file__).resolve().parents[1]
BUILD = "native-behavior-test"


def fixture(root):
    contract, discovery, model, _ = binding_fixture(root)
    path = root / "application.py"
    path.write_bytes((ROOT / "tests/fixtures/behavior-contracts/native_application.py").read_bytes())
    spec = importlib.util.spec_from_file_location("native_behavior_fixture", path)
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    model["revision"] = "native-one"
    model["project_id"] = contract["project_id"]
    binding = model["behavior_bindings"]
    action = binding["actions"]["grant-share"]
    action["completion_witness"]["reader"] = source("read_commit")
    witnesses = [*binding["variables"].values(), *action["parameters"].values(),
                 action["completion_witness"], *(exit_["witness"] for exit_ in action["exits"])]
    for witness in witnesses:
        for key in witness["native"]["keys"]:
            if key["name"] == "model":
                key["observed"] = ["provenance", "objects", 0, "type"]
    # The commit has its own point-event identity. Its parent call identifies
    # the action whose native result was read; do not replace the child's ID.
    for key in action["completion_witness"]["native"]["keys"]:
        if key["name"] == "invocation":
            key["observed"] = ["parent_call_id"]
    return contract, discovery, model, scan(root, ["application.py"]), app


def run_native(model, app, allowed, *, mode="on", post_commit_error=False, after_commit=None):
    """Exercise ordinary business functions while isolated wiring records facts."""
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE states (model TEXT PRIMARY KEY, value TEXT)")
    connection.executemany("INSERT INTO states VALUES (?,?)", [(name, "inactive") for name in ("grant", "archive")])
    connection.commit()
    statements = []
    connection.set_trace_callback(statements.append)
    events = []

    def sink(event, kind):
        if mode == "fault":
            raise OSError("Synthetic observer transport failure")
        if kind == "events":
            events.append(event)

    project = {"project_id": model["project_id"], "model": model}
    probe = BOProbe(project, BUILD, enabled=mode != "off", sink=sink)
    native = {}
    call_id = "share-invocation"
    entity, attempt = "1", "first"
    owner = "state-model:grant"

    def row(model_ref, **values):
        return {"model": model_ref, "instance": entity, "invocation": call_id,
                "attempt": attempt, "build": BUILD, **values}

    native["share"] = [row(owner, allowed=allowed)]
    def provenance(model_ref):
        return {"objects": [{"type": model_ref, "id": entity, "role": "state_owner"}]}
    try:
        with probe.span("share", lambda: {"inputs": {"owner": owner, "allowed": allowed}},
                        call_id=call_id, entity=entity, attempt=attempt,
                        scope="attempt", provenance=provenance(owner)):
            app.share(connection, allowed)
            app.commit(connection)
            committed = app.read_commit(statements)
            probe.record("commit", "commit", lambda: {"outputs": {"transaction_id": committed}})
            native["commit"] = [row(owner, transaction_id=app.read_commit(statements))]
            for name, state in app.read_native(connection).items():
                model_ref = "state-model:" + name
                probe.record(name, "read", lambda state=state: {"outputs": {"state": state}},
                             provenance=provenance(model_ref), call_id=call_id)
                # A separate read, not an event/projection value.
                native[name] = [row(model_ref, state=app.read_native(connection)[name])]
            if after_commit is not None:
                after_commit(probe, native, row)
            if post_commit_error:
                raise RuntimeError("Failure after an actual commit")
    except Exception as error:
        connection.rollback()
        native["share"][0]["exception_type"] = type(error).__name__
    finally:
        probe.flush(2)
        probe.close()
    actual = app.read_native(connection)
    connection.close()
    return {"case": "post-commit-error" if post_commit_error else "share" if allowed else "error",
            "mode": mode, "events": events, "native_values": native,
            "native_state": actual, "health": probe.bo_health()}


class NativeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.contract, self.discovery, self.model, self.index, self.app = fixture(Path(self.temp.name))
        self.payload = {"build_id": BUILD, "runs": [run_native(self.model, self.app, allowed) for allowed in (True, False)]}

    def result(self):
        return assess_runtime(self.contract, self.discovery, self.model, self.payload,
                              index=self.index, case_ids={run["case"] for run in self.payload["runs"]})

    def test_actual_sqlite_values_commit_exception_and_parameters_match(self):
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertEqual(self.payload["runs"][0]["native_state"], {"grant": "active", "archive": "inactive"})
        self.assertEqual(len(result["boundaries"]), 2)
        self.assertEqual(result["domain_findings"], [])

    def test_wrong_capture_is_mapping_failure_with_unchanged_native_result(self):
        event = next(e for e in self.payload["runs"][0]["events"] if e["node"] == "grant")
        event["outputs"]["state"] = "inactive"
        self.assertIn("native_value_differs", {e["code"] for e in self.result()["errors"]})
        self.assertEqual(self.payload["runs"][0]["native_state"]["grant"], "active")

    def test_missing_commit_does_not_become_a_successful_function_return(self):
        run = self.payload["runs"][0]
        run["events"] = [e for e in run["events"] if e["node"] != "commit"]
        result = self.result()
        self.assertFalse(result["valid"])
        self.assertIn("action_completion_differs", {e["code"] for e in result["errors"]})

    def test_reordered_records_preserve_identity(self):
        before = self.result()
        for run in self.payload["runs"]:
            run["events"].reverse()
        self.assertEqual(self.result()["valid"], before["valid"])
        self.assertTrue(before["valid"], before)

    def test_unknown_or_backwards_causal_references_cannot_assign_completion(self):
        original = deepcopy(self.payload)
        for target in ("missing", "cycle"):
            self.payload = deepcopy(original)
            events = self.payload["runs"][0]["events"]
            entry = next(e for e in events if e["phase"] == "enter")
            commit = next(e for e in events if e["node"] == "commit")
            entry["depends"] = [{"event": commit["id"] if target == "cycle" else target,
                                 "type": "trigger"}]
            self.assertFalse(self.result()["valid"])

    def test_foreign_revision_is_rejected_before_matching_native_values(self):
        self.payload["runs"][0]["events"][0]["model_revision"] = "previous"
        self.assertIn("native_event_invalid", {e["code"] for e in self.result()["errors"]})

    def test_wrong_model_build_or_attempt_cannot_join(self):
        original = deepcopy(self.payload)
        for key, value in (("model", "state-model:archive"), ("build", "old"), ("attempt", "other")):
            self.payload = deepcopy(original)
            self.payload["runs"][0]["native_values"]["grant"][0][key] = value
            self.assertFalse(self.result()["valid"], key)

    def test_exception_after_commit_retains_both_physical_boundaries(self):
        action = self.model["behavior_bindings"]["actions"]["grant-share"]
        action["cases"].append({"id": "post-commit-error", "boundaries": ["complete", "exception"]})
        for witness in [*self.model["behavior_bindings"]["variables"].values(),
                        *action["parameters"].values(), action["completion_witness"], action["exits"][0]["witness"]]:
            witness["cases"].append("post-commit-error")
        self.payload["runs"].append(run_native(self.model, self.app, True, post_commit_error=True))
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertEqual(self.payload["runs"][-1]["native_state"]["grant"], "active")

    def test_observer_off_and_transport_failure_preserve_native_effects(self):
        expected = self.payload["runs"][0]["native_state"]
        for mode in ("off", "fault"):
            run = run_native(self.model, self.app, True, mode=mode)
            self.assertEqual(run["native_state"], expected)
            self.assertEqual(run["events"], [])
            if mode == "fault":
                self.assertGreater(run["health"]["errors"], 0)


if __name__ == "__main__":
    unittest.main()
