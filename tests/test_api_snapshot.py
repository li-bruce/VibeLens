"""Keep exact API structure available in live views and frozen recordings."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from test_multilanguage import project_fixture
from bo_observer.observation.recording_session import checkpoint
from bo_observer.service import GraphSession
from bo_observer.workflow.sync_verify import verify


class ApiSnapshotTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".validation").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.temporary.name)
        self.project = project_fixture(self.root)
        (self.root / "routes.py").write_text(
            "from flask import Flask\napp = Flask(__name__)\n"
            '@app.get("/files")\ndef list_files():\n'
            '    """List files visible to the signed-in user."""\n'
            "    return []\n",
            encoding="utf-8",
        )
        self.project["model"]["source_files"].append("routes.py")
        (self.root / "bo_stategraph/project.json").write_text(
            json.dumps(self.project), encoding="utf-8"
        )
        self.session = GraphSession(self.root)

    def tearDown(self):
        self.session.close()
        self.temporary.cleanup()

    def test_live_view_includes_minimal_api_without_enabling_full_code_cache(self):
        view = self.session.view()
        api = view["api_structure"]
        self.assertEqual(api["errors"], [])
        self.assertEqual(len(api["nodes"]), 1)
        endpoint = api["nodes"][0]
        self.assertEqual(endpoint["code_role"], "endpoint")
        self.assertEqual(endpoint["api"]["path"], "/files")
        self.assertEqual(endpoint["api"]["methods"], ["GET"])
        # The native view adds default chart labels; API discovery must not
        # rewrite its business nodes, declared transitions or project file.
        self.assertEqual(view["model"]["nodes"], self.session.model["nodes"])
        self.assertEqual(
            view["model"]["machine"]["transitions"], self.project["model"]["machine"]["transitions"]
        )
        self.assertEqual(
            json.loads((self.root / "bo_stategraph/project.json").read_text(encoding="utf-8")),
            self.project,
        )
        self.assertEqual(self.session.sequence, 0)
        self.assertFalse((self.root / ".stategraph/code-graph.json").exists())
        self.assertEqual(self.session.view()["api_structure"]["nodes"], api["nodes"])

    def test_runtime_checkpoint_skips_source_scanning(self):
        with patch.object(
            self.session.web.bo_api_graph,
            "api_snapshot",
            side_effect=AssertionError("Runtime checkpoint rescanned API source"),
        ):
            self.assertIsNone(self.session.recording_view()["api_structure"])

    def test_context_freezes_api_projection_without_mutable_aliases(self):
        view = self.session.view()
        frozen = deepcopy(view["api_structure"])
        context = checkpoint(view, context=True)
        self.assertEqual(context["api_structure"], frozen)
        view["api_structure"]["nodes"].clear()
        self.assertEqual(context["api_structure"], frozen)
        self.assertNotIn("api_structure", checkpoint(view))

    def test_recording_keeps_initial_api_after_capture_scope_is_applied(self):
        # Applying producer scope causes an extra runtime-only read. The static
        # API projection must survive that boundary, just like project structure.
        self.session.recordings.bo_scope_setter = lambda scope: None
        method = self.session.web.bo_api_graph.api_snapshot
        with patch.object(self.session.web.bo_api_graph, "api_snapshot", wraps=method) as scan:
            self.session.recordings.start("API snapshot")
            self.assertEqual(scan.call_count, 1)
            context = deepcopy(self.session.recordings.active["context"])
            self.assertEqual(context["api_structure"]["nodes"][0]["api"]["path"], "/files")
            self.session.recordings.stop()
            self.assertEqual(scan.call_count, 1)
        self.assertFalse((self.root / ".stategraph/code-graph.json").exists())
        self.assertEqual(self.session.sequence, 0)

    def test_wrong_configured_api_fails_native_mapping_without_optional_cache(self):
        model = self.project["model"]
        model["source_files"].append("bo_stategraph/telemetry.json")
        model["nodes"].append(
            {
                "id": "http_files",
                "kind": "function",
                "layer": "api",
                "label": "Read files",
                "summary": "Observe the actual file-list request and response.",
                "source": {"path": "routes.py", "symbol": "list_files"},
                "capture": {"in": {"path": "string"}, "out": {"status": "number"}},
            }
        )
        telemetry = {
            "protocol": "bo-telemetry/v1",
            "backend": "opentelemetry",
            "registrations": [
                {
                    "node": "http_files",
                    "source": {"path": "routes.py", "symbol": "list_files"},
                    "match": {"name": "GET /missing"},
                    "capture": {
                        "in": {"path": "http.target"},
                        "out": {"status": "http.status_code"},
                    },
                }
            ],
        }
        (self.root / "bo_stategraph/project.json").write_text(
            json.dumps(self.project), encoding="utf-8"
        )
        (self.root / "bo_stategraph/telemetry.json").write_text(
            json.dumps(telemetry), encoding="utf-8"
        )
        change = self.root / ".stategraph/api-gate"
        change.mkdir(parents=True)
        # Isolate the API preflight: ordinary review is already accepted. No
        # observation command is supplied, so this must stop at the mapping gap.
        report = verify(
            self.root,
            {"model": "bo_stategraph/project.json"},
            change,
            inspect=lambda *args: ({}, {"id": "candidate"}, {"errors": [], "review_errors": []}),
            snapshot=lambda *args: None,
        )
        self.assertFalse(report["valid"])
        self.assertEqual(report["reports"]["mapping"]["status"], "failed")
        self.assertFalse(report["reports"]["mapping"]["api_observation"]["valid"])
        self.assertIn("http_endpoint_unresolved", json.dumps(report["errors"]))
        self.assertFalse((self.root / ".stategraph/code-graph.json").exists())


if __name__ == "__main__":
    unittest.main()
