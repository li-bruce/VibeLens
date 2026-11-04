"""Concept selections use actual observation owners and preserve recorded IDs."""

from copy import deepcopy
from contextlib import redirect_stdout
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))

from bo_observer.concepts import bind_projection  # noqa: E402
from bo_observer.concepts.common import canonical_id  # noqa: E402
from bo_observer.control.selection import build_plan, validate_evidence  # noqa: E402
from bo_observer.control.cli import main as control_main, get as control_get  # noqa: E402
from bo_observer.graph.observation_scope import (  # noqa: E402
    capture_owners,
    concept_targets,
    display_graph,
)
from bo_observer.observation.recording_session import Recordings  # noqa: E402
from bo_observer.observation.session import GraphSession  # noqa: E402
from bo_observer.web.bo_web import BOWeb  # noqa: E402
from test_concept_models import bound_fixture  # noqa: E402


def bound_view():
    """Use the real binding validator, with conceptual and native IDs distinct."""
    document, model, acceptance = bound_fixture()
    model.update(revision="r1", project_id="sharing")
    return {
        "model": model,
        "concept_structure": bind_projection(document, model, acceptance=acceptance),
        "manifest": {"build_id": "build-1"},
        "machine": {},
        "authority": {"parameters": {}},
        "health": {"run_id": "run-1", "attempted": 0},
        "events": [],
        "binding_status": {"status": "current"},
        "historical": False,
    }


class ConceptCaptureTests(unittest.TestCase):
    def test_http_inspect_plan_apply_retains_session_concepts_without_runtime_history(self):
        """Traverse CLI -> HTTP -> BOWeb -> GraphSession context and back again.

        The already validated projection is the fixture; this test exercises
        transport and identity selection, not application source admission.
        """
        view = bound_view()
        (ROOT / ".validation").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as directory:
            root = Path(directory)
            (root / "bo_stategraph").mkdir()
            (root / "bo_stategraph/project.json").write_text(
                json.dumps({"project_id": "sharing"}), encoding="utf-8"
            )
            spec = root / "request.json"
            spec.write_text(
                json.dumps({"action": "view", "label": "Share", "anchors": ["share"], "depth": 0}),
                encoding="utf-8",
            )
            web = BOWeb(root)
            # Use the actual session/control methods; source scans and event
            # history are outside this transport fixture's responsibility.
            session = GraphSession.__new__(GraphSession)
            session.lock = threading.RLock()
            session.model, session.manifest = view["model"], view["manifest"]
            session.project = {"project_id": "sharing"}
            session.bo_concept_context = SimpleNamespace(
                view=lambda: deepcopy(view["concept_structure"])
            )
            web.code_graph = SimpleNamespace(view=lambda **kwargs: {"nodes": [], "edges": []})
            web.bo_api_graph = SimpleNamespace(api_snapshot=lambda: {"nodes": [], "edges": []})
            session.web = web
            web.control_view = session.view
            requests = []

            class Handler(BaseHTTPRequestHandler):
                def log_message(self, *_):
                    pass

                def do_GET(self):
                    requests.append(self.path)
                    value = [] if self.path == "/api/recordings" else web.get(self.path)
                    if value is None:
                        self.send_error(404)
                        return
                    body = json.dumps(value).encode()
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)

            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                base = "http://127.0.0.1:" + str(server.server_port)
                with patch.dict("os.environ", {"CODEX_THREAD_ID": "concept-capture-chat"}):
                    results = {}
                    for command in ("activate", "inspect", "plan", "apply"):
                        message = "$vibelens" if command == "activate" else "/vibelens show share"
                        with redirect_stdout(io.StringIO()) as output:
                            status = control_main(
                                [
                                    command,
                                    "--root",
                                    str(root),
                                    "--url",
                                    base,
                                    "--message",
                                    message,
                                    "--spec",
                                    str(spec),
                                ]
                            )
                        self.assertEqual(status, 0, output.getvalue())
                        results[command] = json.loads(output.getvalue())["result"]
                    self.assertIn("share", {node["id"] for node in results["inspect"]["nodes"]})
                    self.assertEqual(results["plan"]["node_ids"], ["share"])
                    active = results["activate"]["session"]
                    queued = control_get(base, "/api/vibelens/control?vl_session=" + active)
                    self.assertEqual(queued["plan"]["node_ids"], ["share"])
                    context = control_get(base, "/api/vibelens/control/context")
                    self.assertEqual(context["concept_structure"], view["concept_structure"])
                    self.assertNotIn("events", context)
                    self.assertNotIn("runtime_frames", context)
                    self.assertNotIn("/api/view", requests)
            finally:
                server.shutdown()
                server.server_close()
                worker.join(3)

    def test_conversation_selection_keeps_concepts_and_verifies_full_inventory(self):
        view = bound_view()
        before = deepcopy(view)
        plan = build_plan(
            view, {"action": "view", "label": "Share", "anchors": ["share"], "depth": 0}
        )
        self.assertEqual(plan["node_ids"], ["share"])
        validate_evidence(plan, view)
        self.assertEqual(view, before)
        view["concept_structure"]["nodes"][0]["label"] = "Changed meaning shown"
        with self.assertRaisesRegex(ValueError, "graph changed"):
            validate_evidence(plan, view)

    def test_replay_matches_native_events_without_rewriting_them(self):
        view = bound_view()
        recording = {
            "id": "recording-1",
            "status": "stopped",
            "build_id": "build-1",
            "context": {"model": view["model"]},
            "events": [
                {
                    "id": "event-1",
                    "node": "native:share",
                    "build_id": "build-1",
                    "model_revision": "r1",
                    "call_id": "call-1",
                },
                {
                    "id": "event-2",
                    "node": "native:read",
                    "build_id": "build-1",
                    "model_revision": "r1",
                },
            ],
        }
        original = deepcopy(recording)
        plan = build_plan(
            view,
            {"action": "replay", "label": "Share", "anchors": ["share"], "depth": 0},
            recording,
        )
        self.assertEqual(plan["recording"]["event_ids"], ["event-1"])
        self.assertEqual(plan["node_ids"], ["share"])
        validate_evidence(plan, view, recording)
        self.assertEqual(recording, original)

    def test_focused_recording_uses_native_scope_and_preserves_context(self):
        view = bound_view()
        scopes = []
        (ROOT / ".validation").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as directory:
            recorder = Recordings(
                directory,
                lambda: deepcopy(view),
                {},
                interval=60,
                scope_setter=lambda nodes: scopes.append(nodes),
            )
            try:
                recording_id = recorder.start(scope={"mode": "focused", "roots": ["share"]})["id"]
                self.assertEqual(scopes[0], ["native:share"])
                event = {
                    "id": "event-1",
                    "seq": 1,
                    "run_id": "run-1",
                    "node": "native:share",
                    "inputs": {},
                    "outputs": {},
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                }
                view["events"].append(event)
                view["health"]["attempted"] = 1
                recorder.bo_event(event)
                recorder.stop()
                saved = recorder.get(recording_id)
                self.assertEqual(saved["capture"]["roots"], ["native:share"])
                self.assertEqual(saved["events"][0]["node"], "native:share")
                self.assertEqual(saved["context"]["concept_structure"], view["concept_structure"])
                self.assertIsNone(scopes[-1])
            finally:
                recorder.close()

    def test_conceptual_association_cannot_grant_capture_scope(self):
        view = bound_view()
        view["concept_structure"]["edges"] = [
            edge
            for edge in view["concept_structure"]["edges"]
            if edge.get("mapping_role") != "implements" or edge["from"] != "share"
        ]
        # A visually connected concept still has no registered observation owner.
        view["concept_structure"]["edges"].append(
            {"id": "fake-flow", "from": "share", "to": "native:read", "type": "flow"}
        )
        with self.assertRaisesRegex(ValueError, "no capture binding"):
            capture_owners(view, ["share"])
        self.assertEqual(capture_owners(view, ["share"], strict=False), [])
        self.assertEqual(capture_owners(view, ["native:read"]), ["native:read"])

    def test_unbound_projection_wrong_markers_and_unknown_targets_are_rejected(self):
        original = bound_view()
        for mutation in [
            lambda view, edge: view["concept_structure"].update(stage="design"),
            lambda view, edge: edge.update(observed=True),
            lambda view, edge: edge.update(origin="concept-crosslink"),
            lambda view, edge: edge.update(id="ordinary-visual-map"),
        ]:
            view = deepcopy(original)
            edge = next(
                edge
                for edge in view["concept_structure"]["edges"]
                if edge.get("mapping_role") == "implements" and edge["from"] == "share"
            )
            mutation(view, edge)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                capture_owners(view, ["share"])

    def test_multiple_owners_stay_separate_and_do_not_merge_lifecycles(self):
        view = bound_view()
        edge = next(
            edge
            for edge in view["concept_structure"]["edges"]
            if edge.get("mapping_role") == "implements" and edge["from"] == "share"
        )
        view["concept_structure"]["edges"].append(
            {
                **edge,
                "id": canonical_id("concept-implements", "share", "native:read"),
                "to": "native:read",
            }
        )
        self.assertEqual(capture_owners(view, ["share"]), ["native:read", "native:share"])
        self.assertEqual(view["events"], [])

    def test_native_nodes_and_self_maps_do_not_become_concept_bindings(self):
        view = bound_view()
        edge = next(
            edge
            for edge in view["concept_structure"]["edges"]
            if edge.get("mapping_role") == "implements" and edge["from"] == "share"
        )
        for target in ("native:share", "native:read"):
            view["concept_structure"]["edges"].append(
                {
                    **edge,
                    "from": "native:share",
                    "to": target,
                    "id": canonical_id("concept-implements", "native:share", target),
                }
            )
        self.assertNotIn("native:share", concept_targets(view))
        self.assertEqual(capture_owners(view, ["native:share"]), ["native:share"])
        node = next(node for node in view["concept_structure"]["nodes"] if node["id"] == "share")
        node["origin"] = "source-ast"
        with self.assertRaisesRegex(ValueError, "no capture binding"):
            capture_owners(view, ["share"])

    def test_exact_source_map_resolves_code_but_not_arbitrary_dependencies(self):
        view = bound_view()
        owner = next(node for node in view["model"]["nodes"] if node["id"] == "native:share")
        view["code_structure"] = {
            "nodes": [{"id": "code:share", "code_role": "function", "source": owner["source"]}],
            "edges": [
                {
                    "id": "maps-share",
                    "from": "native:share",
                    "to": "code:share",
                    "type": "maps",
                    "code_relation": "maps",
                }
            ],
        }
        self.assertEqual(capture_owners(view, ["code:share"]), ["native:share"])
        view["code_structure"]["nodes"][0]["source"] = {"path": "other.py", "symbol": "share"}
        with self.assertRaises(ValueError):
            capture_owners(view, ["code:share"])

    def test_display_inventory_includes_project_and_api_without_mutating_model(self):
        view = bound_view()
        view["project_structure"] = {
            "nodes": [{"id": "file:sharing", "code_role": "file"}],
            "edges": [],
        }
        view["api_structure"] = {
            "nodes": [{"id": "api:share", "code_role": "endpoint"}],
            "edges": [],
        }
        native = deepcopy(view["model"])
        identities = {node["id"] for node in display_graph(view)["nodes"]}
        self.assertTrue({"share", "file:sharing", "api:share", "native:share"} <= identities)
        self.assertEqual(view["model"], native)


if __name__ == "__main__":
    unittest.main()
