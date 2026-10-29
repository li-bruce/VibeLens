"""Source-first engineering tree, dependency evidence and update regressions."""

import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from bo_observer.code_graph.service import CodeGraph
from bo_observer.code_graph.index import identity
from bo_observer.service import GraphSession, make_server
from test_multilanguage import project_fixture


def fixture(root):
    """Small actual Python/TS/Vue source tree, with a deliberate import cycle."""
    project = project_fixture(root)
    files = {
        "src/routes.py": "from .access import allow\ndef share(user):\n    return allow(user)\n",
        "src/access.py": "def allow(user):\n    from .store import load\n    return load(user)\n",
        "src/store.py": "from .routes import share\ndef load(user):\n    return user\n",
        "web/share.ts": "export function share(name: string) { return name; }\n",
        "web/main.ts": "import { share } from './share.js';\nexport * from './share.js';\nimport './main.css';\nexport function run() { return share('file'); }\n",
        "web/Panel.vue": "<script setup>\nimport { share } from './share.js';\nfunction click() { return share('file'); }\n</script>\n<template><button @click='click'>Share</button></template>\n",
        "web/main.css": "button { color: navy; }\n",
        "web/index.html": "<!doctype html><title>Files</title>\n",
        "README.md": "# Files\n",
        "package.json": json.dumps({"name": "files", "dependencies": {"file-ui": "workspace:*", "vue": "^3"}}),
        "packages/ui/package.json": json.dumps({"name": "file-ui"}),
        "pyproject.toml": '[project]\nname = "files-server"\ndependencies = ["SQLAlchemy>=2"]\n',
    }
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (root / "src/empty").mkdir()
    return project


class EngineeringStructureTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".validation").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.temp.name)
        self.project = fixture(self.root)
        self.service = CodeGraph(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def graph(self):
        graph, model = self.service.refresh()
        self.assertEqual(graph["errors"], [])
        return graph, model

    def test_tree_is_complete_and_symbols_remain_connected(self):
        graph, _ = self.graph()
        nodes = {n["id"]: n for n in graph["nodes"]}
        for name, fact in graph["project"]["entries"].items():
            role = "directory" if fact["kind"] == "directory" else "file"
            item = nodes[identity(role, name)]
            self.assertEqual(item["project_path"], name)
            if name != ".":
                self.assertIn(item["parent"], nodes)
                self.assertTrue(any(e["code_relation"] == "contains" and e["from"] == item["parent"]
                                    and e["to"] == item["id"] for e in graph["edges"]))
        self.assertIn(identity("directory", "src/empty"), nodes)
        self.assertIn(identity("file", "web/index.html"), nodes)
        self.assertEqual(nodes[graph["symbols"]["src/routes.py::share"]]["parent"], identity("file", "src/routes.py"))
        self.assertTrue(all(e["from"] in nodes and e["to"] in nodes for e in graph["edges"]))

    def test_import_reexport_and_resource_relations_have_actual_evidence(self):
        graph, _ = self.graph()
        for a, b, kind in [("src/access.py", "src/store.py", "imports"),
                           ("web/main.ts", "web/share.ts", "imports"),
                           ("web/main.ts", "web/share.ts", "exports"),
                           ("web/main.ts", "web/main.css", "imports"),
                           ("web/Panel.vue", "web/share.ts", "imports")]:
            edge = next(e for e in graph["edges"] if e["from"] == identity("file", a)
                        and e["to"] == identity("file", b) and e["code_relation"] == kind)
            self.assertEqual(edge["evidence"]["path"], a)
            self.assertIn("import" if kind == "imports" else "export",
                          (self.root / a).read_text().splitlines()[edge["evidence"]["line"] - 1])

    def test_manifest_dependencies_and_file_cycles_are_distinct(self):
        graph, _ = self.graph()
        self.assertTrue(any(e["from"] == identity("file", "package.json")
                            and e["to"] == identity("file", "packages/ui/package.json")
                            and e["code_relation"] == "dependency" for e in graph["edges"]))
        self.assertEqual(graph["project"]["file_cycles"], [sorted(identity("file", p)
            for p in ("src/routes.py", "src/access.py", "src/store.py"))])
        self.assertTrue(any(n.get("package_name") == "SQLAlchemy" for n in graph["nodes"]))

    def test_project_projection_excludes_functions_and_keeps_relations(self):
        graph = self.service.view(projection="project", limit=5000)
        self.assertTrue(graph["edges"])
        self.assertFalse(any(n["code_role"] in {"class", "function", "parameter", "endpoint"} for n in graph["nodes"]))
        self.assertTrue(any(e["code_relation"] == "imports" for e in graph["edges"]))
        self.assertEqual(self.service.view(projection="project", focus="advance")["focus"], "advance")
        with self.assertRaisesRegex(ValueError, "projection"):
            self.service.view(projection="invented")
        bounded = self.service.view(projection="project", limit=1)
        self.assertGreater(bounded["project"]["omitted_entries"], 0)
        self.assertLess(len(bounded["project"]["entries"]), graph["project"]["total_entries"])

    def test_edit_add_delete_empty_directory_and_config_invalidate_index(self):
        original, _ = self.graph()
        symbol = original["symbols"]["src/routes.py::share"]
        (self.root / "src/routes.py").write_text("\nfrom .access import allow\ndef share(user):\n    return allow(user)\n")
        (self.root / "src/new.py").write_text("def added(): return 1\n")
        (self.root / "src/empty").rmdir()
        (self.root / "web/main.css").unlink()
        changed, _ = self.graph()
        self.assertNotEqual(original["revision"], changed["revision"])
        self.assertEqual(changed["symbols"]["src/routes.py::share"], symbol)
        self.assertIn(identity("file", "src/new.py"), {n["id"] for n in changed["nodes"]})
        self.assertNotIn("src/empty", changed["project"]["entries"])
        self.assertNotIn("web/main.css", changed["project"]["entries"])
        (self.root / "package.json").write_text('{"dependencies":{"react":"19"}}')
        revised, _ = self.graph()
        self.assertNotEqual(changed["revision"], revised["revision"])
        self.assertFalse(any(n.get("package_name") == "vue" for n in revised["nodes"]))

    def test_ignores_observer_cache_and_preferences_without_hiding_application_files(self):
        before, _ = self.graph()
        for name in ("node_modules/tool/test.py", ".stategraph/poll.txt", "bo_stategraph/config/views/local.json", "bo_stategraph/data/recordings/test.json"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("{}")
        after, _ = self.graph()
        self.assertEqual(before["revision"], after["revision"])
        self.assertIn("src/routes.py", after["project"]["entries"])

    def test_check_rejects_missing_directory_or_dependency_without_repair(self):
        self.graph()
        saved = self.service.cache.read_text()
        for field in ("nodes", "edges", "project"):
            graph = json.loads(saved)
            graph[field] = [] if field != "project" else {}
            self.service.cache.write_text(json.dumps(graph))
            self.assertFalse(self.service.check()["valid"])
            self.assertEqual(json.loads(self.service.cache.read_text())[field], graph[field])

    def test_invalid_source_remains_a_file_and_fails_coverage(self):
        (self.root / "src/broken.py").write_text("def broken(\n")
        graph, _ = self.service.refresh()
        self.assertTrue(graph["errors"])
        self.assertIn("src/broken.py", graph["project"]["entries"])
        self.assertNotIn("src/broken.py::broken", graph["symbols"])
        self.assertFalse(self.service.check()["valid"])

    def test_scanned_text_does_not_bypass_source_reader_allowlist(self):
        graph, _ = self.graph()
        self.assertIn("intent.json", graph["project"]["entries"])
        with self.assertRaises(ValueError):
            self.service.source("intent.json", graph["revision"])
        self.assertIn("button", self.service.source("web/main.css", graph["revision"])["source"])

    def test_explicit_scope_and_unresolved_alias_are_preserved(self):
        (self.root / "sync.json").write_text(json.dumps({
            "model": "bo_stategraph/project.json", "source_scope": {"roots": ["web"]}}))
        (self.root / "web/alias.ts").write_text("import { share } from '@/share';\n")
        graph, _ = self.graph()
        self.assertNotIn("src/routes.py", graph["project"]["entries"])
        unresolved = next(n for n in graph["nodes"] if n["label"] == "@/share")
        self.assertEqual(unresolved["reference_scope"], "project")
        self.assertFalse(any(e["from"] == identity("file", "web/alias.ts")
                             and e["to"] == identity("file", "web/share.ts") for e in graph["edges"]))

    def test_invalid_manifest_is_not_successfully_indexed(self):
        (self.root / "package.json").write_text('{"dependencies": ["invalid"]}')
        graph, _ = self.service.refresh()
        self.assertTrue(any(e["path"] == "package.json" for e in graph["errors"]))
        self.assertFalse(self.service.check()["valid"])

    def test_package_name_alone_does_not_prove_local_dependency(self):
        (self.root / "package.json").write_text(json.dumps({"dependencies": {"file-ui": "^1"}}))
        graph, _ = self.graph()
        edge = next(e for e in graph["edges"] if e["from"] == identity("file", "package.json")
                    and e["code_relation"] == "dependency")
        self.assertNotEqual(edge["to"], identity("file", "packages/ui/package.json"))
        (self.root / "package.json").write_text(json.dumps({"dependencies": {"file-ui": "file:packages/ui"}}))
        graph, _ = self.graph()
        self.assertTrue(any(e["code_relation"] == "dependency" and e["to"] == identity("file", "packages/ui/package.json")
                            for e in graph["edges"]))

    def test_filesystem_links_are_not_recursively_expanded(self):
        link = self.root / "readme-link.txt"
        try:
            link.symlink_to(self.root / "README.md")
        except OSError as error:
            self.skipTest("Host does not allow creating symlinks: " + str(error))
        graph, _ = self.graph()
        self.assertEqual(graph["project"]["entries"]["readme-link.txt"]["kind"], "symlink")
        self.assertTrue(any(edge["code_relation"] == "links"
                            and edge["from"] == identity("file", "readme-link.txt")
                            and edge["to"] == identity("file", "README.md") for edge in graph["edges"]))
        self.assertNotIn("readme-link.txt", graph["files"])

    def test_large_cycle_scan_and_single_file_incremental_update(self):
        (self.root / "bulk").mkdir()
        total = 1500
        for number in range(total):
            (self.root / f"bulk/file{number}.py").write_text(
                f"from bulk.file{(number + 1) % total} import read\ndef read(value): return value\n")
        start = time.perf_counter()
        graph, _ = self.graph()
        cold = time.perf_counter() - start
        self.assertTrue(any(len(cycle) == total for cycle in graph["project"]["file_cycles"]))
        original = graph["revision"]
        (self.root / "bulk/file0.py").write_text("from bulk.file1 import read\ndef read(value): return 1\n")
        start = time.perf_counter()
        updated, _ = self.graph()
        warm = time.perf_counter() - start
        self.assertNotEqual(original, updated["revision"])
        self.assertEqual(updated["incremental"]["parsed"], ["bulk/file0.py"])
        self.assertGreaterEqual(len(updated["incremental"]["reused"]), total - 1)
        report = {"files": total, "nodes": len(updated["nodes"]), "edges": len(updated["edges"]),
                  "cold_seconds": cold, "changed_file_seconds": warm,
                  "parsed": len(updated["incremental"]["parsed"]), "reused": len(updated["incremental"]["reused"])}
        (ROOT / ".validation/engineering-performance.json").write_text(json.dumps(report, indent=2))
        print("\nEngineering benchmark: " + json.dumps(report))

    def test_http_tree_requests_are_not_business_events(self):
        session = GraphSession(self.root)
        server = make_server(session, port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for _ in range(2):
                with urlopen(f"http://127.0.0.1:{server.server_port}/api/code/graph?projection=project") as response:
                    value = json.load(response)
                self.assertEqual(value["projection"], "project")
            self.assertEqual(session.sequence, 0)
            self.assertEqual(session.model, self.project["model"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
            session.close()

    def test_cancelled_source_response_does_not_attempt_an_error_response(self):
        session = GraphSession(self.root)
        server = make_server(session, port=0)
        try:
            for failing_write in (1, 2):
                writes = []
                def write(raw):
                    writes.append(raw)
                    if len(writes) == failing_write:
                        raise ConnectionAbortedError("Source request cancelled")
                handler = SimpleNamespace(
                    headers={}, close_connection=False,
                    send_response=lambda code: None,
                    send_header=lambda key, value: None,
                    end_headers=lambda: write(b"headers"),
                    wfile=SimpleNamespace(write=write))
                server.RequestHandlerClass.reply(handler, 200, {"source": "def read(): pass"})
                self.assertTrue(handler.close_connection)
                self.assertEqual(len(writes), failing_write)
            self.assertEqual(session.sequence, 0)
        finally:
            server.server_close()
            session.close()


if __name__ == "__main__":
    unittest.main()
