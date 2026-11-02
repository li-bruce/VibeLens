"""Use actual discovery, JSON CLI and native project validation boundaries."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools"), str(ROOT / "tests")]

from test_relation_insertion import CONTEXT, entry, rules, triangle
from test_multilanguage import project_fixture
from bo_observer.graph.relations.cli import operate
from bo_observer.graph.relations.model import construct, validate
from bo_observer.graph.behavior_model import validate as validate_behavior
from bo_observer.protocol import validate_project
from bo_observer.web.bo_design import BODesign
from bo_observer.workflow.requirements_dialogue import assess
from bo_observer.workflow.sync_io import write
from bo_observer.adapters.python.bo_executor import BOExecutor
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.observation.session import GraphSession


def discovery():
    """A small confirmed business-to-implementation mapping, with fixed IDs."""
    spec = rules()
    spec["definitions"][0]["match"] = {
        "type": "maps",
        "origin": "design",
        "semantic_relation": "implements",
    }
    spec["definitions"][1]["match"] = {"type": "data", "origin": "design"}
    return {
        "schema": "business-discovery/v1",
        "project_id": "sharing",
        "goal": "Share an uploaded file",
        "title": "File sharing",
        "sources": [
            {
                "id": "U1",
                "kind": "user",
                "text": "Use the sharing function to read file data.",
                "locator": "Synthetic module integration test",
            }
        ],
        "decisions": [],
        "relation_rules": spec,
        "networks": [
            {
                "id": "sharing",
                "title": "Share a file",
                "actors": ["Owner"],
                "trigger": "Owner selects a file",
                "outcome": "The file is shared",
                "nodes": [
                    {
                        "id": "a",
                        "kind": "action",
                        "label": "Share file",
                        "source_refs": ["U1"],
                        "model_nodes": ["business.share"],
                    },
                    {
                        "id": "b",
                        "kind": "action",
                        "label": "Read file",
                        "source_refs": ["U1"],
                        "model_nodes": ["function.read"],
                    },
                    {
                        "id": "c",
                        "kind": "data",
                        "label": "File record",
                        "source_refs": ["U1"],
                        "model_nodes": ["table.files"],
                    },
                ],
                "edges": [
                    {
                        "id": item["edge"]["id"],
                        "from": item["edge"]["from"],
                        "to": item["edge"]["to"],
                        "relation": "data" if item["relation"] == "reads" else "maps",
                        "label": item["relation"],
                        "source_refs": ["U1"],
                        "relation_registration": {
                            "relation": item["relation"],
                            "context": deepcopy(CONTEXT),
                        },
                    }
                    for item in triangle()
                ],
            }
        ],
    }


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".validation").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_design_construction_uses_the_same_index_and_raw_declarations_survive(self):
        doc = discovery()
        self.assertTrue(assess(doc)["ready"], assess(doc))
        write(self.root / "discovery.json", doc)
        model = BODesign(self.root).view()["model"]
        index = validate(model)
        self.assertEqual(index.decision("ac")["leaf_path"], ["ab", "bc"])
        self.assertEqual(
            [(e["from"], e["to"]) for e in model["edges"]],
            [("business.share", "function.read"), ("function.read", "table.files")],
        )
        self.assertEqual(json.loads((self.root / "discovery.json").read_text()), doc)
        self.assertEqual(len(model["relation_registry"]["entries"]), 3)

    def test_iteration_breaks_a_witness_and_restores_the_summary(self):
        doc = discovery()
        write(self.root / "discovery.json", doc)
        before = BODesign(self.root).view()["model"]
        doc["networks"][0]["edges"][1]["relation_registration"]["context"]["revision"] = "v2"
        write(self.root / "discovery.json", doc)
        after = BODesign(self.root).view()["model"]
        self.assertEqual(len(before["edges"]), 2)
        self.assertEqual(len(after["edges"]), 3)
        self.assertEqual([n["id"] for n in before["nodes"]], [n["id"] for n in after["nodes"]])
        self.assertEqual(before["machine"], after["machine"])
        self.assertNotEqual(
            before["relation_registry"]["revision"], after["relation_registry"]["revision"]
        )

    def test_discovery_rejects_invalid_rules_and_orphan_registration(self):
        for change in (
            lambda d: d.update(relation_rules=None),
            lambda d: d.pop("relation_rules"),
            lambda d: d["relation_rules"]["definitions"][2].update(match={"type": "flow"}),
            lambda d: d["networks"][0]["edges"][2].update(relation="flow"),
            lambda d: d["networks"][0]["edges"][2]["relation_registration"].update(
                context={"unexpected": True}
            ),
        ):
            doc = discovery()
            change(doc)
            self.assertFalse(assess(doc)["valid"])
            write(self.root / "discovery.json", doc)
            with self.assertRaises(ValueError):
                BODesign(self.root).view()

    def test_legacy_design_preserves_all_ordinary_physical_edges(self):
        doc = json.loads(
            (ROOT / "skills/vibelens/assets/discovery.example.json").read_text(encoding="utf-8")
        )
        write(self.root / "discovery.json", doc)
        model = BODesign(self.root).view()["model"]
        self.assertNotIn("relation_registry", model)
        self.assertEqual(len(model["edges"]), 4)
        self.assertEqual([e["type"] for e in model["edges"]], ["flow", "data", "guard", "join"])

    def test_full_project_validation_retains_native_execution_and_detects_bypass(self):
        project = project_fixture(self.root)
        original = deepcopy(project["model"]["machine"])
        project["model"] = construct(project["model"])
        validate_project(project)
        validate_behavior(self.root, project["model"])
        self.assertEqual(project["model"]["machine"], original)
        before = BOExecutor(
            original, {"available": lambda context, payload: context["slots"] > 0}
        ).step("pending", "start", {"slots": 1})
        after = BOExecutor(
            project["model"]["machine"],
            {"available": lambda context, payload: context["slots"] > 0},
        ).step("pending", "start", {"slots": 1})
        self.assertEqual(before, after)
        project["model"]["edges"][0]["label"] = "Edited outside registration"
        with self.assertRaisesRegex(ValueError, "insertion decisions"):
            validate_project(project)
        with self.assertRaisesRegex(ValueError, "insertion decisions"):
            validate_behavior(self.root, project["model"])

    def test_appended_physical_projector_facts_remain_visible_and_protected(self):
        model = construct(
            {"nodes": [{"id": "a"}, {"id": "b"}], "edges": [entry("ab", "a", "b", None)["edge"]]}
        )
        model["nodes"].append({"id": "c"})
        extra = entry("bc", "b", "c", None)["edge"]
        model["edges"].append(extra)
        validate(model)
        result = operate(model, "remove", {"id": "ab"})
        self.assertEqual(result["edges"], [extra])
        with self.assertRaisesRegex(ValueError, "external edge"):
            operate(model, "insert", {"edge": extra})

    def test_registered_graph_keeps_actual_probe_and_collector_events_unchanged(self):
        project = project_fixture(self.root)
        project["model"] = construct(project["model"])
        write(self.root / "bo_stategraph/project.json", project)
        session = GraphSession(self.root)
        probe = BOProbe(
            session.project,
            session.manifest["build_id"],
            sink=lambda event, kind: session.event(event),
        )
        try:
            probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})
            self.assertTrue(probe.flush(2))
            events = session.history.snapshot()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["node"], "advance")
            self.assertEqual(events[0]["outputs"], {"state": "running"})
            self.assertEqual(session.gaps, 0)
            validate(session.project["model"])
        finally:
            probe.close()
            session.close()

    def test_check_rejects_reintroduced_summary_and_missing_nodes(self):
        graph = {
            "nodes": [{"id": ident} for ident in ("a", "b", "c")],
            "edges": [i["edge"] for i in triangle()],
        }
        model = construct(
            graph,
            rules(),
            registrations={
                i["edge"]["id"]: {k: v for k, v in i.items() if k != "edge"} for i in triangle()
            },
        )
        for change in (
            lambda m: m["edges"].append(triangle()[2]["edge"]),
            lambda m: m["nodes"].pop(),
        ):
            changed = deepcopy(model)
            change(changed)
            with self.assertRaises(ValueError):
                validate(changed)

    def cli(self, action, *, payload=None, expected=None, model="graph.json"):
        command = [
            sys.executable,
            "-B",
            "-X",
            "utf8",
            str(ROOT / "skills/vibelens/scripts/bo_relations.py"),
            action,
            "--root",
            str(self.root),
            "--model",
            model,
        ]
        if payload is not None:
            write(self.root / "input.json", payload)
            command += ["--input", "input.json"]
        if expected:
            command += ["--expected-revision", expected]
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=20
        )
        return result.returncode, json.loads(result.stdout)

    def test_atomic_json_cli_roundtrip_insert_restore_and_conflict(self):
        write(
            self.root / "graph.json",
            {"nodes": [{"id": ident} for ident in ("a", "b", "c")], "edges": []},
        )
        self.assertEqual(self.cli("init", payload={"rules": rules()})[0], 0)
        status, result = self.cli(
            "batch", payload=[{"op": "insert", "entry": value} for value in triangle()]
        )
        self.assertEqual(status, 0, result)
        self.assertEqual(result["counts"], {"retained": 2, "duplicate": 0, "represented": 1})
        before = (self.root / "graph.json").read_bytes()
        self.assertEqual(self.cli("remove", payload={"id": "bc"}, expected="stale")[0], 1)
        self.assertEqual((self.root / "graph.json").read_bytes(), before)
        self.assertEqual(
            self.cli("remove", payload={"id": "bc"}, expected=result["revision"])[0], 0
        )
        status, checked = self.cli("check")
        self.assertEqual(status, 0, checked)
        self.assertEqual(checked["counts"]["retained"], 2)

    def test_cli_path_escape_and_bad_json_leave_target_unchanged(self):
        write(self.root / "graph.json", {"nodes": [{"id": "a"}], "edges": []})
        before = (self.root / "graph.json").read_bytes()
        self.assertEqual(self.cli("init", payload={}, model="../outside.json")[0], 1)
        self.assertEqual(self.cli("init", payload={"unknown": True})[0], 1)
        self.assertEqual((self.root / "graph.json").read_bytes(), before)

    def test_real_envelope_cli_preserves_and_checks_machine_contract(self):
        project = project_fixture(self.root)
        write(self.root / "graph.json", project)
        self.assertEqual(self.cli("init", payload={})[0], 0)
        value = json.loads((self.root / "graph.json").read_text())
        self.assertEqual(value["model"]["machine"], project["model"]["machine"])
        value["model"]["machine"]["version"] = "invalid"
        write(self.root / "graph.json", value)
        self.assertEqual(self.cli("check")[0], 1)


if __name__ == "__main__":
    unittest.main()
