"""Correct final rows and healthy producers cannot hide rejected intermediate facts."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from test_multilanguage import project_fixture, JS
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.adapters.python.bo_executor import BOExecutor
from bo_observer.workflow.snapshot_evidence import assess_snapshot_admission
from bo_observer.workflow.sync_verify import assess_probe_health
from bo_observer.workflow.observation_requirements import observation_plan
from bo_stategraph import BOStateGraph


class SnapshotEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.folder.name)
        self.project = project_fixture(self.root)
        self.run = {"case": "native", "mode": "on", "events": [], "snapshots": []}
        self.probe = BOProbe(
            self.project, "build", sink=lambda value, kind: self.run[kind].append(value)
        )

    def tearDown(self):
        self.probe.close()
        self.folder.cleanup()

    def read(self, slots=1):
        ident = self.probe.record("advance", "read", lambda: {}, revision=0)
        self.probe.snapshot("task", "pending", {"slots": slots}, 0, ident)
        self.assertTrue(self.probe.flush(3))
        return ident

    def audit(self, run=None):
        return assess_snapshot_admission(
            self.project, "build", {"runs": [run or self.run]}, required=True
        )

    def test_list_sink_health_does_not_prove_snapshot_admission(self):
        self.read()
        self.read(slots=0)
        self.run["probe_health"] = self.probe.bo_health()
        self.assertTrue(assess_probe_health({"runs": [self.run]}, required=True)["valid"])
        report = self.audit()
        self.assertFalse(report["valid"])
        self.assertIn("old or conflicting revision", str(report["errors"]))
        self.assertEqual(report["state_errors"], [])

    def test_independent_identical_reads_keep_their_own_evidence(self):
        first, second = self.read(), self.read()
        report = self.audit()
        self.assertTrue(report["valid"], report)
        self.assertEqual([row["evidence_id"] for row in report["checks"]], [first, second])
        self.assertEqual([row["revision"] for row in report["checks"]], [0, 0])

    def test_missing_snapshot_cannot_be_replaced_by_final_projection(self):
        self.read()
        changed = deepcopy(self.run)
        changed.pop("snapshots")
        changed["projection"] = {"instances": [{"observed": {"state": "pending", "revision": 0}}]}
        self.assertTrue(self.audit(changed)["errors"][0]["missing_state_snapshot"])

    def test_snapshot_sequence_is_not_sorted_to_hide_reordering(self):
        self.read()
        self.read()
        changed = deepcopy(self.run)
        changed["snapshots"].reverse()
        self.assertIn("out of producer order", str(self.audit(changed)["errors"]))

    def test_evidence_identity_revision_and_build_are_checked(self):
        self.read()
        for key, value in (
            ("evidence_id", "absent"),
            ("revision", 1),
            ("build_id", "old"),
            ("producer_id", "other"),
        ):
            with self.subTest(key=key):
                changed = deepcopy(self.run)
                changed["snapshots"][0][key] = value
                self.assertFalse(self.audit(changed)["valid"])

    def test_observed_invalid_state_is_reported_separately_from_capture(self):
        self.read()
        changed = deepcopy(self.run)
        changed["snapshots"][0]["state"] = "not-declared"
        report = self.audit(changed)
        self.assertTrue(report["checks"][0]["accepted"])
        self.assertTrue(report["valid"], report)
        self.assertTrue(report["state_errors"])

    def test_disabled_modes_and_legacy_events_do_not_claim_canonical_validation(self):
        self.read()
        for run in (
            {**self.run, "mode": "off"},
            {**self.run, "mode": "fault"},
            {"mode": "on", "events": [{"revision": 1}]},
        ):
            report = self.audit(run)
            self.assertTrue(report["valid"], report)
            self.assertEqual(report["status"], "not_applicable")

    def test_duplicate_delivery_and_separate_runs_keep_their_identity(self):
        self.read()
        self.run["snapshots"].append(deepcopy(self.run["snapshots"][0]))
        self.assertTrue(self.audit()["valid"])
        report = assess_snapshot_admission(
            self.project,
            "build",
            {"runs": [self.run, {**self.run, "case": "independent"}]},
            required=True,
        )
        self.assertTrue(report["valid"], report)
        self.assertEqual(len(report["checks"]), 4)

    def test_retry_cannot_change_json_type_behind_the_same_evidence_id(self):
        self.read()
        changed = deepcopy(self.run)
        retry = deepcopy(changed["snapshots"][0])
        retry["context"]["slots"] = True
        changed["snapshots"].append(retry)
        report = self.audit(changed)
        self.assertFalse(report["valid"], report)
        self.assertFalse(report["checks"][1]["accepted"])

    def test_native_observer_duplicate_comparison_preserves_json_types(self):
        for changed in (True, 1.0):
            with self.subTest(value=changed):
                graph = BOStateGraph(self.project["model"], build_id="build", mode="observe")
                fields = dict(state="pending", revision=0, evidence_id="same", build_id="build")
                self.assertTrue(
                    graph.bo_observe("task", context={"slots": 1}, **fields)["accepted"]
                )
                result = graph.bo_observe("task", context={"slots": changed}, **fields)
                self.assertFalse(result["accepted"], result)
                self.assertEqual(type(graph.bo_instances()[0]["observed"]["context"]["slots"]), int)

    def test_transient_decision_is_a_typed_event_input_in_python_and_node(self):
        chart = deepcopy(self.project["model"]["machine"])
        chart["events"]["start"]["payload"] = {"allowed": {"type": "boolean"}}
        executor = BOExecutor(chart, {"available": lambda context, payload: payload["allowed"]})
        context = {"slots": 1}
        results = [
            executor.step("pending", "start", context, {"allowed": value})
            for value in (True, False)
        ]
        self.assertEqual([row["state"] for row in results], ["running", "waiting"])
        self.assertEqual(context, {"slots": 1})
        module = self.root / "inputs.mjs"
        module.write_text(
            "import {BOExecutor} from " + json.dumps(JS.as_uri()) + ";\n"
            "const chart=" + json.dumps(chart) + ";\n"
            "const context={slots:1}; const executor=new BOExecutor(chart,{available:(c,p)=>p.allowed});\n"
            'console.log(JSON.stringify({context, results:[true,false].map(allowed=>executor.step("pending","start",context,{allowed}))}));\n',
            encoding="utf-8",
        )
        result = subprocess.run(["node", str(module)], capture_output=True, text=True, check=True)
        actual = json.loads(result.stdout)
        self.assertEqual(actual["results"], results)
        self.assertEqual(actual["context"], context)
        with self.assertRaises(ValueError):
            executor.step("pending", "start", context, {"allowed": "false"})

    def test_iteration_plan_keeps_context_and_event_inputs_distinct(self):
        model = deepcopy(self.project["model"])
        model["machine"]["events"]["start"]["payload"] = {"allowed": {"type": "boolean"}}
        plan = observation_plan(model, {})["state_evidence"]
        self.assertEqual(
            plan["models"]["default"]["context"], {"slots": {"type": "integer", "min": 0}}
        )
        self.assertEqual(
            plan["models"]["default"]["event_inputs"]["start"], {"allowed": {"type": "boolean"}}
        )
        model.pop("machine")
        self.assertEqual(observation_plan(model, {})["state_evidence"]["models"], {})


if __name__ == "__main__":
    unittest.main()
