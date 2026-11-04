"""Source discovery skips generated trees but still inspects ordinary exclusions."""

import os
import ast
import json
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.workflow.bo_sync import source_inventory


class SourceInventoryWalkTests(unittest.TestCase):
    def test_generated_directories_are_pruned_before_descending(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            (root / "worker.py").write_text("def run():\n    return 1\n", encoding="utf-8")
            blocked = {root / name for name in ("node_modules", ".stategraph", ".validation")}
            for directory in blocked:
                directory.mkdir()
                (directory / "hidden.py").write_text("def ignored(): pass\n", encoding="utf-8")
            scanned = []
            original = os.scandir

            def inspect(directory):
                path = Path(directory)
                scanned.append(path)
                if path in blocked:
                    raise AssertionError("Generated tree was traversed: " + str(path))
                return original(directory)

            with patch("os.scandir", side_effect=inspect):
                result = source_inventory(root, {"source_scope": {"roots": ["."]}})
            self.assertEqual(list(result["files"]), ["worker.py"])
            self.assertTrue(scanned)
            self.assertFalse(set(scanned) & blocked)

    def test_ordinary_exclusion_cannot_hide_application_or_route(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            directory = root / "private"
            directory.mkdir()
            (directory / "service.py").write_text(
                "@app.get('/hidden')\ndef hidden():\n    return 1\n", encoding="utf-8"
            )
            result = source_inventory(
                root,
                {
                    "source_scope": {
                        "roots": ["."],
                        "exclude": {"private/**": "Reviewed excluded directory"},
                    }
                },
            )
            self.assertEqual(result["files"], {})
            self.assertEqual(result["excluded_implementations"], ["private/service.py"])
            self.assertIn("private/service.py", result["excluded_entrypoints"])

    def test_cached_inspection_keeps_errors_and_rereads_same_stat_source(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            (root / "private").mkdir()
            path = root / "private/service.py"
            body = b"@app.get('/hidden')\ndef hidden():\n    return 1\n"
            path.write_bytes(body)
            stamp = path.stat()
            cfg = {"source_scope": {"roots": ["."], "exclude": {"private/**": "Review"}}}
            cache = {}
            first = source_inventory(root, cfg, inspection_cache=cache)
            with patch.object(
                ast, "parse", side_effect=AssertionError("Unchanged source reparsed")
            ):
                second = source_inventory(root, cfg, inspection_cache=cache)
            self.assertEqual(first, second)
            self.assertIn("private/service.py", second["excluded_entrypoints"])
            path.write_bytes(body.replace(b"/hidden", b"/toggle"))
            os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            third = source_inventory(root, cfg, inspection_cache=cache)
            self.assertNotEqual(first["excluded_entrypoints"], third["excluded_entrypoints"])
            self.assertEqual(third["excluded_implementations"], ["private/service.py"])


class SharedSourceScopeTests(unittest.TestCase):
    """Classified storage is pruned; project-owned code stays independently visible."""

    def setUp(self):
        (ROOT / ".validation").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        target = self.root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def configuration(self, *, roots=None):
        return {
            "source_scope": {
                "roots": roots or ["."],
                "prune": [
                    {"path": "installed", "category": "dependency", "reason": "Installed packages"},
                    {"path": "artifacts", "category": "artifact", "reason": "Captured outputs"},
                ],
            }
        }

    def project(self, config=None):
        sys.path.insert(0, str(ROOT / "tools"))
        from test_multilanguage import project_fixture

        project = project_fixture(self.root)
        self.write(
            "worker.py",
            'def advance(state, event, slots):\n    """Advance a task from its current capacity."""\n    return state\n',
        )
        self.write("sync.json", json.dumps(config or self.configuration()))
        return project

    def test_classified_wide_storage_is_pruned_before_read_or_ast(self):
        """A bounded stand-in for a 34k-directory recording tree is never entered."""
        self.write("src/app.py", 'def execute():\n    """Run the application."""\n    return 1\n')
        blocked = {self.root / "installed", self.root / "artifacts"}
        for directory in blocked:
            directory.mkdir()
            for ordinal in range(64):
                (directory / ("record-" + str(ordinal))).mkdir()
            (directory / "invalid.py").write_text("this is not valid Python !!!", encoding="utf-8")
        scanned = []
        original = os.scandir

        def inspect(directory):
            current = Path(directory)
            scanned.append(current)
            if any(current == path or current.is_relative_to(path) for path in blocked):
                raise AssertionError("Would descend the simulated 34,473-artifact tree")
            return original(directory)

        with (
            patch("os.scandir", side_effect=inspect),
            patch.object(
                ast, "parse", side_effect=AssertionError("Pruned storage was sent to AST")
            ),
        ):
            inventory = source_inventory(self.root, self.configuration())
        self.assertEqual(set(inventory["files"]), {"src/app.py"})
        self.assertFalse(set(scanned) & blocked)
        self.assertEqual({item["path"] for item in inventory["pruned"]}, {"installed", "artifacts"})
        self.assertFalse(inventory["excluded_entrypoints"])

    def test_supported_owned_languages_and_new_top_level_modules_remain_discovered(self):
        sources = {
            "src/service.py": "def save(): return 1\n",
            "api/route.js": "export const read = () => 1;\n",
            "frontend/model.ts": "export const value: number = 1;\n",
            "frontend/Panel.tsx": "export const Panel = () => <button/>;\n",
            "frontend/Panel.vue": "<script setup>const value = 1;</script><template>{{value}}</template>\n",
            "models/files.py": "class File: pass\n",
            "migrations/first.py": "def upgrade(): return None\n",
        }
        for name, body in sources.items():
            self.write(name, body)
        first = source_inventory(self.root, self.configuration())
        self.assertEqual(set(first["files"]), set(sources))
        self.write("new_feature/handler.py", "def added(): return 2\n")
        second = source_inventory(self.root, self.configuration())
        self.assertEqual(set(second["files"]) - set(first["files"]), {"new_feature/handler.py"})

    def test_gitignore_is_versioned_advice_without_hiding_owned_code(self):
        self.write("src/app.py", "def execute(): return 1\n")
        self.write(".gitignore", "src/\n*.py\n")
        first = source_inventory(self.root, self.configuration())
        self.assertIn("src/app.py", first["files"])
        self.assertTrue(first["scope_inputs"][".gitignore"])
        self.write(".gitignore", "src/\n*.py\nnew_feature/\n")
        second = source_inventory(self.root, self.configuration())
        self.assertNotEqual(first["scope_inputs"], second["scope_inputs"])
        self.assertEqual(first["files"], second["files"])

    def test_exact_owned_override_restores_only_its_declared_subtree(self):
        self.write("installed/local/handler.py", "def owned(): return 1\n")
        self.write("installed/package/foreign.py", "def foreign(): return 2\n")
        inventory = source_inventory(self.root, self.configuration(roots=[".", "installed/local"]))
        self.assertEqual(set(inventory["files"]), {"installed/local/handler.py"})
        self.assertNotIn("installed/package/foreign.py", inventory["files"])

    def test_unclassified_soft_exclusion_still_detects_hidden_business_route(self):
        self.write("src/hidden.py", "@app.get('/hidden')\ndef hidden(): return 1\n")
        config = self.configuration()
        config["source_scope"]["exclude"] = {"src/**": "Previously reviewed source"}
        inventory = source_inventory(self.root, config)
        self.assertIn("src/hidden.py", inventory["excluded_entrypoints"])
        self.assertIn("src/hidden.py", inventory["excluded_implementations"])

    def test_project_api_and_documentation_share_the_same_classified_scope(self):
        from bo_observer.code_graph.service import CodeGraph
        from bo_observer.graph.source_documentation import report
        from bo_observer.sources import scan

        project = self.project()
        self.write(
            "api.py",
            'from flask import Flask\napp = Flask(__name__)\n@app.get("/files")\ndef read():\n    """Read project files."""\n    return []\n',
        )
        self.write(
            "artifacts/server.py",
            'from flask import Flask\napp = Flask(__name__)\n@app.get("/foreign")\ndef hidden(): return []\n',
        )
        self.write("installed/pkg.py", "def undocumented(): return 1\n")
        service = CodeGraph(self.root, persist=False)
        graph, model = service.refresh()
        self.assertFalse(graph["errors"])
        self.assertEqual(
            [node["api"]["path"] for node in graph["nodes"] if node.get("code_role") == "endpoint"],
            ["/files"],
        )
        paths = {node.get("project_path") for node in service.view(projection="project")["nodes"]}
        self.assertIn("api.py", paths)
        self.assertNotIn("artifacts/server.py", paths)
        self.assertNotIn("installed/pkg.py", paths)
        inventory = source_inventory(self.root, self.configuration())
        checked = report(scan(self.root, inventory["files"]), model)
        self.assertTrue(checked["valid"], checked)
        self.assertIn("api.py::read", checked["checked_symbols"])
        self.assertFalse(any("artifacts/" in name for name in checked["checked_symbols"]))
        self.assertEqual(project["project_id"], "fixture")

    def test_explicit_code_or_node_anchors_cannot_reclassify_pruned_storage_as_source(self):
        from bo_observer.code_graph.service import CodeGraph

        for role in ("code_files", "source", "represents", "feature"):
            with self.subTest(role=role):
                config = self.configuration()
                project = self.project(config)
                self.write(
                    "artifacts/hidden.py",
                    'def hidden(value):\n    """Read a recorded value."""\n    return value\n',
                )
                source = {"path": "artifacts/hidden.py", "symbol": "hidden"}
                if role == "code_files":
                    config["code_files"] = ["worker.py", source["path"]]
                elif role == "source":
                    project["model"]["nodes"][0]["source"] = source
                elif role == "represents":
                    project["model"]["nodes"].append(
                        {
                            "id": "recorded-value",
                            "kind": "data",
                            "label": "Value",
                            "summary": "Observed value",
                            "represents": {**source, "parameter": "value"},
                        }
                    )
                else:
                    project["model"]["implementation"] = {
                        "schema": "bo-implementation/v1",
                        "features": [
                            {
                                "id": "hidden",
                                "nodes": ["advance"],
                                "sources": [source["path"] + "::hidden"],
                                "requirements": ["R1"],
                                "parameters": [],
                                "cases": [],
                            }
                        ],
                        "support": {},
                        "excluded": {},
                    }
                project["model"]["source_files"].append(source["path"])
                self.write("sync.json", json.dumps(config))
                self.write("bo_stategraph/project.json", json.dumps(project))
                with self.assertRaisesRegex(ValueError, "source scope"):
                    CodeGraph(self.root, persist=False).refresh()

    def test_hashed_config_and_review_inputs_are_not_executable_anchors(self):
        from bo_observer.graph.behavior_model import capture

        project = self.project()
        self.write("artifacts/readme.json", '{"case":"previous evidence"}')
        project["model"]["source_files"].append("artifacts/readme.json")
        manifest = capture(self.root, project["model"])
        self.assertIn("artifacts/readme.json", manifest["files"])

    def test_invalid_paths_categories_and_reasons_are_rejected(self):
        from bo_observer.source_scope import compile_scope

        invalid = [
            {"path": ".", "category": "artifact", "reason": "Review"},
            {"path": "../escape", "category": "artifact", "reason": "Review"},
            {"path": str(self.root / "absolute"), "category": "artifact", "reason": "Review"},
            {"path": "artifacts/**", "category": "artifact", "reason": "Review"},
            {"path": "artifacts", "category": "other", "reason": "Review"},
            {"path": "artifacts", "category": "artifact", "reason": ""},
            {"path": "artifacts", "category": "artifact"},
            {"category": "artifact", "reason": "Review"},
            {"path": "artifacts", "category": "artifact", "reason": 1},
        ]
        for entry in invalid:
            with self.subTest(entry=entry), self.assertRaisesRegex(ValueError, "source scope"):
                compile_scope(self.root, {"source_scope": {"roots": ["."], "prune": [entry]}})
        with self.assertRaisesRegex(ValueError, "source scope"):
            source_inventory(self.root, {"source_scope": {"roots": ["missing-firstparty"]}})

    def test_explicit_binding_outside_declared_source_roots_is_rejected(self):
        from bo_observer.source_scope import compile_scope

        self.write("src/owned.py", "def execute(): return 1\n")
        self.write("outside.py", "def hidden(): return 2\n")
        policy = compile_scope(self.root, self.configuration(roots=["src"]))
        policy.assert_source("src/owned.py", "node.source")
        with self.assertRaisesRegex(ValueError, "source scope"):
            policy.assert_source("outside.py", "node.source")

    def test_default_dependency_and_review_runtime_boundaries_keep_local_modules(self):
        for name in (
            "node_modules/package/index.js",
            ".venv/pkg/installed.py",
            "review/runtime/old.py",
        ):
            self.write(name, "invalid generated content !!!\n")
        owned = {"runtime/engine.py", "data/models.py", "review/source_helper.py"}
        for name in owned:
            self.write(name, "def owned(): return 1\n")
        inventory = source_inventory(self.root, {"source_scope": {"roots": ["."]}})
        self.assertEqual(set(inventory["files"]), owned)
        self.assertEqual(
            {item["path"] for item in inventory["pruned"]},
            {"node_modules", ".venv", "review/runtime"},
        )

    def test_direct_scan_cannot_bypass_pruned_source_scope(self):
        from bo_observer.sources import scan

        self.project()
        self.write("artifacts/old.py", "def old(): return 1\n")
        with self.assertRaisesRegex(ValueError, "source scope"):
            scan(self.root, ["artifacts/old.py"])
        self.assertIn("worker.py::advance", scan(self.root, ["worker.py"])["symbols"])

    def test_capture_rejects_pruned_physical_and_parameter_anchors(self):
        from bo_observer.graph.behavior_model import capture

        for role in ("source", "represents"):
            with self.subTest(role=role):
                project = self.project()
                self.write("artifacts/old.py", "def old(value): return value\n")
                source = {"path": "artifacts/old.py", "symbol": "old"}
                project["model"]["source_files"].append(source["path"])
                if role == "source":
                    project["model"]["nodes"][0]["source"] = source
                else:
                    project["model"]["nodes"].append(
                        {
                            "id": "recorded-value",
                            "kind": "data",
                            "label": "Value",
                            "summary": "Recorded value",
                            "represents": {**source, "parameter": "value"},
                        }
                    )
                with self.assertRaisesRegex(ValueError, "source scope"):
                    capture(self.root, project["model"])

    def test_hash_only_python_artifacts_keep_integrity_without_ast_parsing(self):
        from bo_observer.graph.behavior_model import capture

        project = self.project()
        self.write("artifacts/old.py", "incomplete historical source !!!\n")
        project["model"]["source_files"].append("artifacts/old.py")
        before = capture(self.root, project["model"])
        self.assertIn("artifacts/old.py", before["files"])
        self.write("artifacts/old.py", "changed historical source !!!\n")
        after = capture(self.root, project["model"])
        self.assertNotEqual(before["files"]["artifacts/old.py"], after["files"]["artifacts/old.py"])
        self.assertEqual(before["bindings"]["advance"], after["bindings"]["advance"])

    def test_all_executable_reference_kinds_use_the_same_policy(self):
        from bo_observer.source_scope import compile_scope, validate_executable_sources

        self.write("artifacts/old.py", "def old(value): return value\n")
        policy = compile_scope(self.root, self.configuration())
        reference = {"path": "artifacts/old.py", "symbol": "old"}
        models = [
            {
                "implementation": {
                    "features": [
                        {"parameters": [{"source": "artifacts/old.py::old", "name": "value"}]}
                    ]
                }
            },
            {"policy": {"predicates": [{"id": "allowed", "source": reference}]}},
            {"implementation": {"support": {"artifacts/old.py::old": {"node": "advance"}}}},
        ]
        for model in models:
            with self.subTest(model=model), self.assertRaisesRegex(ValueError, "source scope"):
                validate_executable_sources(policy, model=model)
        with self.assertRaisesRegex(ValueError, "source scope"):
            validate_executable_sources(
                policy, telemetry={"registrations": [{"source": reference}]}
            )

    def test_gitignore_change_invalidates_snapshot_and_maintenance_without_source_edits(self):
        from bo_observer.workflow.bo_sync import maintenance_task
        from bo_observer.workflow.sync_config import snapshot

        config = self.configuration()
        config.update(
            {
                "config_path": "sync.json",
                "model": "bo_stategraph/project.json",
                "manifest": "manifest.json",
                "acceptance": "acceptance.json",
                "code_files": ["worker.py"],
                "watch_files": [],
            }
        )
        self.project(config)
        self.write("acceptance.json", '{"cases": []}')
        self.write(".gitignore", "artifacts/\n")
        before_inventory = source_inventory(self.root, config)
        with patch(
            "bo_observer.workflow.sync_config.tool_fingerprints", return_value={"fixture": "1"}
        ):
            before = snapshot(self.root, config)
            self.write(".gitignore", "artifacts/\nnew-output/\n")
            after = snapshot(self.root, config)
        self.assertEqual(before_inventory["files"], after["source_inventory"]["files"])
        self.assertNotEqual(
            before["id"], after["id"], "scope inputs must affect candidate identity"
        )
        task = maintenance_task(self.root, config, before_inventory)
        self.assertTrue(task["scope_changed"])
        self.assertEqual(task["status"], "needs_update")

    def test_artifact_presence_changes_diagnostics_not_semantic_revisions(self):
        from copy import deepcopy
        from bo_observer.code_graph.service import CodeGraph
        from bo_observer.workflow.sync_config import snapshot

        config = self.configuration()
        config.update(
            {
                "config_path": "sync.json",
                "model": "bo_stategraph/project.json",
                "manifest": "manifest.json",
                "acceptance": "acceptance.json",
                "code_files": ["worker.py", "api.py"],
                "watch_files": [],
            }
        )
        self.project(config)
        self.write(
            "api.py",
            'from flask import Flask\napp = Flask(__name__)\n@app.get("/files")\ndef read():\n    """Read files."""\n    return []\n',
        )
        self.write("acceptance.json", '{"cases": []}')
        service = CodeGraph(self.root, persist=False)
        before, _ = service.refresh()
        frozen = deepcopy(before)
        api_before = service.api_snapshot()
        inventory_before = source_inventory(self.root, config)
        with patch(
            "bo_observer.workflow.sync_config.tool_fingerprints", return_value={"fixture": "1"}
        ):
            snapshot_before = snapshot(self.root, config)
            self.write("artifacts/new-record/old.py", "invalid recorded code !!!\n")
            self.write(".stategraph/transient.json", '{"observer":"cache"}')
            after, _ = service.refresh()
            snapshot_after = snapshot(self.root, config)
        inventory_after = source_inventory(self.root, config)
        self.assertEqual(before, frozen, "fresh diagnostic reports cannot mutate an old graph")
        self.assertNotEqual(inventory_before["pruned"], inventory_after["pruned"])
        self.assertEqual(before["revision"], after["revision"])
        self.assertEqual(api_before["revision"], service.api_snapshot()["revision"])
        self.assertEqual(snapshot_before["id"], snapshot_after["id"])

    def test_owned_root_cannot_follow_a_link_into_classified_storage(self):
        from bo_observer.source_scope import compile_scope

        self.write("artifacts/old.py", "def old(): return 1\n")
        link, target = self.root / "owned-link", self.root / "artifacts"
        if os.name == "nt":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)],
                check=True,
                capture_output=True,
            )
        else:
            link.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "source scope"):
            compile_scope(self.root, self.configuration(roots=[".", "owned-link"]))
        self.assertEqual((target / "old.py").read_text(encoding="utf-8"), "def old(): return 1\n")


if __name__ == "__main__":
    unittest.main()
