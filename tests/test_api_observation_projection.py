"""Only exact registered HTTP sources may supply endpoint observation facts."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from bo_observer.code_graph.service import CodeGraph
from test_multilanguage import project_fixture


class APIObservationProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.temp.name)
        self.project = project_fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def configure(self, source, registrations):
        (self.root / "api.py").write_text(source, encoding="utf-8")
        model = self.project["model"]
        model["source_files"] += ["api.py", "bo_stategraph/telemetry.json"]
        known = set()
        for item in registrations:
            if item["node"] in known:
                continue
            known.add(item["node"])
            model["nodes"].append(
                {
                    "id": item["node"],
                    "kind": "function",
                    "layer": "api",
                    "label": item["node"],
                    "summary": "Observe the native HTTP request and response.",
                    "source": item["source"],
                    "capture": {"in": {"path": "string"}, "out": {"status": "number"}},
                }
            )
        for item in registrations:
            item["capture"] = {"in": {"path": "http.target"}, "out": {"status": "http.status_code"}}
        configuration = {
            "protocol": "bo-telemetry/v1",
            "backend": "opentelemetry",
            "registrations": registrations,
        }
        (self.root / "bo_stategraph/telemetry.json").write_text(
            json.dumps(configuration), encoding="utf-8"
        )
        (self.root / "bo_stategraph/project.json").write_text(
            json.dumps(self.project), encoding="utf-8"
        )
        return CodeGraph(self.root, persist=False)

    def registration(self, node, name, symbol="files", **extra):
        return {
            "node": node,
            "source": {"path": "api.py", "symbol": symbol},
            "match": {"name": name, **extra},
        }

    def endpoints(self, graph):
        return {
            node["api"]["path"]: node
            for node in graph["nodes"]
            if node.get("code_role") == "endpoint"
        }

    def test_combined_route_observes_both_methods_without_replacing_native_ids(self):
        service = self.configure(
            "from flask import Flask\napp=Flask(__name__)\n@app.route('/api/<path:operation>',methods=['GET','POST'])\ndef files(operation):\n    return operation\n",
            [
                self.registration("api_get", "GET /api/<path:operation>"),
                self.registration("api_post", "POST /api/<path:operation>"),
            ],
        )
        graph, _ = service.refresh()
        endpoint = self.endpoints(graph)["/api/<path:operation>"]
        self.assertTrue(endpoint["observation_projection"])
        self.assertEqual(
            {row["node"] for row in endpoint["observation_sources"]}, {"api_get", "api_post"}
        )
        self.assertEqual(
            {row["method"] for row in endpoint["observation_sources"]}, {"GET", "POST"}
        )
        self.assertEqual(graph["observation_issues"], [])
        native = deepcopy(self.project["model"]["nodes"])
        snapshot = service.api_snapshot()
        self.assertEqual(len(snapshot["nodes"]), 1)
        self.assertEqual({edge["from"] for edge in snapshot["edges"]}, {"api_get", "api_post"})
        self.assertTrue(
            all(edge["mapping_role"] == "http-observation" for edge in snapshot["edges"])
        )
        self.assertEqual(self.project["model"]["nodes"], native)
        self.assertFalse(
            service.cache.exists(), "Mandatory API snapshots must respect persist=False"
        )
        self.assertEqual(snapshot["nodes"][0]["id"], endpoint["id"])

    def test_same_handler_different_routes_do_not_share_observations(self):
        service = self.configure(
            "from flask import Flask\napp=Flask(__name__)\n@app.get('/files')\n@app.get('/archive')\ndef files(): return []\n",
            [
                self.registration("api_files", "GET /files"),
                self.registration("api_archive", "GET /archive"),
            ],
        )
        graph = service.view(projection="api")
        routes = self.endpoints(graph)
        self.assertEqual(
            [row["node"] for row in routes["/files"]["observation_sources"]], ["api_files"]
        )
        self.assertEqual(
            [row["node"] for row in routes["/archive"]["observation_sources"]], ["api_archive"]
        )

    def test_wrong_method_route_or_handler_never_becomes_an_observation(self):
        service = self.configure(
            "from flask import Flask\napp=Flask(__name__)\n@app.get('/files')\ndef files(): return []\ndef other(): return []\n",
            [
                self.registration("wrong_method", "POST /files"),
                self.registration("wrong_route", "GET /other"),
                self.registration("wrong_handler", "GET /files", "other"),
            ],
        )
        graph, _ = service.refresh()
        endpoint = self.endpoints(graph)["/files"]
        self.assertEqual(endpoint["observation_sources"], [])
        self.assertNotIn("observation_projection", endpoint)
        self.assertEqual(len(graph["observation_issues"]), 3)

    def test_attribute_selectors_require_consistent_literal_method_and_route(self):
        service = self.configure(
            "from flask import Flask\napp=Flask(__name__)\n@app.get('/files')\ndef files(): return []\n",
            [
                self.registration(
                    "exact",
                    "Read files",
                    attributes={"http.request.method": "GET", "http.route": "/files"},
                ),
                self.registration(
                    "wrong",
                    "POST /files",
                    attributes={"http.request.method": "GET", "http.route": "/files"},
                ),
                self.registration("unknown", "Read a request"),
            ],
        )
        graph, _ = service.refresh()
        self.assertEqual(
            [row["node"] for row in self.endpoints(graph)["/files"]["observation_sources"]],
            ["exact"],
        )
        self.assertEqual(
            {issue["reason"] for issue in graph["observation_issues"]},
            {"http_selector_not_route_qualified"},
        )

    def test_same_capture_reused_across_routes_is_not_qualified_by_node_id(self):
        service = self.configure(
            "from flask import Flask\napp=Flask(__name__)\n@app.get('/files')\n@app.get('/archive')\ndef files(): return []\n",
            [
                self.registration("shared", "GET /files"),
                self.registration("shared", "GET /archive"),
            ],
        )
        graph, _ = service.refresh()
        self.assertTrue(
            all(not endpoint["observation_sources"] for endpoint in self.endpoints(graph).values())
        )
        self.assertIn(
            "http_capture_reused_across_endpoints",
            {issue["reason"] for issue in graph["observation_issues"]},
        )

    def test_two_router_registrations_with_the_same_handler_are_ambiguous(self):
        service = self.configure(
            "from flask import Flask\nfirst=Flask('first')\nsecond=Flask('second')\ndef files(): return []\nfirst.add_url_rule('/files',view_func=files,methods=['GET'])\nsecond.add_url_rule('/files',view_func=files,methods=['GET'])\n",
            [self.registration("api_files", "GET /files")],
        )
        graph, _ = service.refresh()
        self.assertFalse(self.endpoints(graph)["/files"]["observation_sources"])
        self.assertEqual(graph["observation_issues"][0]["reason"], "http_endpoint_ambiguous")
        self.assertEqual(graph["observation_issues"][0]["registrations"], 2)

    def test_telemetry_and_model_changes_invalidate_projection_without_source_edits(self):
        service = self.configure(
            "from flask import Flask\napp=Flask(__name__)\n@app.get('/files')\ndef files(): return []\n",
            [self.registration("api_files", "GET /files")],
        )
        before = service.view(projection="api")
        path = self.root / "bo_stategraph/telemetry.json"
        configuration = json.loads(path.read_text())
        configuration["registrations"][0]["match"]["name"] = "POST /files"
        path.write_text(json.dumps(configuration), encoding="utf-8")
        after = service.view(projection="api")
        self.assertNotEqual(before["revision"], after["revision"])
        self.assertEqual(self.endpoints(after)["/files"]["observation_sources"], [])
        self.assertEqual(
            self.endpoints(before)["/files"]["id"], self.endpoints(after)["/files"]["id"]
        )

    def test_duplicate_native_node_on_one_combined_endpoint_is_safe(self):
        service = self.configure(
            "from flask import Flask\napp=Flask(__name__)\n@app.route('/files',methods=['GET','POST'])\ndef files(): return []\n",
            [
                self.registration("api_files", "GET /files"),
                self.registration("api_files", "POST /files"),
            ],
        )
        graph, _ = service.refresh()
        endpoint = self.endpoints(graph)["/files"]
        self.assertTrue(endpoint["observation_projection"])
        self.assertEqual({row["node"] for row in endpoint["observation_sources"]}, {"api_files"})
        self.assertEqual(len(endpoint["observation_sources"]), 2)

    def test_strict_check_catches_new_unregistered_route_and_cli_does_not_write_cache(self):
        service = self.configure(
            "from flask import Flask\napp=Flask(__name__)\n@app.get('/files')\n@app.get('/archive')\ndef files(): return []\n",
            [
                self.registration("api_files", "GET /files"),
                self.registration("api_archive", "GET /archive"),
            ],
        )
        path = self.root / "bo_stategraph/telemetry.json"
        complete = path.read_text(encoding="utf-8")
        configuration = json.loads(complete)
        configuration["registrations"].pop()
        path.write_text(json.dumps(configuration), encoding="utf-8")
        adopted = service.api_observation_check()
        self.assertTrue(adopted["valid"])
        self.assertEqual(adopted["coverage"], "incomplete")
        self.assertEqual(len(adopted["unobserved_routes"]), 1)
        self.assertFalse(service.api_observation_check(require_complete=True)["valid"])
        command = [
            sys.executable,
            "-B",
            str(ROOT / "skills/vibelens/scripts/bo_code.py"),
            "api-check",
            "--root",
            str(self.root),
            "--strict",
        ]
        failed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(failed.returncode, 1, failed.stderr)
        self.assertEqual(len(json.loads(failed.stdout)["missing_routes"]), 1)
        path.write_text(complete, encoding="utf-8")
        passed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertEqual(json.loads(passed.stdout)["coverage"], "complete")
        self.assertFalse(service.cache.exists())

    def test_configured_bad_selector_fails_even_when_optional_code_cache_is_disabled(self):
        service = self.configure(
            "from flask import Flask\napp=Flask(__name__)\n@app.get('/files')\ndef files(): return []\n",
            [self.registration("api_files", "POST /files")],
        )
        report = service.api_observation_check()
        self.assertFalse(report["valid"])
        self.assertEqual(report["coverage"], "incomplete")
        self.assertTrue(report["errors"])
        check = service.check()
        self.assertFalse(check["enabled"])
        self.assertFalse(check["valid"])
        self.assertFalse(check["api_observation"]["valid"])
        self.assertFalse(service.cache.exists())

    def test_unconfigured_route_stays_unobserved_with_explicit_incomplete_coverage(self):
        service = self.configure(
            "from flask import Flask\napp=Flask(__name__)\n@app.get('/files')\ndef files(): return []\n",
            [],
        )
        report = service.api_observation_check()
        self.assertFalse(report["configured"])
        self.assertTrue(report["valid"])
        self.assertEqual(report["status"], "not_configured")
        self.assertEqual(report["coverage"], "incomplete")
        self.assertEqual(len(report["unobserved_routes"]), 1)
        self.assertFalse(service.api_observation_check(require_complete=True)["valid"])

    def test_strict_project_without_http_routes_is_not_applicable(self):
        service = self.configure("def helper(): return None\n", [])
        report = service.api_observation_check(require_complete=True)
        self.assertTrue(report["valid"])
        self.assertEqual(report["status"], "not_applicable")
        self.assertEqual(report["coverage"], "not_applicable")

    def test_combined_endpoint_with_only_one_observed_method_is_incomplete(self):
        service = self.configure(
            "from flask import Flask\napp=Flask(__name__)\n@app.route('/files',methods=['GET','POST'])\ndef files(): return []\n",
            [self.registration("api_get", "GET /files")],
        )
        report = service.api_observation_check(require_complete=True)
        self.assertFalse(report["valid"])
        self.assertEqual(report["coverage"], "incomplete")
        self.assertEqual(report["incomplete_methods"][0]["methods"], ["POST"])
        self.assertEqual(len(report["missing_routes"]), 1)

    def test_imported_handler_and_middleware_share_exact_registration_proof(self):
        (self.root / "routes.mjs").write_text(
            "import express from 'express';\nimport {files} from './handlers.mjs';\nconst app=express();\nfunction authenticate(req,res,next) { next(); }\napp.get('/files',authenticate,files);\n",
            encoding="utf-8",
        )
        (self.root / "handlers.mjs").write_text(
            "export function files(req,res) { return res.json([]); }\n", encoding="utf-8"
        )
        self.project["model"]["source_files"] += ["routes.mjs", "handlers.mjs"]
        service = self.configure(
            "def unused(): return None\n",
            [
                {
                    "node": "api_files",
                    "source": {"path": "handlers.mjs", "symbol": "files"},
                    "match": {"name": "GET /files"},
                }
            ],
        )
        snapshot = service.api_snapshot()
        self.assertEqual(len(snapshot["nodes"]), 1)
        self.assertTrue(snapshot["nodes"][0]["observation_projection"])
        self.assertEqual(
            snapshot["nodes"][0]["observation_sources"][0]["source"]["path"], "handlers.mjs"
        )
        self.assertEqual(snapshot["observation_issues"], [])

    def test_partly_unqualified_reused_capture_id_cannot_safely_project_any_events(self):
        service = self.configure(
            "from flask import Flask\napp=Flask(__name__)\n@app.get('/files')\ndef files(): return []\n",
            [
                self.registration("api_files", "GET /files"),
                self.registration("api_files", "unrelated task"),
            ],
        )
        graph, _ = service.refresh()
        self.assertEqual(self.endpoints(graph)["/files"]["observation_sources"], [])
        self.assertFalse(service.api_observation_check()["valid"])


if __name__ == "__main__":
    unittest.main()
