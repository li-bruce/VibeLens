"""Multiple independent definitions, overlapping names and real observation identity."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_contracts import validate_chart
from bo_models import machine_registry, network_registry, instance_key, model_inventory
from bo_stategraph import BOStateGraph, bo_validate_export, bo_digest
from bo_observer.protocol import validate_project, validate_snapshot
from bo_observer.adapters.python.bo_executor import BOExecutors
from bo_observer.observation.session import GraphSession
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.web.semantic_names import inventory
from bo_observer.workflow.mapping_contract import (
    validate_plan,
    assess_projections,
    protected_plan_errors,
)
from bo_observer import concepts
from test_concept_models import bound_fixture, approve


def project_fixture():
    """Two objects intentionally share state, event and instance names."""
    base = json.loads(
        (ROOT / "examples/multilanguage/bo_stategraph/project.json").read_text(encoding="utf-8")
    )
    chart = {
        "engine": "bo.fsm",
        "version": "1",
        "state_type": "enum",
        "states": ["idle", "ready"],
        "values": ["idle", "ready"],
        "initial": "idle",
        "events": {"advance": {"payload": {}}},
        "context": {},
        "guards": {},
        "transitions": [{"source": "idle", "dest": "ready", "trigger": "advance"}],
    }
    model = base["model"]
    model.pop("machine")
    model["machines"] = {"file": deepcopy(chart), "approval": deepcopy(chart)}
    model["nodes"] = []
    model["edges"] = []
    model["overview"] = []
    model["source_files"] = ["app.py"]
    model.pop("presentation", None)
    for name in model["machines"]:
        model["overview"].append({"node": name + ":advance"})
        model["edges"].append(
            {
                "id": name + ":changes",
                "from": name + ":advance",
                "to": name + ":ready",
                "type": "data",
                "evidence": "The native operation produces this object's next state",
            }
        )
        model["nodes"].append(
            {
                "id": name + ":advance",
                "kind": "action",
                "layer": "business",
                "label": "Advance " + name,
                "summary": "Advance the " + name,
                "source": {"path": "app.py", "symbol": name + "_advance"},
                "capture": {"in": {}, "out": {}},
            }
        )
        for state in chart["values"]:
            model["nodes"].append(
                {
                    "id": name + ":" + state,
                    "kind": "state",
                    "layer": "state",
                    "state_model_id": name,
                    "value": state,
                    "label": state,
                    "summary": name + " is " + state,
                    "capture": {},
                }
            )
    model["networks"] = [
        {
            "id": name + "-states",
            "layer": "state",
            "state_model_id": name,
            "nodes": [name + ":idle", name + ":ready"],
        }
        for name in model["machines"]
    ]
    return base


def bound_networks():
    """Extend a confirmed grant design with a second independent object lifecycle."""
    doc, model, acceptance = bound_fixture()
    second = deepcopy(doc["state_models"][0])
    second["id"] = "archive"
    second["subject"] = deepcopy(second["subject"])
    obj = deepcopy(
        next(item for item in doc["objects"] if item["id"] == second["subject"]["object"])
    )
    obj["id"] = "archived_object"
    doc["objects"].append(obj)
    second["subject"]["object"] = obj["id"]
    doc["state_models"].append(second)
    doc["confirmations"] = []
    approve(doc)
    chart = model.pop("machine")
    model["machines"] = {"grant": chart, "archive": deepcopy(chart)}
    for node in model["nodes"]:
        if node.get("kind") == "state":
            node["state_model_id"] = "grant"
    model["nodes"] += [
        {**deepcopy(node), "id": node["id"] + ":archive", "state_model_id": "archive"}
        for node in model["nodes"]
        if node.get("kind") == "state"
    ]
    binding = model["concepts"]
    binding["schema"] = "bo-concept-bindings/v2"
    binding.pop("primary_state_model")
    binding["state_models"] = {"grant": "grant", "archive": "archive"}
    binding["objects"]["archive"] = deepcopy(second["subject"])
    binding["events"].update(
        {
            key.replace(":grant:", ":archive:"): deepcopy(value)
            for key, value in list(binding["events"].items())
        }
    )
    binding["semantic_revision"] = concepts.assess(doc)["semantic_revision"]
    return doc, model, acceptance


def write_project(root):
    """A runnable owned-source fixture, with tool code staying in the installed Skill."""
    project = project_fixture()
    for node in project["model"]["nodes"]:
        if node["kind"] == "action":
            node["capture"]["out"] = {"state": "string"}
    (root / "app.py").write_text(
        'def file_advance():\n    """Make an uploaded file ready."""\n    return "ready"\n\ndef approval_advance():\n    """Complete review without changing the file lifecycle."""\n    return "ready"\n',
        encoding="utf-8",
    )
    (root / "intent.json").write_text(
        json.dumps({"project_id": project["project_id"], "requirements": []}), encoding="utf-8"
    )
    (root / "bo_stategraph").mkdir(exist_ok=True)
    (root / "bo_stategraph/project.json").write_text(json.dumps(project), encoding="utf-8")
    return project


class ModelNetworkTests(unittest.TestCase):
    def test_registry_preserves_independent_graphs_and_rejects_ambiguous_sources(self):
        project = project_fixture()
        self.assertEqual(set(validate_chart(project["model"])["models"]), {"file", "approval"})
        validate_project(project)
        self.assertEqual(len(network_registry(project["model"])), 2)
        self.assertEqual(
            {item["id"] for item in model_inventory(project["model"])["state_models"]},
            {"file", "approval"},
        )
        project["model"]["machine"] = deepcopy(project["model"]["machines"]["file"])
        with self.assertRaises(ValueError):
            validate_chart(project["model"])

    def test_every_machine_is_validated_even_when_the_first_is_legal(self):
        model = project_fixture()["model"]
        model["machines"]["approval"]["transitions"][0]["dest"] = "missing"
        with self.assertRaises(ValueError):
            validate_chart(model)

    def test_observation_and_transition_checks_are_partitioned_by_model(self):
        model = project_fixture()["model"]
        graph = BOStateGraph(model, build_id="b")

        def observe(mid, state, revision, event=None):
            return graph.bo_observe(
                "1",
                state_model_id=mid,
                state=state,
                context={},
                revision=revision,
                evidence_id=f"{mid}-{revision}",
                build_id="b",
                event=event,
                payload={},
            )

        observe("file", "idle", 0)
        observe("approval", "idle", 0)
        self.assertEqual(observe("file", "ready", 1, "advance")["status"], "observed")
        self.assertEqual(
            {
                entry["observed"]["state_model_id"]: entry["observed"]["state"]
                for entry in graph.bo_instances()
            },
            {"file": "ready", "approval": "idle"},
        )
        wrong = observe("approval", "idle", 1, "advance")
        self.assertEqual(wrong["status"], "mismatch")
        self.assertEqual(wrong["observed"]["state"], "idle")
        self.assertFalse(observe("file", "idle", 0)["accepted"])
        public = graph.bo_export()
        self.assertEqual(bo_validate_export(public)["instances"], public["instances"])
        self.assertEqual(graph.bo_definition(), {"machines": model["machines"]})
        with self.assertRaises(ValueError):
            graph.bo_candidates("idle", "advance")

    def test_executor_registry_retains_strict_portable_capabilities(self):
        machines = project_fixture()["model"]["machines"]
        executor = BOExecutors(machines)
        self.assertEqual(executor.step("approval", "idle", "advance", {})["state"], "ready")
        with self.assertRaises(ValueError):
            executor.step("unknown", "idle", "advance", {})
        machines["file"]["execution"] = {"unsupported": True}
        with self.assertRaises(ValueError):
            BOExecutors(machines)

    def test_cross_model_guard_uses_native_facts_without_merging_definitions(self):
        """A native rule can connect two lifecycles; registration alone cannot advance them."""
        model = project_fixture()["model"]
        model["machines"]["file"]["guards"] = {"reviewed": {}}
        model["machines"]["file"]["transitions"][0]["conditions"] = "reviewed"
        model["edges"].append(
            {
                "id": "review-controls-file",
                "from": "approval:ready",
                "to": "file:advance",
                "type": "guard",
                "evidence": "File advancement reads the independently stored review state",
            }
        )
        native = {"file": "idle", "approval": "idle"}
        executor = BOExecutors(
            model["machines"],
            {"file": {"reviewed": lambda context, payload: native["approval"] == "ready"}},
        )
        graph = BOStateGraph(model, build_id="b")
        for mid in native:
            graph.bo_observe(
                "1",
                state_model_id=mid,
                state=native[mid],
                context={},
                revision=0,
                evidence_id=mid + ":initial",
                build_id="b",
            )
        with self.assertRaisesRegex(ValueError, "no enabled"):
            executor.step("file", native["file"], "advance", {})
        self.assertEqual(native["file"], "idle")
        for mid in ("approval", "file"):
            result = executor.step(mid, native[mid], "advance", {})
            native[mid] = result["state"]
            observed = graph.bo_observe(
                "1",
                state_model_id=mid,
                context={},
                revision=1,
                evidence_id=mid + ":advance",
                build_id="b",
                **result,
            )
            self.assertEqual(observed["status"], "observed")
        self.assertEqual(
            {
                row["observed"]["state_model_id"]: row["observed"]["state"]
                for row in graph.bo_instances()
            },
            native,
        )
        self.assertIn(
            "review-controls-file", {edge["id"] for edge in graph.bo_export()["model"]["edges"]}
        )

    def test_snapshot_protocol_requires_explicit_machine_and_keeps_context_local(self):
        project = project_fixture()
        snapshot = {
            "protocol": "bo-snapshot/v2",
            "project_id": project["project_id"],
            "model_revision": project["model"]["revision"],
            "build_id": "b",
            "run_id": "r",
            "producer_id": "p",
            "instance_id": "1",
            "state_model_id": "file",
            "state": "idle",
            "context": {},
            "revision": 0,
            "evidence_id": "e",
            "event": None,
            "guards": None,
            "payload": None,
            "configuration": None,
        }
        validate_snapshot(snapshot, project, "b")
        snapshot["state_model_id"] = "other"
        with self.assertRaises(ValueError):
            validate_snapshot(snapshot, project, "b")
        snapshot.pop("state_model_id")
        snapshot["protocol"] = "bo-snapshot/v1"
        with self.assertRaises(ValueError):
            validate_snapshot(snapshot, project, "b")
        self.assertNotEqual(instance_key("a:b", "c", "file"), instance_key("a", "b:c", "file"))

    def test_multiple_confirmed_models_bind_and_missing_second_model_fails(self):
        doc, model, cases = bound_networks()
        result = concepts.check_binding(doc, model, acceptance=cases)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["bound_state_models"], ["archive", "grant"])
        projection = concepts.bind_projection(doc, model, acceptance=cases)
        maps = {
            edge["from"]: edge["to"]
            for edge in projection["edges"]
            if edge.get("mapping_role") == "implements"
        }
        self.assertNotEqual(maps["state:archive:active"], maps["state:grant:active"])
        del model["concepts"]["state_models"]["archive"]
        result = concepts.check_binding(doc, model, acceptance=cases)
        self.assertIn("unbound_state_model", {error["code"] for error in result["errors"]})

    def test_meaning_change_in_second_model_requires_new_confirmation(self):
        doc, model, cases = bound_networks()
        doc["state_models"][1]["transitions"][0]["dest"] = "inactive"
        result = concepts.check_binding(doc, model, acceptance=cases)
        self.assertFalse(result["valid"])
        self.assertIn(
            "state_semantics_changed_during_binding", {error["code"] for error in result["errors"]}
        )

    def test_any_layer_can_have_several_networks_and_shared_members(self):
        model = project_fixture()["model"]
        model["networks"] += [
            {"id": "workflow-a", "layer": "business", "nodes": ["file:advance"]},
            {
                "id": "workflow-b",
                "layer": "business",
                "nodes": ["approval:advance", "file:advance"],
            },
        ]
        self.assertEqual(len(network_registry(model)), 4)
        model["networks"][0]["nodes"].append("unknown")
        with self.assertRaises(ValueError):
            validate_chart(model)

    def test_real_capture_recording_export_and_iteration_keep_both_models(self):
        """Exercise actual native functions and probe queues, not fabricated replay rows."""
        (ROOT / ".validation").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            project = write_project(root)
            session = GraphSession(root)
            probe = BOProbe(project, session.manifest["build_id"], sink=session.bo_sink)
            session.bo_bind_capture(
                scope_setter=probe.bo_set_scope,
                flush_capture=lambda: probe.flush(3),
                health=probe.bo_health,
            )
            try:
                import runpy

                native = runpy.run_path(str(root / "app.py"))
                recording_id = session.recordings.start()["id"]

                def capture(model_id, state, revision):
                    event = probe.record(
                        model_id + ":advance",
                        "change",
                        lambda: {"outputs": {"state": state}},
                        attempt="shared-caller",
                        entity="1",
                        revision=revision,
                    )
                    self.assertTrue(
                        probe.snapshot(
                            "1",
                            state,
                            {},
                            revision,
                            event,
                            state_model_id=model_id,
                            event="advance" if revision else None,
                        )
                    )
                    self.assertTrue(probe.flush(3))
                    return event

                capture("file", "idle", 0)
                capture("approval", "idle", 0)
                capture("file", native["file_advance"](), 1)
                view = session.view()
                self.assertEqual(
                    {
                        cfg["state_model_id"]: cfg["phase"]
                        for cfg in view["machine"]["configurations"]
                    },
                    {"file": "ready", "approval": "idle"},
                )
                capture("approval", native["approval_advance"](), 1)
                session.recordings.stop()
                recording = session.recordings.get(recording_id)
                self.assertEqual(recording["gaps"], [])
                self.assertEqual(len(recording["events"]), 4)
                self.assertEqual(len(recording["runtime_frames"]["frames"]), 4)
                for frame in recording["runtime_frames"]["frames"]:
                    cfg = frame["machine"]["configurations"][0]
                    self.assertEqual(cfg["state_model_id"], frame["machine"]["state_model_id"])
                    self.assertEqual(cfg["state_revision"], frame["revision"])
                self.assertEqual(probe.bo_health()["errors"], 0)
                bo_validate_export(session.export())
                # A second-model source edit must block admission until reviewed reload.
                source = root / "app.py"
                source.write_text(
                    source.read_text(encoding="utf-8").replace(
                        'return "ready"', 'return "ready"  # reviewed implementation', 1
                    ),
                    encoding="utf-8",
                )
                self.assertNotEqual(session.binding()["status"], "current")
            finally:
                probe.close()
                session.close()
            # Register a new state only on approval. Every model is revalidated.
            machine = project["model"]["machines"]["approval"]
            machine["states"].append("archived")
            machine["values"].append("archived")
            machine["events"]["archive"] = {"payload": {}}
            machine["transitions"].append(
                {"source": "ready", "dest": "archived", "trigger": "archive"}
            )
            with self.assertRaises(ValueError):
                validate_chart(project["model"])
            project["model"]["nodes"].append(
                {
                    "id": "approval:archived",
                    "kind": "state",
                    "layer": "state",
                    "state_model_id": "approval",
                    "value": "archived",
                    "label": "Archived",
                    "summary": "Review archived",
                }
            )
            validate_project(project)
            self.assertEqual(project["model"]["machines"]["file"]["values"], ["idle", "ready"])
            # Reload the changed build, execute the added operation, and capture
            # both models again. A schema-only update is not runtime acceptance.
            with (root / "app.py").open("a", encoding="utf-8") as stream:
                stream.write(
                    '\ndef approval_archive():\n    """Archive a completed review."""\n    return "archived"\n'
                )
            archive = deepcopy(
                next(node for node in project["model"]["nodes"] if node["id"] == "approval:advance")
            )
            archive.update(
                id="approval:archive",
                label="Archive review",
                source={"path": "app.py", "symbol": "approval_archive"},
            )
            project["model"]["nodes"].append(archive)
            project["model"]["edges"].append(
                {
                    "id": "approval:archives",
                    "from": "approval:archive",
                    "to": "approval:archived",
                    "type": "data",
                    "evidence": "The new native archive function returns the archived state",
                }
            )
            project["model"]["networks"][1]["nodes"].append("approval:archived")
            project["model"]["revision"] += "-iteration"
            (root / "bo_stategraph/project.json").write_text(json.dumps(project), encoding="utf-8")
            revised = GraphSession(root)
            revised_probe = BOProbe(project, revised.manifest["build_id"], sink=revised.bo_sink)
            try:
                native = runpy.run_path(str(root / "app.py"))
                for mid, operation, revision in (
                    ("file", None, 0),
                    ("approval", None, 0),
                    ("approval", "advance", 1),
                    ("approval", "archive", 2),
                ):
                    state = "idle" if operation is None else native[mid + "_" + operation]()
                    event = revised_probe.record(
                        mid + ":" + (operation or "advance"),
                        "change",
                        lambda: {"outputs": {"state": state}},
                        entity="1",
                        revision=revision,
                    )
                    self.assertTrue(
                        revised_probe.snapshot(
                            "1", state, {}, revision, event, state_model_id=mid, event=operation
                        )
                    )
                    self.assertTrue(revised_probe.flush(3))
                current = revised.view()
                self.assertEqual(revised.binding()["status"], "current")
                self.assertEqual(
                    {
                        cfg["state_model_id"]: cfg["phase"]
                        for cfg in current["machine"]["configurations"]
                    },
                    {"file": "idle", "approval": "archived"},
                )
                self.assertEqual(len(current["model"]["networks"][1]["nodes"]), 3)
                self.assertEqual(revised_probe.bo_health()["errors"], 0)
                bo_validate_export(revised.export())
            finally:
                revised_probe.close()
                revised.close()

    def test_semantic_names_are_model_qualified(self):
        model = project_fixture()["model"]
        rows = inventory({"model": model})
        states = [row for row in rows if row["category"] == "states"]
        self.assertEqual(
            {row["id"] for row in states},
            {'["file","idle"]', '["file","ready"]', '["approval","idle"]', '["approval","ready"]'},
        )

    def test_mapping_gate_checks_every_model_against_separately_read_facts(self):
        """Identical instance IDs cannot hide a missing or wrong second-model value."""
        model = project_fixture()["model"]
        graph = BOStateGraph(model, build_id="b")
        plan = {
            "schema": "bo-mapping/v2",
            "state_models": ["file", "approval"],
            "source": "Native object store",
            "cases": ["independent-objects"],
            "modes": ["on", "off", "fault"],
            "actual_collection": ["rows"],
            "actual_id": ["id"],
            "actual_model_id": ["state_model_id"],
            "fields": [
                {"id": key, "node": "file:advance", "actual": [key], "mapped": [key]}
                for key in ("state_model_id", "state", "revision", "build_id")
            ],
            "export": {"case": "independent-objects", "mode": "on"},
        }
        validate_plan(plan, model)
        # These rows stand for the test runner's direct application-store read.
        rows = [
            {"id": "1", "state_model_id": mid, "state": state, "revision": 0, "build_id": "b"}
            for mid, state in (("file", "ready"), ("approval", "idle"))
        ]
        machine = {
            "configurations": [
                {
                    "attempt": row["id"],
                    "state_model_id": row["state_model_id"],
                    "phase": row["state"],
                    "state_revision": row["revision"],
                    "run_build_id": "b",
                }
                for row in rows
            ]
        }
        projection = {"build_id": "b", "machine": machine, "instances": graph.bo_instances(machine)}
        payload = {
            "build_id": "b",
            "stategraph_export": graph.bo_export(runtime={"machine": machine}),
            "runs": [
                {
                    "case": "independent-objects",
                    "mode": mode,
                    "rows": deepcopy(rows),
                    "projection": deepcopy(projection),
                }
                for mode in plan["modes"]
            ],
        }
        self.assertEqual(assess_projections(payload, plan, model, "b")[0], [])
        # The actual approval state disagrees even though the file still matches.
        bad = deepcopy(payload)
        bad["runs"][0]["rows"][1]["state"] = "ready"
        self.assertTrue(assess_projections(bad, plan, model, "b")[0])
        bad = deepcopy(payload)
        bad["runs"][1]["rows"].pop()
        self.assertTrue(assess_projections(bad, plan, model, "b")[0])
        for change in ({"state_models": ["file"]}, {"actual_model_id": []}):
            bad_plan = {**plan, **change}
            with self.assertRaises(ValueError):
                validate_plan(bad_plan, model)
            self.assertTrue(protected_plan_errors(plan, bad_plan))
        tampered = deepcopy(payload["stategraph_export"])
        tampered["instances"][1]["observed"]["state_model_id"] = "file"
        tampered["sha256"] = bo_digest(
            {key: value for key, value in tampered.items() if key != "sha256"}
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            bo_validate_export(tampered)

    def test_network_membership_is_supported_across_every_layer(self):
        model = project_fixture()["model"]
        for layer in ("business", "state", "rules", "entry", "structure", "symbols", "data"):
            for number in range(2):
                node_id = f"{layer}-{number}"
                model["nodes"].append({"id": node_id, "layer": layer})
                model["networks"].append(
                    {"id": "net:" + node_id, "layer": layer, "nodes": [node_id]}
                )
        self.assertEqual(len(network_registry(model)), 16)
        model["networks"].append(deepcopy(model["networks"][-1]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            network_registry(model)

    def test_javascript_executor_registry_matches_native_results(self):
        uri = (
            ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs"
        ).as_uri()
        script = (
            f"import {{BOExecutors}} from {json.dumps(uri)};"
            + "const chunks=[];for await(const c of process.stdin)chunks.push(c); const models=JSON.parse(Buffer.concat(chunks));const ex=new BOExecutors(models); console.log(JSON.stringify([ex.step('file','idle','advance',{}),ex.step('approval','idle','advance',{})]));"
        )
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            input=json.dumps(project_fixture()["model"]["machines"]),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([r["state"] for r in json.loads(result.stdout)], ["ready", "ready"])

    def test_javascript_producer_sends_both_models_to_the_real_collector(self):
        """Node uses the same token-protected JSON ingress as a separate application."""
        from bo_observer.service import make_server

        (ROOT / ".validation").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            project = write_project(Path(folder))
            session = GraphSession(folder)
            server = make_server(session, 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            uri = (
                ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs"
            ).as_uri()
            script = (
                f"import {{ BOProbe, BOExecutors }} from {json.dumps(uri)};"
                + """
const chunks = []; for await (const chunk of process.stdin) chunks.push(chunk);
const options = JSON.parse(Buffer.concat(chunks));
const probe = new BOProbe(options), executors = new BOExecutors(options.project.model.machines);
for (const mid of ['file', 'approval']) {
  let state = 'idle';
  for (const revision of [0, 1]) {
    if (revision) state = executors.step(mid, state, 'advance', {}).state;
    const evidence = probe.record(mid + ':advance', 'change', () => ({outputs: {state}}), {entity:'1', attempt:'same', revision});
    if (!probe.snapshot('1', state, {}, revision, evidence, {stateModelId:mid, event:revision ? 'advance' : null})) throw Error('snapshot omitted');
  }
}
if (!await probe.flush(10000)) throw Error('capture did not drain');
console.log(JSON.stringify(probe.bo_health()));
"""
            )
            try:
                options = {
                    "project": project,
                    "buildId": session.manifest["build_id"],
                    "endpoint": f"http://127.0.0.1:{server.server_port}",
                    "token": server.bo_token,
                    "timeout": 5000,
                }
                result = subprocess.run(
                    ["node", "--input-type=module", "-e", script],
                    input=json.dumps(options),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["errors"], 0, result.stdout)
                self.assertEqual(
                    {
                        cfg["state_model_id"]: cfg["phase"]
                        for cfg in session.view()["machine"]["configurations"]
                    },
                    {"file": "ready", "approval": "ready"},
                )
                self.assertEqual(len(session.frames), 4)
                bo_validate_export(session.export())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(5)


if __name__ == "__main__":
    unittest.main()
