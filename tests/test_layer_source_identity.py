"""Keep physical declarations unique without erasing semantic/capture identities."""

from copy import deepcopy
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools"), str(ROOT / "tests")]
from test_multilanguage import project_fixture
from test_database_protocol import data_fixture
from bo_observer.graph.code_structure import scan, enrich
from bo_observer.graph.source_identity import declaration_id, identity
from bo_observer.graph.source_documentation import report as documentation_report
from bo_observer.code_graph.index import build
from bo_observer.code_graph.query import query
from bo_observer.code_graph.service import CodeGraph
from bo_observer.protocol import validate_project, validate_event
from bo_observer.data.protocol import validate_data_projection, OPERATION_ROLES
from bo_observer.data.contract import capture_spec
from bo_observer.policy.projection import project as project_policy, projection_errors


class LayerSourceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.temp.name)
        self.project = project_fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, source):
        (self.root / name).write_text(source, encoding="utf-8")

    def test_enriched_model_loads_in_isolated_standalone_package(self):
        """Shipping the native model must not require the external observer package."""
        model = enrich(self.project["model"], scan(self.root, ["worker.py"]), depth=2)
        package = self.root / "native_graph"
        package.mkdir()
        scripts = ROOT / "skills/vibelens/scripts"
        for source, target in (
            ("bo_stategraph.py", "__init__.py"),
            ("bo_contracts.py", "bo_contracts.py"),
            ("bo_models.py", "bo_models.py"),
            ("execution_contract.py", "execution_contract.py"),
        ):
            shutil.copyfile(scripts / source, package / target)
        runner = """
import importlib.abc, json, sys
from pathlib import Path
class RejectObserver(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if "bo_observer" in fullname.split("."):
            raise AssertionError("standalone package imported observer: " + fullname)
sys.meta_path.insert(0, RejectObserver())
sys.path.insert(0, str(Path.cwd()))
from native_graph import BOStateGraph
from native_graph.bo_contracts import validate_graph
model = json.load(sys.stdin)
validate_graph(model)
graph = BOStateGraph(model, build_id="isolated")
assert graph.bo_structure() == model
assert graph.bo_instances() == []
reference = next(node for node in model["nodes"] if node.get("declaration_id"))
reference["declaration_id"] = "code:symbol:forged"
try:
    validate_graph(model)
except ValueError as error:
    assert "source declaration identity differs" in str(error), error
else:
    raise AssertionError("forged declaration identity was accepted")
print("standalone source reference checks passed")
"""
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-c", runner],
            cwd=self.root,
            input=json.dumps(model),
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("standalone source reference checks passed", result.stdout)

    def test_shared_helpers_reference_one_physical_declaration_and_keep_context_ids(self):
        self.write(
            "worker.py",
            "def shared(value):\n    return value\n"
            "def advance(state: str, event: str, slots: int):\n    return shared(state)\n"
            "def finish(state):\n    return shared(state)\n",
        )
        model = self.project["model"]
        model["nodes"].append(
            {
                "id": "finish-op",
                "kind": "action",
                "layer": "business",
                "label": "Finish task",
                "summary": "Finish task",
                "source": {"path": "worker.py", "symbol": "finish"},
                "capture": {"in": {}, "out": {}},
            }
        )
        model["overview"].append({"node": "finish-op"})
        index = scan(self.root, ["worker.py"])
        result = enrich(model, index, depth=2)
        physical = declaration_id({"path": "worker.py", "symbol": "shared"})
        declarations = [
            node
            for node in result["nodes"]
            if node.get("representation_role") == "declaration"
            and node["source"]["symbol"] == "shared"
        ]
        references = [
            node
            for node in result["nodes"]
            if node.get("representation_role") == "source-reference"
            and node.get("declaration_id") == physical
        ]
        self.assertEqual([node["id"] for node in declarations], [physical])
        self.assertEqual(len(references), 2)
        self.assertEqual(len({node["id"] for node in references}), 2)
        self.assertTrue(
            all(
                node["id"].startswith("code.") and node["code_role"] == "reference"
                for node in references
            )
        )
        self.assertTrue(
            all(
                any(
                    edge.get("mapping_role") == "source-reference"
                    and edge["from"] == node["id"]
                    and edge["to"] == physical
                    for edge in result["edges"]
                )
                for node in references
            )
        )
        self.assertEqual(build(index)["symbols"]["worker.py::shared"], physical)
        full = query(build(index), result, limit=5000)
        self.assertFalse(any(edge["from"] == edge["to"] for edge in full["edges"]))
        self.assertTrue(
            all(
                any(
                    edge.get("mapping_role") == "source-reference"
                    and edge["from"] == node["id"]
                    and edge["to"] == physical
                    for edge in full["edges"]
                )
                for node in references
            )
        )
        self.assertEqual(result, enrich(result, index, depth=2))
        validate_project({**self.project, "model": result})

    def test_imported_alias_resolves_to_the_same_declaration_as_complete_code_index(self):
        self.write("rules.py", "def permitted(value):\n    return value\n")
        self.write(
            "worker.py",
            "from rules import permitted as allow\ndef advance(state, event, slots):\n    return allow(state)\n",
        )
        self.project["model"]["source_files"].append("rules.py")
        index = scan(self.root, ["worker.py", "rules.py"])
        result = enrich(self.project["model"], index, depth=2)
        target = build(index)["symbols"]["rules.py::permitted"]
        self.assertEqual(sum(node["id"] == target for node in result["nodes"]), 1)
        self.assertTrue(
            any(
                node.get("representation_role") == "source-reference"
                and node.get("declaration_id") == target
                for node in result["nodes"]
            )
        )

    def test_lexical_context_does_not_expand_mapped_documentation_scope(self):
        self.write(
            "worker.py",
            'def owner():\n    def advance(state, event, slots):\n        """Apply the requested event."""\n        return state\n',
        )
        model = self.project["model"]
        next(node for node in model["nodes"] if node["id"] == "advance")["source"][
            "symbol"
        ] = "owner.advance"
        index = scan(self.root, ["worker.py"])
        result = enrich(model, index)
        self.assertTrue(documentation_report(index, result)["valid"])
        self.assertIn(
            {"symbol": "worker.py::owner", "reason": "source_summary_missing"},
            documentation_report(index, result, all_symbols=True)["missing"],
        )
        # An explicitly mapped owner remains subject to the original check.
        result["nodes"].append(
            {"id": "owner-operation", "source": {"path": "worker.py", "symbol": "owner"}}
        )
        self.assertIn(
            {"symbol": "worker.py::owner", "reason": "source_summary_missing"},
            documentation_report(index, result)["missing"],
        )

    def test_multiple_operations_keep_their_ids_and_capture_contracts_on_one_source(self):
        model = self.project["model"]
        original = deepcopy(model["nodes"][0])
        for name in ("upload-transform", "upload-transaction", "upload-write"):
            model["nodes"].append(
                {**deepcopy(original), "id": name, "label": name, "parent": "advance"}
            )
        index = scan(self.root, ["worker.py"])
        result = enrich(model, index)
        source = declaration_id(original["source"])
        for name in ("advance", "upload-transform", "upload-transaction", "upload-write"):
            node = next(node for node in result["nodes"] if node["id"] == name)
            self.assertEqual(node["declaration_id"], source)
            self.assertEqual(node["capture"], original["capture"])
            self.assertNotEqual(node.get("representation_role"), "source-reference")

    def test_state_enum_is_not_the_physical_parameter_or_equivalent_state_variable(self):
        model = deepcopy(self.project["model"])
        model["nodes"].append(
            {
                "id": "current-state",
                "kind": "data",
                "label": "Current task state",
                "summary": "Current task state",
                "semantic_role": "state_parameter",
                "represents": {"path": "worker.py", "symbol": "advance", "parameter": "state"},
            }
        )
        index = scan(self.root, ["worker.py"])
        result = enrich(model, index)
        physical_parameter = identity("parameter", ["worker.py::advance", "state"])
        view = query(build(index), result, limit=5000)
        equivalents = [edge for edge in view["edges"] if edge.get("mapping_role") == "equivalent"]
        self.assertEqual(
            [(edge["from"], edge["to"]) for edge in equivalents],
            [("current-state", physical_parameter)],
        )
        self.assertNotEqual(physical_parameter, "running")
        self.assertFalse(any(edge["from"] == "running" for edge in equivalents))

    def test_capture_outputs_do_not_become_formal_source_parameters(self):
        model = deepcopy(self.project["model"])
        mapped = next(node for node in model["nodes"] if node["id"] == "advance")
        mapped["capture"]["out"]["committed"] = "boolean"
        index = scan(self.root, ["worker.py"])
        result = enrich(model, index)
        view = query(build(index), result, limit=5000)
        formals = {
            node["source_parameter"]
            for node in view["nodes"]
            if node.get("code_role") == "parameter"
        }
        self.assertNotIn("committed", formals)
        self.assertEqual(formals, {"state", "event", "slots"})
        self.assertEqual(
            next(node for node in result["nodes"] if node["id"] == "advance")["capture"]["out"][
                "committed"
            ],
            "boolean",
        )

    def test_forged_or_missing_canonical_declarations_are_rejected(self):
        result = enrich(self.project["model"], scan(self.root, ["worker.py"]))
        original = next(node for node in result["nodes"] if node["id"] == "advance")
        target = original["declaration_id"]
        for mutate in (
            lambda graph: graph["nodes"].remove(
                next(node for node in graph["nodes"] if node["id"] == target)
            ),
            lambda graph: next(node for node in graph["nodes"] if node["id"] == "advance").update(
                declaration_id="running"
            ),
        ):
            graph = deepcopy(result)
            mutate(graph)
            with self.assertRaisesRegex(ValueError, "source declaration"):
                validate_project({**self.project, "model": graph})

    def test_exact_policy_projection_composes_with_source_enrichment_in_both_orders(self):
        """Generated declarations cannot take ownership of a policy source anchor."""
        import json

        self.write(
            "worker.py",
            "def same_identity(left, right):\n    return left == right\n"
            "def advance(state, event, slots):\n    return same_identity(state, event)\n",
        )
        model = deepcopy(self.project["model"])
        policy = json.loads(
            (ROOT / "skills/vibelens/assets/discovery.concepts.example.json").read_text(
                encoding="utf-8"
            )
        )["policy"]
        policy["stage"] = "bound"
        policy["predicates"][0]["source"] = {"path": "worker.py", "symbol": "same_identity"}
        for operation in policy["operations"]:
            operation.update(business_nodes=["advance"], cases=["actual-rule-case"])
        model["policy"] = policy
        index = scan(self.root, ["worker.py"])

        rules_first = enrich(project_policy(model), index, depth=2)
        source_first = enrich(project_policy(enrich(model, index, depth=2)), index, depth=2)
        for graph in (rules_first, source_first):
            self.assertEqual(projection_errors(graph), [])
            self.assertEqual(project_policy(graph), graph)
            self.assertEqual(enrich(graph, index, depth=2), graph)
            validate_project({**self.project, "model": graph})
            target = declaration_id({"path": "worker.py", "symbol": "same_identity"})
            self.assertEqual(sum(node["id"] == target for node in graph["nodes"]), 1)
            self.assertTrue(
                any(
                    edge["from"] == "policy:is_owner"
                    and edge["to"] == target
                    and edge.get("mapping_role") == "source-binding"
                    for edge in graph["edges"]
                )
            )
            # Exact-rule checks still reject manual changes to owned elements.
            forged = deepcopy(graph)
            next(node for node in forged["nodes"] if node["id"] == "policy:is_owner")[
                "declaration_id"
            ] = target
            self.assertTrue(projection_errors(forged))
        for key in ("nodes", "edges"):
            self.assertEqual(
                {item["id"]: item for item in rules_first[key]},
                {item["id"]: item for item in source_first[key]},
            )

    def test_data_roles_are_precise_but_legacy_query_wrappers_remain_readable(self):
        model = data_fixture(self.project)["model"]
        transaction = deepcopy(next(node for node in model["nodes"] if node["id"] == "db.read"))
        transaction.update(
            id="db.transaction",
            label="File transaction",
            summary="File transaction",
            data_role="transaction",
            data_metadata={"action": "transaction", "targets": []},
            capture=capture_spec(
                {"action": "transaction", "parameters": {}, "before": {}, "after": {}}
            ),
        )
        model["nodes"].append(transaction)
        operations = {
            node["data_metadata"]["action"]: node
            for node in model["nodes"]
            if node.get("data_role") in OPERATION_ROLES
        }
        self.assertEqual(
            {action: node["data_role"] for action, node in operations.items()},
            {
                "read": "query",
                "write": "write",
                "transaction": "transaction",
                "transform": "transform",
            },
        )
        validate_data_projection(model)
        for action in ("write", "transaction"):
            legacy = deepcopy(model)
            next(node for node in legacy["nodes"] if node["id"] == operations[action]["id"])[
                "data_role"
            ] = "query"
            validate_data_projection(legacy)
        malformed = deepcopy(model)
        next(node for node in malformed["nodes"] if node["id"] == operations["read"]["id"])[
            "data_role"
        ] = "transaction"
        with self.assertRaisesRegex(ValueError, "role and action"):
            validate_data_projection(malformed)

    def test_precise_operation_roles_keep_strict_runtime_target_validation(self):
        project = data_fixture(self.project)
        transaction = deepcopy(
            next(node for node in project["model"]["nodes"] if node["id"] == "db.read")
        )
        transaction.update(
            id="db.transaction",
            data_role="transaction",
            data_metadata={"action": "transaction", "targets": []},
            capture=capture_spec(
                {"action": "transaction", "parameters": {}, "before": {}, "after": {}}
            ),
        )
        project["model"]["nodes"].append(transaction)
        event = {
            "protocol": "bo-event/v1",
            "schema_version": 3,
            "project_id": "fixture",
            "model_revision": "1",
            "build_id": "build-1",
            "run_id": "run-1",
            "producer_id": "producer-1",
            "id": "e1",
            "seq": 1,
            "node": "db.read",
            "phase": "return",
            "entity": "app",
            "attempt": "once",
            "scope": "application",
            "call_id": "c1",
            "parent_call_id": None,
            "basis": {},
            "inputs": {},
            "outputs": {},
            "depends": [],
            "observed_at": "2026-11-04T00:00:00Z",
        }
        for node in ("db.read", "db.write", "db.transaction", "db.transform"):
            event["node"] = node
            event["outputs"] = {
                "target_source": "provided",
                "targets": ["table:images"],
                "target_access": [{"target": "table:images", "action": "write"}],
            }
            validate_event(event, project, "build-1")
            for malformed in (
                {"target_source": "guessed"},
                {
                    "targets": ["table:images"],
                    "target_access": [{"target": "table:missing", "action": "write"}],
                },
            ):
                event["outputs"] = malformed
                with self.subTest(node=node, outputs=malformed), self.assertRaises(ValueError):
                    validate_event(event, project, "build-1")

    def test_receiver_specific_routes_are_distinct_stable_and_report_legacy_split(self):
        source = "from flask import Flask\nfirst=Flask('first')\nsecond=Flask('second')\ndef files(): return []\nfirst.add_url_rule('/files',view_func=files,methods=['GET'])\n"
        self.write("api.py", source)
        service = CodeGraph(self.root, persist=False)
        before = service.view(projection="api")
        previous = next(
            node["id"] for node in before["nodes"] if node.get("code_role") == "endpoint"
        )
        self.assertEqual(previous, identity("endpoint", ["api.py::files", "/files", ["GET"]]))
        source += "second.add_url_rule('/files',view_func=files,methods=['GET'])\n"
        self.write("api.py", source)
        current = service.view(projection="api")
        endpoints = [node for node in current["nodes"] if node.get("code_role") == "endpoint"]
        self.assertEqual(len(endpoints), 2)
        self.assertEqual({node["api"]["receiver"] for node in endpoints}, {"first", "second"})
        targets = {node["id"] for node in endpoints}
        self.assertEqual(len(targets), 2)
        self.assertEqual(current["endpoint_migrations"][0]["legacy_id"], previous)
        self.assertEqual(set(current["endpoint_migrations"][0]["targets"]), targets)
        self.assertEqual(current["endpoint_migrations"][0]["resolution"], "requires_selection")
        self.write("api.py", "# Move every declaration down\n\n" + source)
        moved = service.view(projection="api")
        self.assertEqual(
            {node["id"] for node in moved["nodes"] if node.get("code_role") == "endpoint"}, targets
        )

    def test_one_handler_for_different_paths_remains_multiple_real_endpoints(self):
        self.write(
            "api.py",
            "from flask import Flask\napp=Flask(__name__)\n@app.get('/files')\n@app.get('/archive')\ndef files(): return []\n",
        )
        graph = CodeGraph(self.root, persist=False).view(projection="api")
        routes = [node for node in graph["nodes"] if node.get("code_role") == "endpoint"]
        self.assertEqual({node["api"]["path"] for node in routes}, {"/files", "/archive"})
        handler_targets = {
            edge["to"] for edge in graph["edges"] if edge.get("code_relation") == "handles"
        }
        self.assertEqual(len(handler_targets), 1)
        self.assertEqual(len({node["id"] for node in routes}), 2)

    def test_repeated_identical_registration_statements_remain_distinct_after_line_moves(self):
        source = "from flask import Flask\napp=Flask(__name__)\ndef files(): return []\napp.add_url_rule('/files',view_func=files,methods=['GET'])\napp.add_url_rule('/files',view_func=files,methods=['GET'])\n"
        self.write("api.py", source)
        service = CodeGraph(self.root, persist=False)
        before = service.view(projection="api")
        endpoints = [node for node in before["nodes"] if node.get("code_role") == "endpoint"]
        self.assertEqual(len(endpoints), 2)
        self.assertEqual(len({node["api"]["registration_id"] for node in endpoints}), 2)
        original_ids = {node["id"] for node in endpoints}
        self.write("api.py", source.replace("app.add_url_rule", "\n\napp.add_url_rule"))
        after = service.view(projection="api")
        self.assertEqual(
            {node["id"] for node in after["nodes"] if node.get("code_role") == "endpoint"},
            original_ids,
        )


if __name__ == "__main__":
    unittest.main()
