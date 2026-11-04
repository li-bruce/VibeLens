"""Source comments, API identities and report failures use independent evidence."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from bo_observer.code_graph.service import CodeGraph
from bo_observer.graph.behavior_model import capture
from bo_observer.graph.code_structure import parse_unit
from bo_observer.graph.source_documentation import report
from bo_observer.sources import parse_javascript, scan
from test_multilanguage import project_fixture


class SourceDocumentationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.temp.name)
        self.project = project_fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        (self.root / name).write_text(text, encoding="utf-8")

    def test_python_google_numpy_and_sphinx_comments_are_source_facts(self):
        bodies = [
            '"""Read a stored file.\n\nArgs:\n    file_id (str): Stored file identity.\n\nReturns:\n    Bytes for that file.\n"""',
            '"""Read a stored file.\n\nParameters\n----------\nfile_id : str, optional\n    Stored file identity.\n\nReturns\n-------\nbytes\n"""',
            '"""Read a stored file.\n\n:param file_id: Stored file identity.\n:return: File bytes.\n"""',
        ]
        for body in bodies:
            with self.subTest(body=body):
                source = (
                    "def read_file(file_id):\n    "
                    + body.replace("\n", "\n    ")
                    + "\n    return file_id\n"
                )
                doc = parse_unit("storage.py", source)["symbols"]["read_file"]["documentation"]
                self.assertEqual(doc["summary"], "Read a stored file.")
                self.assertEqual(
                    doc["parameters"]["file_id"]["description"].strip(), "Stored file identity."
                )
                self.assertNotIn("Returns", doc["parameters"])
                self.assertEqual(doc["source"]["path"], "storage.py")
                self.assertEqual(doc["source"]["symbol"], "read_file")

    def test_missing_docstring_is_explicit_and_never_uses_the_function_name(self):
        doc = parse_unit("files.py", "def useful_name(value):\n    return value\n")["symbols"][
            "useful_name"
        ]["documentation"]
        self.assertEqual(doc["status"], "missing")
        self.assertEqual(doc["summary"], "")

    def test_js_ts_react_vue_docs_retain_complete_file_coordinates(self):
        snippets = {
            "api.mjs": "/** Read a stored file.\n * @param fileId Stored file identity.\n */\nexport function readFile(fileId) { return fileId; }",
            "api.ts": "/** Read a stored file.\n * @param fileId Stored file identity.\n */\nexport const readFile = (fileId: string) => fileId;",
            "Files.tsx": "/** Display shared files.\n * @param props The visible file list.\n */\nexport function Files(props: any) { return <main>{props.title}</main>; }",
            "Files.vue": "<template><p>Files</p></template>\n<script setup lang='ts'>\n/** Read a stored file.\n * @param fileId Stored file identity.\n */\nfunction readFile(fileId: string) { return fileId; }\n</script>",
        }
        result = parse_javascript(
            [{"path": path, "source": source} for path, source in snippets.items()]
        )
        self.assertEqual(result["errors"], [])
        for path, unit in result["units"].items():
            symbol = unit["symbols"]["Files" if path.endswith("tsx") else "readFile"]
            doc = symbol["documentation"]
            self.assertEqual(doc["status"], "documented")
            self.assertEqual(doc["source"]["path"], path)
            self.assertEqual(doc["source"]["line"], 3 if path.endswith("vue") else 1)
            self.assertEqual(
                doc["parameters"]["props" if path.endswith("tsx") else "fileId"]["description"],
                "The visible file list." if path.endswith("tsx") else "Stored file identity.",
            )

    def test_comment_changes_refresh_explanations_without_changing_node_ids(self):
        initial = 'def advance(state, event, slots):\n    """Wait for a free slot."""\n    return "waiting"\n'
        self.write("worker.py", initial)
        service = CodeGraph(self.root, persist=False)
        first, _ = service.refresh()
        node_id = first["symbols"]["worker.py::advance"]
        before = next(n for n in first["nodes"] if n["id"] == node_id)
        self.assertEqual(before["documentation"]["summary"], "Wait for a free slot.")
        self.write(
            "worker.py", initial.replace("Wait for a free slot.", "Resume when a slot opens.")
        )
        second, _ = service.refresh()
        self.assertEqual(second["symbols"]["worker.py::advance"], node_id)
        self.assertNotEqual(first["revision"], second["revision"])
        self.assertEqual(
            next(n for n in second["nodes"] if n["id"] == node_id)["documentation"]["summary"],
            "Resume when a slot opens.",
        )
        self.assertFalse(
            any(
                n.get("documentation", {}).get("summary") == "Wait for a free slot."
                for n in second["nodes"]
            )
        )

    def test_manifest_attaches_verified_comments_and_coordinates(self):
        self.write(
            "worker.py",
            'def advance(state, event, slots):\n    """Wait for a free slot."""\n    return "waiting"\n',
        )
        binding = capture(self.root, self.project["model"])["bindings"]["advance"]
        self.assertEqual(binding["documentation"]["summary"], "Wait for a free slot.")
        self.assertEqual(binding["documentation"]["source"]["file_sha256"], binding["file_sha256"])
        self.assertEqual(binding["documentation"]["source"]["path"], "worker.py")

    def test_api_documentation_and_parameter_description_bind_to_exact_source(self):
        self.write(
            "api.py",
            'from flask import Flask\napp = Flask(__name__)\n@app.get(\'/files/<file_id>\')\ndef read(file_id):\n    """Read a stored file.\n\n    Args:\n        file_id: Stored file identity.\n    """\n    return file_id\n',
        )
        graph, _ = CodeGraph(self.root, persist=False).refresh()
        endpoint = next(n for n in graph["nodes"] if n.get("code_role") == "endpoint")
        self.assertEqual(endpoint["api_role"], "endpoint")
        self.assertEqual(endpoint["api"]["path"], "/files/<file_id>")
        self.assertEqual(endpoint["documentation"]["summary"], "Read a stored file.")
        parameter = next(
            n
            for n in graph["nodes"]
            if n.get("code_role") == "parameter" and n["label"] == "file_id"
        )
        self.assertEqual(parameter["documentation"]["summary"], "Stored file identity.")
        self.assertEqual(parameter["source"]["selection"]["line"], 4)
        self.assertEqual(parameter["documentation"]["parameter"], "file_id")

    def test_strict_report_distinguishes_missing_parameter_from_missing_comment(self):
        self.write(
            "mapped.py", 'def read(file_id):\n    """Read a stored file."""\n    return file_id\n'
        )
        index = scan(self.root, ["mapped.py"])
        model = {
            "nodes": [
                {
                    "id": "file-state",
                    "represents": {"path": "mapped.py", "symbol": "read", "parameter": "file_id"},
                }
            ]
        }
        first = report(index, model)
        self.assertFalse(first["valid"])
        self.assertEqual(first["missing"][0]["reason"], "parameter_description_missing")
        model["nodes"][0]["represents"]["parameter"] = "removed_id"
        self.assertEqual(report(index, model)["missing"][0]["reason"], "source_parameter_missing")
        self.assertEqual(report(index, {"nodes": []})["missing"], [])

    def test_api_handlers_are_checked_even_when_missing_from_the_authored_map(self):
        self.write(
            "api.py",
            "from flask import Flask\napp = Flask(__name__)\n@app.get('/files')\ndef read():\n    return []\n",
        )
        result = report(scan(self.root, ["api.py"]), {"nodes": []})
        self.assertEqual(
            result["missing"], [{"symbol": "api.py::read", "reason": "source_summary_missing"}]
        )

    def test_inventory_parameters_need_source_descriptions_without_parameter_nodes(self):
        self.write(
            "app.py",
            'def upload(note):\n    """Store an uploaded file. Keep notes with it."""\n    return note\n',
        )
        model = {
            "nodes": [],
            "implementation": {
                "features": [
                    {
                        "parameters": [
                            {
                                "source": "app.py::upload",
                                "name": "note",
                                "node": "upload",
                                "field": "message",
                            }
                        ]
                    }
                ]
            },
        }
        first = report(scan(self.root, ["app.py"]), model)
        self.assertEqual(
            first["missing"],
            [
                {
                    "symbol": "app.py::upload",
                    "parameter": "note",
                    "reason": "parameter_description_missing",
                }
            ],
        )
        self.write(
            "app.py",
            'def upload(note):\n    """Store an uploaded file. Keep notes with it.\n\n    Args:\n        note: Message attached to this upload.\n    """\n    return note\n',
        )
        index = scan(self.root, ["app.py"])
        self.assertTrue(report(index, model)["valid"])
        self.assertEqual(
            index["symbols"]["app.py::upload"]["documentation"]["summary"],
            "Store an uploaded file.",
        )

    def test_imported_python_handler_uses_the_same_resolution_for_docs_and_graph(self):
        self.write("handlers.py", "def read_file():\n    return []\n")
        self.write(
            "api.py",
            "from flask import Flask\nfrom handlers import read_file\napp = Flask(__name__)\napp.add_url_rule('/files', view_func=read_file, methods=['GET'])\n",
        )
        service = CodeGraph(self.root, persist=False)
        result = service.documentation()
        self.assertIn(
            {"symbol": "handlers.py::read_file", "reason": "source_summary_missing"},
            result["missing"],
        )
        self.write(
            "handlers.py", 'def read_file():\n    """Read visible files."""\n    return []\n'
        )
        graph, _ = service.refresh()
        route = next(n for n in graph["nodes"] if n.get("code_role") == "endpoint")
        self.assertEqual(route["documentation"]["source"]["path"], "handlers.py")
        self.assertEqual(route["documentation"]["summary"], "Read visible files.")

    def test_imported_javascript_handlers_remain_real_routes_and_docs_obligations(self):
        self.write("handlers.mjs", "export function readFiles(req, res) { return res.json([]); }\n")
        self.write(
            "routes.mjs",
            "import express from 'express';\nimport { readFiles } from './handlers.mjs';\nconst app = express();\napp.get('/files', readFiles);\n",
        )
        service = CodeGraph(self.root, persist=False)
        graph, _ = service.refresh()
        route = next(n for n in graph["nodes"] if n.get("code_role") == "endpoint")
        self.assertEqual(route["api"]["path"], "/files")
        self.assertTrue(route["api"]["handler_resolved"])
        self.assertTrue(
            any(
                e["from"] == route["id"] and e["to"] == graph["symbols"]["handlers.mjs::readFiles"]
                for e in graph["edges"]
            )
        )
        self.assertIn(
            {"symbol": "handlers.mjs::readFiles", "reason": "source_summary_missing"},
            service.documentation()["missing"],
        )

    def test_generic_get_methods_and_shadowed_routers_are_not_http_endpoints(self):
        self.write(
            "python_routes.py",
            "from flask import Flask\napp=Flask(__name__)\nclass Cache:\n    def get(self, key): return lambda function: function\ncache=Cache()\n@cache.get('/cached')\ndef cached(): return []\n@app.get('/files')\ndef files(): return []\n",
        )
        self.write(
            "javascript_routes.mjs",
            "import express from 'express';\nconst app=express();\nfunction files(req,res) { return res.json([]); }\napp.get('/real',files);\nconst cache=new Map();\ncache.get('/cached',files);\nfunction other(app) { app.get('/shadowed',files); }\n",
        )
        graph, _ = CodeGraph(self.root, persist=False).refresh()
        self.assertEqual(
            {n["api"]["path"] for n in graph["nodes"] if n.get("code_role") == "endpoint"},
            {"/files", "/real"},
        )

    def test_shared_handler_distinct_methods_and_paths_remain_distinct_routes(self):
        self.write(
            "routes.mjs",
            "import express from 'express';\nconst app=express();\nfunction files(req,res) { return res.json([]); }\napp.get('/files',files);\napp.post('/files',files);\napp.get('/archive',files);\n",
        )
        graph, _ = CodeGraph(self.root, persist=False).refresh()
        routes = [n for n in graph["nodes"] if n.get("code_role") == "endpoint"]
        self.assertEqual(
            {(n["api"]["path"], tuple(n["api"]["methods"])) for n in routes},
            {("/files", ("GET",)), ("/files", ("POST",)), ("/archive", ("GET",))},
        )
        self.assertEqual(len({n["id"] for n in routes}), 3)
        self.assertEqual(
            len({e["to"] for e in graph["edges"] if e["code_relation"] == "handles"}), 1
        )

    def test_unproven_callback_registration_remains_source_evidence_without_an_api(self):
        self.write(
            "api.ts",
            'export function create(name:string){return name}; app.post("/create",create);\n',
        )
        index = scan(self.root, ["api.ts"])
        symbol = index["symbols"]["api.ts::create"]
        self.assertEqual(symbol["entrypoints"], ['app.post("/create")'])
        self.assertEqual(symbol["http_endpoints"], [])
        graph, _ = CodeGraph(self.root, persist=False).refresh()
        self.assertFalse(any(node.get("code_role") == "endpoint" for node in graph["nodes"]))

    def test_one_middleware_registration_has_one_endpoint_with_all_handlers(self):
        self.write(
            "routes.mjs",
            "import express from 'express';\nconst app=express();\nfunction authenticate(req,res,next) { next(); }\nfunction files(req,res) { return res.json([]); }\napp.get('/files',authenticate,files);\n",
        )
        graph, _ = CodeGraph(self.root, persist=False).refresh()
        routes = [n for n in graph["nodes"] if n.get("code_role") == "endpoint"]
        self.assertEqual(len(routes), 1)
        route = routes[0]
        self.assertEqual(len(route["api"]["registration_ids"]), 2)
        targets = {
            e["to"]
            for e in graph["edges"]
            if e["from"] == route["id"] and e["code_relation"] == "handles"
        }
        self.assertEqual(
            targets,
            {graph["symbols"]["routes.mjs::authenticate"], graph["symbols"]["routes.mjs::files"]},
        )
        self.assertEqual(set(graph["endpoint_aliases"].values()), {route["id"]})

    def test_independent_registrations_sharing_a_path_are_not_merged(self):
        self.write(
            "routes.mjs",
            "import express from 'express';\nconst app=express();\nfunction first(req,res) { return res.json([]); }\nfunction second(req,res) { return res.json([]); }\napp.get('/files',first); app.get('/files',second);\n",
        )
        graph, _ = CodeGraph(self.root, persist=False).refresh()
        self.assertEqual(len([n for n in graph["nodes"] if n.get("code_role") == "endpoint"]), 2)
        self.assertEqual(graph["endpoint_aliases"], {})

    def test_decorator_method_order_preserves_existing_endpoint_identity(self):
        from bo_observer.code_graph.index import identity

        self.write(
            "api.py",
            "from flask import Flask\napp=Flask(__name__)\n@app.route('/files',methods=['POST','GET'])\ndef files(): return []\n",
        )
        graph, _ = CodeGraph(self.root, persist=False).refresh()
        route = next(n for n in graph["nodes"] if n.get("code_role") == "endpoint")
        self.assertEqual(
            route["id"], identity("endpoint", ["api.py::files", "/files", ["POST", "GET"]])
        )

    def test_cli_strict_fails_then_passes_after_source_fix(self):
        command = [
            sys.executable,
            "-B",
            str(ROOT / "skills/vibelens/scripts/bo_code.py"),
            "docs",
            "--root",
            str(self.root),
            "--strict",
        ]
        failed = subprocess.run(command, text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(failed.returncode, 1, failed.stderr)
        self.assertTrue(json.loads(failed.stdout)["missing"])
        self.write(
            "worker.py",
            'def advance(state, event, slots):\n    """Wait for a free slot."""\n    return "waiting"\n',
        )
        passed = subprocess.run(command, text=True, capture_output=True, encoding="utf-8")
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertTrue(json.loads(passed.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
