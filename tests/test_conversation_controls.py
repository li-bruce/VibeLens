"""Presentation controls require this conversation's explicit intent and preserve facts."""

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.control.scope import ControlScope, user_command
from bo_observer.control.selection import (
    build_plan,
    validate_evidence,
    validate_plan,
    ClarificationRequired,
)
from bo_observer.graph.behavior_model import digest
from bo_observer.web.bo_web import BOWeb
from bo_observer.web.bo_design import BODesign
from bo_observer.control.cli import main as control_main
from bo_observer.control.cli import get as control_get
from bo_observer.web.view_preferences import Preferences, PreferenceConflict
from bo_observer.observation.observation_scope import observer_route


class ControlTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".validation").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.scope = ControlScope(self.root)
        self.environment = patch.dict(os.environ, {"CODEX_THREAD_ID": "chat-a"})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.artifact = json.loads(
            (ROOT / "tests/fixtures/conversation-control-case.json").read_text(encoding="utf-8")
        )
        self.view = self.artifact["view"]
        self.project = (
            self.view.get("layout_id")
            or self.view["model"].get("project_id")
            or self.view["model"]["presentation"]["layout_id"]
        )
        self.active = self.scope.activate("$vibelens for this project", self.project)
        self.spec = {
            "action": "view",
            "label": "Approval path",
            "anchors": ["review-policy"],
            "depth": 1,
            "nodes": ["business", "decision", "data"],
            "edges": ["flow", "guard", "data", "call"],
            "layout": "layered",
        }

    def test_fixture_remains_the_original_controller_input(self):
        path = ROOT / "tests/fixtures/conversation-control-case.json"
        provenance = json.loads(path.with_suffix(".provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), provenance["sha256"])
        self.assertIn("review-policy", {node["id"] for node in self.view["model"]["nodes"]})

    def test_missing_host_identity_does_not_activate_a_global_scope(self):
        isolated = ControlScope(self.root / "without-host")
        with patch.dict(os.environ):
            os.environ.pop("CODEX_THREAD_ID", None)
            with self.assertRaisesRegex(ValueError, "host conversation ID is required"):
                isolated.activate("$vibelens for this project", self.project)
        self.assertFalse(isolated.directory.exists())

    def test_prefix_is_required_for_every_mutation(self):
        plan = build_plan(self.view, self.spec)
        before = self.scope.for_view(self.active["session"])
        for message in [
            "Show approval",
            "Example: /vibelens show approval",
            "```\n/vibelens show approval\n```",
            "> /vibelens show approval",
            "/vibelens-other show approval",
        ]:
            with self.subTest(message=message), self.assertRaises(ValueError):
                self.scope.publish(message, plan)
        self.assertEqual(self.scope.for_view(self.active["session"]), before)
        self.assertEqual(user_command("$vibelens /vibelens show approval"), "show approval")

    def test_activation_is_not_inferred_from_a_quoted_example(self):
        for message in ["I read about $vibelens", "Example: $vibelens", "`$vibelens`"]:
            with self.assertRaises(ValueError):
                self.scope.activate(message, self.project)

    def test_two_chats_and_projects_are_isolated(self):
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "chat-b"}):
            with self.assertRaises(ValueError):
                self.scope.authorized("/vibelens show approval")
            with self.assertRaises(ValueError):
                self.scope.authorized("/vibelens show approval", "chat-a")
            other = self.scope.activate("$vibelens", self.project)
        self.assertNotEqual(other["session"], self.active["session"])
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as directory:
            with self.assertRaises(OSError):
                ControlScope(directory).for_view(self.active["session"])

    def test_private_preferences_preserve_default_and_peer(self):
        default = Preferences(self.root, self.project)
        document = default.read()
        document["entries"]["business-observer.layout.v2:test"] = json.dumps(
            {
                "positions": {"publish": {"x": 17, "y": 29}},
                "annotations": {"publish": {"note": "Keep this"}},
            }
        )
        default.save(document)
        original = default.path.read_bytes()
        mine = self.scope.preferences(self.active["session"])
        value = mine.read()
        self.assertEqual(value["entries"], default.read()["entries"])
        mine.save(value)
        with self.assertRaises(PreferenceConflict):
            mine.save(value)
        self.assertEqual(default.path.read_bytes(), original)
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "chat-b"}):
            peer = self.scope.activate("$vibelens", self.project)
        self.assertNotEqual(self.scope.preferences(peer["session"]).path, mine.path)
        self.assertEqual(
            self.scope.preferences(peer["session"]).read()["entries"], default.read()["entries"]
        )

    def test_ambiguous_labels_require_a_real_choice(self):
        view = deepcopy(self.view)
        view["model"]["nodes"].append(
            {"id": "another-rule", "label": view["model"]["nodes"][0]["label"], "kind": "condition"}
        )
        spec = {**self.spec, "anchors": [view["model"]["nodes"][0]["label"]]}
        with self.assertRaises(ClarificationRequired) as error:
            build_plan(view, spec)
        self.assertEqual(len(error.exception.question["candidates"]), 2)

    def test_control_cannot_edit_source_or_bypass_validation(self):
        for patch_value in [
            {"action": "edit_source"},
            {"source": "policy.py"},
            {"layout": "run-python"},
            {"nodes": ["invented"]},
            {"depth": True},
        ]:
            with self.subTest(patch=patch_value), self.assertRaises(ValueError):
                build_plan(self.view, {**self.spec, **patch_value})
        plan = build_plan(self.view, self.spec)
        plan["script"] = "print('not executed')"
        with self.assertRaises(ValueError):
            self.scope.publish("/vibelens run this", plan)

    def test_original_paths_boundaries_and_depth(self):
        original = deepcopy(self.view)
        plan = build_plan(self.view, self.spec)
        self.assertTrue(plan["edge_ids"])
        self.assertTrue(
            set(plan["edge_ids"]) <= {edge["id"] for edge in self.view["model"]["edges"]}
        )
        shallow = build_plan(self.view, {**self.spec, "depth": 0})
        self.assertEqual(shallow["node_ids"], ["review-policy"])
        self.assertTrue(shallow["boundaries"])
        self.assertEqual(self.view, original)
        self.assertEqual(
            plan["view_id"], build_plan(self.view, {**self.spec, "depth": 0})["view_id"]
        )

    def test_requested_types_are_used_before_neighbor_expansion(self):
        view = deepcopy(self.view)
        view["model"]["nodes"].append(
            {"id": "state_new", "kind": "state", "layer": "state", "parent": "review-policy"}
        )
        edge = {"id": "initial-state", "from": "state_new", "to": "review-policy", "type": "guard"}
        view["model"]["edges"].append(edge)
        before = deepcopy(view)
        plan = build_plan(view, {**self.spec, "depth": 2})
        self.assertNotIn("state_new", plan["node_ids"])
        self.assertNotIn(edge["id"], plan["edge_ids"])
        self.assertIn(edge, plan["boundaries"])
        self.assertIn("review-policy", plan["node_ids"])
        validate_evidence(plan, view)
        self.assertEqual(view, before)

        # A structurally valid hand-written plan must not bypass the typed view.
        invalid = build_plan(view, {**self.spec, "nodes": [*self.spec["nodes"], "state"]})
        invalid["filters"]["nodes"].remove("state")
        invalid["filters"]["regions"].remove("state")
        invalid["id"] = "control-" + digest({k: v for k, v in invalid.items() if k != "id"})[:20]
        with self.assertRaisesRegex(ValueError, "node type"):
            validate_evidence(invalid, view)

    def test_cross_type_paths_keep_original_boundary_nodes(self):
        view = deepcopy(self.view)
        view["model"]["nodes"] = [
            {"id": "start", "kind": "action", "layer": "business"},
            {"id": "value", "kind": "data"},
            {"id": "end", "kind": "action", "layer": "business"},
        ]
        view["model"]["edges"] = [
            {"id": "first", "from": "start", "to": "value", "type": "data"},
            {"id": "second", "from": "value", "to": "end", "type": "data"},
        ]
        spec = {**self.spec, "anchors": ["start", "end"], "nodes": ["business"]}
        boundary = build_plan(view, spec)
        self.assertEqual(boundary["context_node_ids"], ["value"])
        self.assertEqual(boundary["node_ids"], ["end", "start", "value"])
        self.assertEqual(boundary["edge_ids"], ["first", "second"])
        self.assertEqual(boundary["filters"]["nodes"], ["business"])
        validate_evidence(boundary, view)
        visible = build_plan(view, {**spec, "nodes": ["business", "data"], "depth": 0})
        self.assertEqual(visible["node_ids"], ["end", "start", "value"])
        self.assertEqual(visible["edge_ids"], ["first", "second"])
        self.assertEqual(visible["context_node_ids"], [])

        # A longer hidden chain cannot be drawn as a one-hop boundary. Ask for
        # its types before publication instead of inventing a direct edge.
        view["model"]["nodes"] = [view["model"]["nodes"][0], view["model"]["nodes"][-1]] + [
            {"id": "a", "kind": "data"},
            {"id": "b", "kind": "data"},
            {"id": "c", "kind": "data"},
        ]
        sequence = ["start", "a", "b", "c", "end"]
        view["model"]["edges"] = [
            {"id": str(index), "from": first, "to": second, "type": "data"}
            for index, (first, second) in enumerate(zip(sequence, sequence[1:]))
        ]
        with self.assertRaisesRegex(ValueError, "node type"):
            build_plan(view, spec)

    def test_control_node_membership_matches_actual_viewer_types(self):
        from bo_observer.control.selection import view_types

        nodes = [
            {"kind": "action", "layer": "business", "source": {}},
            {"kind": "state", "source": {}},
            {"kind": "decision", "source": {}},
            {"execution_role": "join"},
            {"execution_role": "resource"},
            {"kind": "data", "semantic_role": "state_parameter", "source": {}, "field": {}},
            {"semantic_roles": ["business"], "kind": "function"},
            *(
                {"code_role": role}
                for role in (
                    "file",
                    "directory",
                    "class",
                    "function",
                    "parameter",
                    "endpoint",
                    "unresolved",
                )
            ),
            *(
                {"data_role": role, "layer": "business"}
                for role in ("store", "dataset", "column", "query", "transform")
            ),
            *({"kind": kind} for kind in ("resource", "data", "wait", "effect", "action")),
            *self.view["model"]["nodes"],
        ]
        module = (ROOT / "skills/vibelens/assets/stategraph-viewer/graph-core.js").as_uri()
        script = f"import {{viewTypes}} from {json.dumps(module)}; console.log(JSON.stringify({json.dumps(nodes)}.map(n => viewTypes(n).sort())));"
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual([sorted(view_types(node)) for node in nodes], json.loads(result.stdout))

    def test_stale_graph_and_recording_fail_without_rewriting_events(self):
        recording = deepcopy(self.artifact["recording"])
        before = deepcopy(recording)
        plan = build_plan(self.view, {**self.spec, "action": "replay", "loop": True}, recording)
        self.assertGreater(plan["recording"]["selected_events"], 0)
        self.assertLess(plan["recording"]["selected_events"], plan["recording"]["total_events"])
        validate_evidence(plan, self.view, recording)
        stale = deepcopy(self.view)
        stale["model"]["revision"] += "-changed"
        with self.assertRaises(ValueError):
            validate_evidence(plan, stale, recording)
        recording["events"][0]["outputs"]["changed"] = True
        with self.assertRaises(ValueError):
            validate_evidence(plan, self.view, recording)
        self.assertEqual(self.artifact["recording"], before)

    def test_end_revokes_only_this_conversation(self):
        self.scope.end("/vibelens stop")
        with self.assertRaises(ValueError):
            self.scope.authorized("/vibelens show approval")

    def test_nested_plans_are_checked_even_with_a_recomputed_digest(self):
        original = build_plan(self.view, self.spec)
        for key, value in [
            ("node_ids", []),
            ("anchors", ["unknown"]),
            ("filters", {"nodes": ["unknown"], "edges": ["flow"], "regions": ["business"]}),
            ("boundaries", [{}]),
            ("limits_hit", "yes"),
            ("recording", {"id": "unrequested"}),
        ]:
            plan = deepcopy(original)
            plan[key] = value
            plan["id"] = (
                "control-" + digest({key: value for key, value in plan.items() if key != "id"})[:20]
            )
            with self.subTest(field=key), self.assertRaises(ValueError):
                validate_plan(plan)

    def test_design_graph_controls_work_before_source_and_runtime_exist(self):
        project = self.root / "design"
        project.mkdir()
        doc = json.loads(
            (ROOT / "skills/vibelens/assets/discovery.example.json").read_text(encoding="utf-8")
        )
        doc.update(project_id="design-project", layout_id="design-project")
        path = project / "discovery.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        before = path.read_bytes()
        view = BODesign(project).view()
        self.assertNotIn("revision", view["model"])
        spec = {**self.spec, "anchors": [view["model"]["nodes"][0]["id"]], "depth": 0}
        plan = build_plan(view, spec)
        validate_evidence(plan, view)
        self.assertEqual(plan["base"]["model_revision"], view["manifest"]["build_id"])
        with (
            patch("bo_observer.control.cli.get", return_value=view),
            redirect_stdout(io.StringIO()) as output,
        ):
            code = control_main(
                [
                    "activate",
                    "--root",
                    str(project),
                    "--url",
                    "http://127.0.0.1:8830",
                    "--message",
                    "$vibelens for this project",
                ]
            )
        self.assertEqual(code, 0, output.getvalue())
        # A setup may declare its future model path before that file exists.
        (project / "sync.json").write_text(
            json.dumps({"model": "behavior.json", "discovery": "discovery.json"}), encoding="utf-8"
        )
        with (
            patch("bo_observer.control.cli.get", return_value=view),
            redirect_stdout(io.StringIO()) as output,
        ):
            code = control_main(
                [
                    "activate",
                    "--root",
                    str(project),
                    "--url",
                    "http://127.0.0.1:8830",
                    "--message",
                    "$vibelens for this project",
                ]
            )
        self.assertEqual(code, 0, output.getvalue())
        with (
            patch("bo_observer.control.cli.get", return_value=view),
            redirect_stdout(io.StringIO()) as output,
        ):
            code = control_main(
                [
                    "inspect",
                    "--root",
                    str(project),
                    "--url",
                    "http://127.0.0.1:8830",
                    "--message",
                    "/vibelens show the draft",
                ]
            )
        self.assertEqual(code, 0, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())["result"]["recordings"], [])
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((project / "behavior.json").exists())
        self.assertEqual(view["events"], [])

    def test_invented_relation_and_replay_events_are_rejected(self):
        recording = deepcopy(self.artifact["recording"])
        plan = build_plan(self.view, {**self.spec, "action": "replay"}, recording)
        for key, value in [
            ("edge_ids", ["invented"]),
            ("recording", {**plan["recording"], "event_ids": ["invented"], "selected_events": 1}),
        ]:
            altered = deepcopy(plan)
            altered[key] = value
            altered["id"] = (
                "control-"
                + digest({key: value for key, value in altered.items() if key != "id"})[:20]
            )
            with self.subTest(field=key), self.assertRaises(ValueError):
                validate_evidence(altered, self.view, recording)

    def test_disconnected_paths_and_exceeded_budgets_fail(self):
        view = deepcopy(self.view)
        view["model"]["nodes"].append({"id": "isolated", "label": "Isolated", "kind": "action"})
        with self.assertRaisesRegex(ValueError, "No declared path"):
            build_plan(view, {**self.spec, "anchors": ["upload", "isolated"]})
        with self.assertRaisesRegex(ValueError, "display budget"):
            build_plan(self.view, {**self.spec, "anchors": ["upload", "publish"], "max_nodes": 1})

    def test_missing_and_stale_web_bindings_fail_closed(self):
        plan = build_plan(self.view, self.spec)
        self.scope.publish("/vibelens show approval", plan)
        web = BOWeb(self.root)
        route = "/api/vibelens/control?vl_session=" + self.active["session"]
        result = web.get(route)
        self.assertIsNone(result["plan"])
        self.assertEqual(result["result"]["status"], "rejected")
        web.control_view = lambda: self.view
        self.assertEqual(web.get(route)["plan"], plan)
        stale = deepcopy(self.view)
        stale["model"]["revision"] += "-changed"
        web.control_view = lambda: stale
        result = web.get(route)
        self.assertIsNone(result["plan"])
        self.assertEqual(result["result"]["status"], "rejected")

    def test_personal_control_configuration_is_excluded_from_core_exports(self):
        import fnmatch

        for name in [
            "examples/delivery/ownership.json",
            "examples/team-archive/ownership.json",
            "skills/vibelens/assets/ownership.example.json",
        ]:
            config = json.loads((ROOT / name).read_text(encoding="utf-8"))
            for private in [
                "bo_stategraph/config/control/chat.json",
                "bo_stategraph/config/views/conversations/chat.json",
            ]:
                self.assertTrue(
                    any(
                        fnmatch.fnmatchcase(private, pattern) for pattern in config["core_exclude"]
                    ),
                    (name, private),
                )

    def test_observer_controls_are_never_business_routes(self):
        for route in [
            "/api/vibelens/control",
            "/api/vibelens/control/context",
            "/api/vibelens/control?vl_session=abc",
            "/api/preferences?vl_session=abc",
        ]:
            self.assertTrue(observer_route(route))
        self.assertFalse(observer_route("/api/login"))
        self.assertFalse(observer_route("/api/messages"))

    def test_http_controls_ignore_large_unrelated_runtime_history(self):
        """Model controls do not need a live response's retained event/frame bodies."""
        web = BOWeb(self.root)
        live = deepcopy(self.view)
        live["runtime_frames"] = {"transport_test_payload": "x" * (9 * 1024 * 1024)}
        web.control_view = lambda: live
        full_body = json.dumps(live).encode()
        self.assertGreater(len(full_body), 8 * 1024 * 1024)
        (self.root / "bo_stategraph/project.json").write_text(
            json.dumps({"project_id": self.project}), encoding="utf-8"
        )
        spec = self.root / "request.json"
        spec.write_text(json.dumps(self.spec), encoding="utf-8")
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                requests.append(self.path)
                if self.path in {"/api/view", "/oversize"}:
                    body = full_body
                elif self.path == "/api/recordings":
                    body = b"[]"
                else:
                    value = web.get(self.path)
                    if value is None:
                        self.send_error(404)
                        return
                    body = json.dumps(value).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (ConnectionError, OSError):
                    pass  # A bounded reader intentionally closes the oversize response.

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            base = "http://127.0.0.1:" + str(server.server_port)
            for command in ("activate", "inspect", "plan", "apply"):
                message = "$vibelens" if command == "activate" else "/vibelens show approval"
                with self.subTest(command=command), redirect_stdout(io.StringIO()) as output:
                    code = control_main(
                        [
                            command,
                            "--root",
                            str(self.root),
                            "--url",
                            base,
                            "--message",
                            message,
                            "--spec",
                            str(spec),
                        ]
                    )
                    self.assertEqual(code, 0, output.getvalue())
            self.assertNotIn("/api/view", requests)
            self.assertEqual(requests.count("/api/vibelens/control/context"), 4)
            context = control_get(base, "/api/vibelens/control/context")
            self.assertNotIn("runtime_frames", context)
            self.assertNotIn("events", context)
            self.assertEqual(context["model"], live["model"])
            self.assertEqual(context["manifest"], live["manifest"])
            with self.assertRaisesRegex(ValueError, "inspection budget"):
                control_get(base, "/oversize")
            self.assertEqual(
                live["runtime_frames"]["transport_test_payload"], "x" * (9 * 1024 * 1024)
            )
        finally:
            server.shutdown()
            server.server_close()
            worker.join(3)


if __name__ == "__main__":
    unittest.main()
