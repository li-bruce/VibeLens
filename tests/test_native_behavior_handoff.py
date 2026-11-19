"""A real queue outlives its producer call and enters another model's worker."""

from copy import deepcopy
from pathlib import Path
from queue import Queue
import tempfile
from threading import Thread
import unittest

from test_native_behavior_runtime import fixture, run_native, BUILD
from test_native_behavior_bindings import value_binding, source
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.behavior.contract import assess
from bo_observer.behavior.native_runtime import assess_runtime
from bo_observer.sources import scan


def handoff_fixture(root):
    contract, discovery, model, _, app = fixture(root)
    binding = model["behavior_bindings"]
    action = deepcopy(contract["actions"][0])
    action.update(id="archive-deliver", model_refs=["state-model:archive"], reads=[], writes=[],
                  unchanged=["grant-status", "archive-status"], enabled={"op": "literal", "domain": "flag", "value": True},
                  completion={"kind": "return", "meaning": "Worker returns the received value"})
    action.pop("transition_ref")
    contract["actions"].append(action)
    contract["domains"].extend([
        {"id": "job", "type": "identity", "object_ref": "object:grant", "identity_policy": "opaque", "source_refs": ["U1"]},
        {"id": "queue", "type": "sequence", "element_domain": "flag", "max_items": 2,
         "bound_origin": "analysis_bound", "source_refs": ["U1"]},
    ])
    contract["interactions"] = [{"id": "deliver", "kind": "handoff",
        "model_refs": ["state-model:grant", "state-model:archive"], "action_refs": ["grant-share", "archive-deliver"],
        "producer": "grant-share", "consumer": "archive-deliver", "payload_domain": "flag", "queue_domain": "queue",
        "correlation_domain": "job", "ordering": "fifo", "delivery": "at_least_once", "retry": "none",
        "deduplication": "none", "assumption_refs": [], "on_cancel": "Leave delivered work complete",
        "on_failure": "Retain the failed attempt", "source_refs": ["U1"]}]
    for ident, symbol in (("job-send", "enqueue"), ("job-receive", "consume"), ("worker", "consume")):
        model["nodes"].append({"id": ident, "kind": "function", "source": source(symbol),
                               "capture": {"in": {"allowed": "boolean"},
                                           "out": {"correlation": "string", "payload": "boolean", "accepted": "boolean"}}})

    def field(node, phase, name, *, parent=False, direction="outputs"):
        value = value_binding(node, writer=False)
        value["reader"] = source("read_job")
        value["observation"] = {"node": node, "phase": phase, "path": [direction, name]}
        value["native"]["value"] = [name]
        for key in value["native"]["keys"]:
            if key["name"] == "model":
                key["observed"] = ["provenance", "objects", 0, "type"]
            if key["name"] == "invocation" and parent:
                key["observed"] = ["parent_call_id"]
        return value

    parameter = field("worker", "enter", "allowed", direction="inputs")
    parameter["source_parameter"] = "allowed"
    binding["actions"]["archive-deliver"] = {
        "entry": {"node": "worker", "phase": "enter"}, "completion": {"node": "worker", "phase": "return"},
        "completion_witness": field("worker", "return", "accepted"), "parameters": {"allowed": parameter},
        "exits": [], "cases": [{"id": "share", "boundaries": ["complete"]}]}
    binding["interactions"]["deliver"] = {"witnesses": [
        {"role": role, "action": action_id, "site": {"node": node, "phase": "change"},
         "fields": {name: field(node, "change", name, parent=role == "send") for name in ("correlation", "payload")},
         "cases": ["share"]}
        for role, action_id, node in (("send", "grant-share", "job-send"), ("receive", "archive-deliver", "job-receive"))]}
    result = assess(contract, discovery)
    if not result["valid"]:
        raise ValueError(result["errors"])
    binding["definition_sha256"] = result["definition_sha256"]
    return contract, discovery, model, scan(root, ["application.py"]), app


class NativeHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.contract, self.discovery, self.model, self.index, self.app = handoff_fixture(Path(self.temp.name))
        queue, wire, worker_errors = Queue(), {}, []
        job = {"correlation": "download-1", "payload": True}

        def send(probe, native, row):
            self.app.enqueue(queue, job)
            wire["send"] = probe.record("job-send", "change", lambda: {"outputs": self.app.read_job(job)})
            native["job-send"] = [row("state-model:grant", **self.app.read_job(job))]

        run = run_native(self.model, self.app, True, after_commit=send)
        # Start after the originating span and producer have both closed.
        def work():
            probe = BOProbe({"project_id": self.contract["project_id"], "model": self.model}, BUILD,
                            sink=lambda event, kind: run["events"].append(event) if kind == "events" else None)
            try:
                received = queue.get(timeout=2)
                identity = {"model": "state-model:archive", "instance": "1", "invocation": "worker-call",
                            "attempt": "first", "build": BUILD}
                with probe.span("worker", lambda: {"inputs": {"allowed": received["payload"]}},
                                call_id="worker-call", entity="1", attempt="first", scope="attempt",
                                provenance={"objects": [{"type": "state-model:archive", "id": "1", "role": "state_owner"}]},
                                depends=[{"event": wire["send"], "type": "trigger"}]) as span:
                    probe.record("job-receive", "change", lambda: {"outputs": self.app.read_job(received)}, call_id="worker-call")
                    accepted = self.app.consume(received["payload"])
                    span.result(lambda: {"outputs": {"accepted": accepted}})
                    run["native_values"]["job-receive"] = [{**identity, **self.app.read_job(received)}]
                    run["native_values"]["worker"] = [{**identity, "allowed": self.app.read_job(received)["payload"],
                                                       "accepted": self.app.read_job(received)["payload"]}]
            except Exception as error:
                worker_errors.append(repr(error))
            finally:
                probe.flush(2)
                probe.close()
        worker = Thread(target=work)
        worker.start()
        worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(worker_errors, [])
        self.payload = {"build_id": BUILD, "runs": [run, run_native(self.model, self.app, False)]}

    def result(self):
        return assess_runtime(self.contract, self.discovery, self.model, self.payload,
                              index=self.index, case_ids={"share", "error"})

    def test_detached_worker_retains_model_and_native_job_correspondence(self):
        result = self.result()
        self.assertTrue(result["valid"], result.get("errors"))
        self.assertEqual(result["interactions"]["checks"][0]["witnesses"], 2)

    def test_equal_job_values_without_handoff_reference_do_not_pass(self):
        entry = next(e for e in self.payload["runs"][0]["events"] if e["node"] == "worker" and e["phase"] == "enter")
        entry["depends"] = []
        result = self.result()
        self.assertIn("handoff_send_unwitnessed", {e["code"] for e in result["errors"]})

    def test_incorrect_payload_capture_and_missing_worker_are_detected(self):
        run = self.payload["runs"][0]
        event = next(e for e in run["events"] if e["node"] == "job-receive")
        event["outputs"]["payload"] = False
        self.assertIn("native_value_differs", {e["code"] for e in self.result()["errors"]})
        run["events"] = [e for e in run["events"] if e["node"] not in {"worker", "job-receive"}]
        self.assertIn("action_entry_missing", {e["code"] for e in self.result()["errors"]})

    def test_handoff_witness_cannot_belong_to_an_unrelated_invocation(self):
        event = next(e for e in self.payload["runs"][0]["events"] if e["node"] == "job-receive")
        event["parent_event_id"] = event["parent_call_id"] = None
        event["call_id"] = "unrelated"
        # Keep value correspondence intact to isolate ownership validation.
        self.payload["runs"][0]["native_values"]["job-receive"][0]["invocation"] = "unrelated"
        self.assertIn("interaction_action_unowned", {e["code"] for e in self.result()["errors"]})


if __name__ == "__main__":
    unittest.main()
