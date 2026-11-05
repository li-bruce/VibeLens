"""General observation failures must be caught independently of business assertions."""

from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile
import unittest
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from bo_observer.workflow.observation_requirements import (
    deferred_builder_errors,
    invocation_closure,
    observation_plan,
    probe_sites,
    layer_of,
)
from bo_observer.graph.code_structure import scan
from bo_observer.workflow.change_sync import review_errors
from bo_observer.workflow.iteration_recall import recall
from bo_observer.workflow.sync_verify import assess_observations
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.observation.ownership import observation_ownership, parent_references
from bo_observer.protocol import schema_check
from bo_contracts import validate_graph
from test_multilanguage import project_fixture


class ObservationContinuityTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.folder.name)

    def tearDown(self):
        self.folder.cleanup()

    def events(self, broken=False):
        """Run real functions with a real producer; only negative controls drop evidence."""
        project = project_fixture(self.root)
        project["model"]["nodes"][0]["capture"]["out"]["status"] = "number"
        values = []
        probe = BOProbe(project, "build", sink=lambda value, kind: values.append(value))
        results = []
        try:
            for status in (400, 401, 403, 404, 409):
                with probe.span("advance", entity="request", attempt=str(status)) as observed:
                    try:
                        raise ValueError(status)
                    except ValueError as error:
                        if broken:
                            observed.result(lambda: {"outputs": {"status": error.args[0]}})
                        else:
                            observed.result(lambda status=status: {"outputs": {"status": status}})
                    results.append(status)
            self.assertTrue(probe.flush(3))
            return values, results, probe.bo_health()
        finally:
            probe.close()

    def test_correct_responses_cannot_hide_five_lost_completions(self):
        events, results, health = self.events(broken=True)
        self.assertEqual(results, [400, 401, 403, 404, 409])
        self.assertEqual(health["errors"], 5)
        report = invocation_closure({"runs": [{"mode": "on", "case": "errors", "events": events}]})
        self.assertEqual(len(report["errors"]), 5)
        self.assertTrue(all("invocation_without_exit" in error for error in report["errors"]))

    def test_bound_completion_values_and_real_pairs_pass(self):
        events, results, health = self.events()
        self.assertEqual(health["errors"], 0)
        self.assertEqual(
            [event["outputs"]["status"] for event in events if event["phase"] == "return"],
            results,
        )
        report = invocation_closure(
            {"runs": [{"mode": "on", "case": "errors", "events": events}]}, required=True
        )
        self.assertTrue(report["valid"], report)
        self.assertEqual(report["closed_calls"], 5)

    def test_point_facts_preserve_explicit_entity_and_actual_parent_entry(self):
        project = project_fixture(self.root)
        project["model"]["nodes"].append(
            {"id": "point", "capture": {"in": {}, "out": {"value": "boolean"}}}
        )
        events = []
        probe = BOProbe(project, "build", sink=lambda body, kind: events.append(body))
        try:
            with probe.span("advance", entity="actor", attempt="request") as outer:
                point_id = probe.record(
                    "point",
                    "decision",
                    lambda: {"outputs": {"value": True}},
                    entity="file-a",
                    attempt="file-a",
                    scope="entity",
                )
                probe.record("point", "read", lambda: {}, parent_call_id=None)
                with probe.span("advance", entity="file-b") as child:
                    probe.record("point", "decision", lambda: {"outputs": {"value": False}})
            self.assertTrue(probe.flush())
            point = next(event for event in events if event["id"] == point_id)
            self.assertEqual((point["entity"], point["attempt"]), ("file-a", "file-a"))
            self.assertEqual(point.get("parent_event_id"), outer.entry_id)
            self.assertEqual(point["parent_call_id"], outer.call_id)
            detached = next(event for event in events if event["phase"] == "read")
            self.assertIsNone(detached.get("parent_event_id"))
            self.assertIsNone(detached["parent_call_id"])
            inner = next(
                event
                for event in events
                if event["phase"] == "decision" and event["outputs"]["value"] is False
            )
            self.assertEqual(inner.get("parent_event_id"), child.entry_id)
            self.assertEqual((inner["entity"], inner["attempt"]), ("file-b", "request"))
            root_exit = next(
                event
                for event in events
                if event["phase"] == "return" and event["call_id"] == outer.call_id
            )
            self.assertIsNone(root_exit.get("parent_event_id"))
            self.assertIsNone(root_exit["parent_call_id"])
            self.assertEqual(probe.bo_errors, 0)
        finally:
            probe.close()

    def test_wrong_identity_or_duplicate_entry_does_not_close_a_call(self):
        events, _, _ = self.events()
        for change in ("producer_id", "entity", "attempt", "call_id"):
            values = deepcopy(events[:2])
            values[-1][change] = "other"
            self.assertFalse(
                invocation_closure({"runs": [{"mode": "on", "events": values}]})["valid"]
            )
        duplicate = [events[0], events[0], events[1]]
        self.assertFalse(
            invocation_closure({"runs": [{"mode": "on", "events": duplicate}]})["valid"]
        )

    def test_internal_fact_needs_owner_even_when_values_and_call_exits_are_correct(self):
        project = project_fixture(self.root)
        project["model"]["nodes"].append(
            {"id": "permission", "capture": {"in": {}, "out": {"allowed": "boolean"}}}
        )
        values = []
        probe = BOProbe(project, "build", sink=lambda body, kind: values.append(body))
        try:
            with probe.span("advance", entity="request", attempt="one"):
                probe.record(
                    "permission",
                    "decision",
                    lambda: {"outputs": {"allowed": True}},
                    entity="file-a",
                    attempt="check-a",
                )
            self.assertTrue(probe.flush())
        finally:
            probe.close()
        payload = {"runs": [{"mode": "on", "case": "grant", "events": values}]}
        correct = invocation_closure(payload, required=True, model=project["model"])
        self.assertTrue(correct["valid"], correct)
        broken = deepcopy(payload)
        fact = broken["runs"][0]["events"][1]
        fact.pop("parent_event_id")
        fact.pop("parent_call_id")
        report = invocation_closure(broken, required=True, model=project["model"])
        self.assertFalse(report["valid"])
        self.assertEqual(report["closed_calls"], 1)
        self.assertEqual(fact["outputs"], {"allowed": True})
        self.assertEqual(len(report["errors"]), 1)
        self.assertTrue(report["errors"][0]["missing_observation_owner"])

    def test_only_declared_external_points_can_be_unparented(self):
        events, _, _ = self.events()
        point = {
            **events[0],
            "id": "external",
            "node": "notice",
            "phase": "change",
            "call_id": "notification",
            "parent_call_id": None,
            "parent_event_id": None,
        }
        model = {
            "nodes": [
                {
                    "id": "notice",
                    "observation_root": True,
                    "source": {"path": "native.py", "symbol": "on_notice"},
                }
            ]
        }
        self.assertTrue(observation_ownership([point], model)["valid"])
        self.assertFalse(observation_ownership([point], {"nodes": []})["valid"])
        self.assertFalse(
            observation_ownership([{**point, "parent_call_id": "missing"}], model)["valid"]
        )
        self.assertFalse(
            observation_ownership(
                [{**point, "phase": "enter", "parent_call_id": "missing"}], model
            )["valid"]
        )

    def test_external_root_declaration_is_typed_and_source_bound(self):
        model = project_fixture(self.root)["model"]
        model["nodes"][0]["observation_root"] = True
        validate_graph(model)
        for value in (1, "external", None):
            broken = deepcopy(model)
            broken["nodes"][0]["observation_root"] = value
            with self.assertRaises(ValueError):
                validate_graph(broken)
        model["nodes"][1]["observation_root"] = True
        with self.assertRaisesRegex(ValueError, "native source binding"):
            validate_graph(model)

    def test_closed_parent_or_wrong_legacy_scope_cannot_own_a_point(self):
        events, _, _ = self.events()
        entry, exit_event = events[:2]
        point = {
            **entry,
            "id": "late",
            "node": "permission",
            "phase": "decision",
            "call_id": "check",
            "seq": exit_event["seq"] + 1,
            "parent_call_id": entry["call_id"],
            "parent_event_id": entry["id"],
        }
        self.assertFalse(observation_ownership([entry, exit_event, point], {})["valid"])
        point["seq"] = entry["seq"] + 1
        local_exit = {**exit_event, "seq": point["seq"] + 1}
        self.assertTrue(observation_ownership([entry, point, local_exit], {})["valid"])
        point.pop("parent_event_id")
        self.assertTrue(observation_ownership([entry, point, local_exit], {})["valid"])
        point["entity"] = "another-file"
        self.assertFalse(observation_ownership([entry, point, local_exit], {})["valid"])

    def test_explicit_parent_references_are_strict_and_entity_independent(self):
        events, _, _ = self.events()
        parent = events[0]
        child = {
            **parent,
            "id": "point",
            "seq": parent["seq"] + 1,
            "node": "decision",
            "phase": "decision",
            "call_id": "point-call",
            "parent_call_id": parent["call_id"],
            "parent_event_id": parent["id"],
            "entity": "another-file",
            "attempt": "another-evaluation",
        }
        self.assertTrue(parent_references([parent, child], complete=True)["valid"])
        for change in (
            {"parent_event_id": "missing"},
            {"parent_event_id": "point"},
            {"parent_call_id": "wrong"},
            {"build_id": "wrong"},
            {"parent_event_id": False},
            {"seq": parent["seq"]},
        ):
            bad = {**child, **change}
            self.assertFalse(parent_references([parent, bad], complete=True)["valid"], change)
        self.assertFalse(
            parent_references([{**parent, "phase": "return"}, child], complete=True)["valid"]
        )
        gap = parent_references([child])
        self.assertTrue(gap["valid"])
        self.assertEqual(len(gap["gaps"]), 1)
        cycle_a = {
            **parent,
            "id": "a",
            "producer_id": "producer-a",
            "call_id": "call-a",
            "parent_event_id": "b",
            "parent_call_id": "call-b",
        }
        cycle_b = {
            **parent,
            "id": "b",
            "producer_id": "producer-b",
            "call_id": "call-b",
            "parent_event_id": "a",
            "parent_call_id": "call-a",
        }
        self.assertFalse(parent_references([cycle_a, cycle_b], complete=True)["valid"])

    def test_parent_entry_schema_accepts_legacy_and_rejects_invalid_fields(self):
        events, _, _ = self.events()
        event = events[0]
        schema_check(event, "event")
        legacy = deepcopy(event)
        legacy.pop("parent_event_id", None)
        schema_check(legacy, "event")
        for value in (False, 0, [], "", "x" * 513):
            with self.assertRaises(ValueError):
                schema_check({**event, "parent_event_id": value}, "event")

    def test_fault_modes_do_not_become_business_failures(self):
        payload = {
            "runs": [
                {
                    "mode": "fault",
                    "case": "denied",
                    "events": [],
                    "observations": {"status": 403},
                }
            ]
        }
        contract = {
            "checks": [
                {
                    "id": "deny",
                    "requirement": "R1",
                    "case": "denied",
                    "path": ["status"],
                    "equals": 403,
                }
            ]
        }
        self.assertEqual(assess_observations({}, contract, payload, ["fault"]), [])
        self.assertTrue(invocation_closure(payload)["valid"])
        self.assertFalse(invocation_closure(payload, required=True)["valid"])

    def test_mid_call_commit_cannot_replace_an_explicit_span_return(self):
        events, _, _ = self.events()
        commit = {**events[1], "id": "mid-call", "phase": "commit"}
        model = {
            "nodes": [
                {
                    "id": "advance",
                    "lifecycle": {
                        "bindings": [
                            {"phase": "enter", "state": "running", "boundary": "start"},
                            {"phase": "commit", "state": "committed", "boundary": "end"},
                        ]
                    },
                }
            ]
        }
        payload = {"runs": [{"mode": "on", "events": [events[0], commit]}]}
        self.assertFalse(invocation_closure(payload, required=True, model=model)["valid"])
        payload["runs"][0]["events"].append(events[1])
        self.assertTrue(invocation_closure(payload, required=True, model=model)["valid"])

    def test_source_scan_rejects_cleared_exception_capture_before_runtime(self):
        source = 'def handler(probe):\n    with probe.span("request") as observed:\n        try:\n            raise ValueError(403)\n        except ValueError as error:\n            observed.result(lambda: {"outputs": {"status": error.args[0]}})\n'
        model = {"nodes": [{"id": "request", "source": {"path": "app.py", "symbol": "handler"}}]}
        (self.root / "app.py").write_text(source, encoding="utf-8")
        self.assertEqual(len(deferred_builder_errors(self.root, model)), 1)
        (self.root / "app.py").write_text(
            source.replace("lambda:", "lambda error=error:"), encoding="utf-8"
        )
        self.assertEqual(deferred_builder_errors(self.root, model), [])

    def test_unrelated_result_method_is_not_a_probe_annotation(self):
        source = "def handler(future):\n    try:\n        raise ValueError(403)\n    except ValueError as error:\n        future.result(lambda: error.args[0])\n"
        (self.root / "app.py").write_text(source, encoding="utf-8")
        model = {"nodes": [{"id": "request", "source": {"path": "app.py", "symbol": "handler"}}]}
        self.assertEqual(deferred_builder_errors(self.root, model), [])

    def test_python_and_javascript_span_sites_have_neutral_boundaries(self):
        (self.root / "app.py").write_text(
            'def run(probe):\n    with probe.span("request"):\n        return 1\n',
            encoding="utf-8",
        )
        (self.root / "app.mjs").write_text(
            'export async function run(probe) { return probe.span("request", {}, async () => 1); }',
            encoding="utf-8",
        )
        index = scan(self.root, ["app.py", "app.mjs"])
        self.assertEqual(index["errors"], [])
        sites = probe_sites(index, {"probe_callees": ["probe.span"]})
        for symbol in ("app.py::run", "app.mjs::run"):
            self.assertEqual(
                {site["phase"] for site in sites if site["symbol"] == symbol},
                {"enter", "return", "error"},
            )
        self.assertEqual(probe_sites(index, {"probe_callees": ["unrelated.record"]}), [])

    def test_recall_keeps_contracts_layers_and_source_changes_without_accepting(self):
        (self.root / ".stategraph").mkdir()
        baseline = {"request": "Add messages", "files": {"app.py": "old", "gone.py": "old"}}
        current = {
            "id": "new",
            "files": {"app.py": "new"},
            "structure": {"symbols": {}},
            "intent": {"requirements": [{"id": "R1"}]},
            "model": {
                "nodes": [
                    {
                        "id": "request",
                        "layer": "business",
                        "source": {"path": "app.py", "symbol": "handler"},
                    },
                    {"id": "route", "code_role": "endpoint"},
                    {"id": "table", "data_role": "dataset"},
                ]
            },
        }
        cfg = {
            "model": "project.json",
            "acceptance": "acceptance.json",
            "observations_command": ["python", "observe.py"],
            "stategraph": {
                "module": "bo_stategraph/__init__.py",
                "development_mode": "observe",
            },
        }
        result = recall(self.root, cfg, current, baseline)
        self.assertEqual(result["changed_files"], ["app.py", "gone.py"])
        self.assertEqual(result["layers"]["business"]["affected_nodes"], ["request"])
        self.assertEqual(result["layers"]["implementation"]["nodes"], 1)
        self.assertEqual(result["layers"]["implementation"]["facets"]["api"], 1)
        self.assertEqual(result["layers"]["data"]["nodes"], 1)
        self.assertEqual(result["contracts"]["acceptance"], "acceptance.json")
        self.assertEqual(
            result["required_checks"]["reports"],
            ["concepts", "mapping", "state_rules", "business", "project_checks"],
        )
        self.assertFalse((self.root / ".stategraph/source-baseline.json").exists())
        saved = json.loads(
            (self.root / ".stategraph/iteration-recall.json").read_text(encoding="utf-8")
        )
        self.assertEqual(saved, result)

    def test_recall_bounds_context_preview_without_changing_complete_contract(self):
        contract = {
            "schema": "bo-mapping/v1",
            "context_fields": [
                {
                    "id": f"actor-{index}",
                    "case": f"request-{index}",
                    "node": "route",
                    "phase": "return",
                    "mapped": ["provenance", "actor"],
                    "actual": ["native", str(index), "principal"],
                }
                for index in range(2000)
            ],
        }
        path = self.root / "mapping.json"
        path.write_text(json.dumps(contract), encoding="utf-8")
        original = path.read_bytes()
        current = {
            "id": "candidate",
            "files": {},
            "structure": {"symbols": {}},
            "intent": {},
            "model": {"nodes": []},
        }
        result = recall(
            self.root,
            {"mapping_contract": "mapping.json", "observations_command": []},
            current,
        )
        self.assertEqual(result["context_mapping_count"], 2000)
        self.assertEqual(result["context_mapping_omitted"], 1988)
        self.assertEqual(len(result["context_mapping"]), 12)
        self.assertEqual(result["contracts"]["mapping_contract"], "mapping.json")
        self.assertLess(len(json.dumps(result)), 15000)
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse((self.root / ".stategraph/source-baseline.json").exists())

    def test_observation_closure_cannot_be_disabled_during_iteration(self):
        base = {
            "intent": {"requirements": []},
            "acceptance": {"checks": []},
            "verification_contract": {"require_observation_closure": True},
        }
        current = {**deepcopy(base), "id": "candidate", "verification_contract": {}}
        review = {
            "candidate_id": "candidate",
            "decisions": {
                name: {"action": "unchanged", "reason": "Regression fixture"}
                for name in ("business", "state_machine", "abstraction", "probes")
            },
        }
        (self.root / "review.json").write_text(json.dumps(review), encoding="utf-8")
        self.assertIn(
            {"weakened_verification": "require_observation_closure"},
            review_errors(self.root, base, current, {"unmapped_changed_symbols": []}),
        )

    def test_layer_requirements_and_viewer_use_identical_classification(self):
        nodes = [
            {"layer": "business"},
            {"kind": "state"},
            {"kind": "decision"},
            {"execution_role": "join"},
            {"code_role": "endpoint"},
            {"kind": "function", "layer": "api"},
            {"code_role": "file"},
            {"code_role": "function"},
            {"data_role": "query"},
            {"data_role": "write"},
            {"data_role": "transaction"},
            {"data_role": "transform"},
            {"data_role": "dataset"},
            {"kind": "function"},
            {"semantic_role": "state_parameter"},
            {"data_role": "store", "layer": "business"},
            {"kind": "resource", "origin": "policy-definition"},
            {"kind": "resource", "execution_role": "resource"},
            {"kind": "data", "capture_owner_role": "transaction"},
            {"kind": "unregistered-node-type"},
        ]
        module = (ROOT / "skills/vibelens/assets/stategraph-viewer/graph-layers.js").as_uri()
        script = f"import {{concernOf as layerOf}} from {json.dumps(module)}; console.log(JSON.stringify({json.dumps(nodes)}.map(layerOf)));"
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual([layer_of(node) for node in nodes], json.loads(result.stdout))
        self.assertEqual(layer_of({"kind": "function", "layer": "api"}), "implementation")
        self.assertEqual(layer_of({"execution_role": "join"}), "state")
        self.assertEqual(layer_of({"kind": "unregistered-node-type"}), "unknown")


if __name__ == "__main__":
    unittest.main()
