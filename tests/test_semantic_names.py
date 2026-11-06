"""Names are translated presentation evidence, never a second executable model."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.web import semantic_names as names


def fixture():
    return {
        "model": {
            "nodes": [
                {"id": "share", "label": "Share", "layer": "business", "kind": "business"},
                {
                    "id": "allowed",
                    "label": "allowed",
                    "layer": "parameter",
                    "kind": "data",
                    "source": {"path": "sharing.py", "symbol": "allowed", "line": 10},
                    "capture": {"out": {"result": {"actor/id": "str"}}},
                },
            ],
            "edges": [
                {
                    "id": "next",
                    "from": "share",
                    "to": "allowed",
                    "type": "flow",
                    "label": "After sharing",
                }
            ],
            "machine": {"values": ["active"], "events": {"share": {}}, "initial": "active"},
        },
        "concept_structure": {
            "nodes": [
                {
                    "id": "state:active",
                    "concept_id": "grant:active",
                    "concept_kind": "state",
                    "layer": "state",
                    "label": "Active",
                },
                {
                    "id": "rule:active",
                    "concept_kind": "predicate",
                    "layer": "rules",
                    "label": "Grant is active",
                },
            ],
            "edges": [],
        },
    }


def document(items):
    result = {"schema": names.SCHEMA, "locales": ["en", "zh-CN"], "names": {}, "basis": {}}
    for item in items:
        result["names"].setdefault(item["category"], {})[item["id"]] = {
            "en": item["label"],
            "zh-CN": "示例名称",
        }
        result["basis"].setdefault(item["category"], {})[item["id"]] = item["basis"]
    return result


class SemanticNamesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / ".validation").mkdir(exist_ok=True)

    def test_overlay_is_detached_and_layer_specific(self):
        view = fixture()
        before = deepcopy(view)
        items = names.inventory(view)
        doc = document(items)
        doc["names"]["concepts"]["grant:active"]["zh-CN"] = "授权有效"
        doc["names"]["concepts"]["rule:active"]["zh-CN"] = "授权仍然有效"
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as directory:
            self.assertTrue(names.install(directory, doc, items)["valid"])
            result = names.overlay_model(directory, view["model"])
            self.assertEqual(result["machine"], view["model"]["machine"])
            self.assertEqual(result["nodes"], view["model"]["nodes"])
            self.assertEqual(result["edges"], view["model"]["edges"])
            self.assertNotEqual(
                result["presentation"]["names"]["concepts"]["grant:active"],
                result["presentation"]["names"]["concepts"]["rule:active"],
            )
            result["nodes"][0]["label"] = "Detached"
        self.assertEqual(view, before)

    def test_new_nodes_and_changed_meaning_require_maintenance(self):
        view = fixture()
        items = names.inventory(view)
        doc = document(items)
        view["model"]["nodes"][1]["source"]["line"] = 200
        self.assertTrue(names.assess(names.inventory(view), doc)["valid"])
        view["model"]["nodes"][1]["documentation"] = {"summary": "Read the current recipient grant"}
        view["model"]["nodes"].append({"id": "revoke", "label": "Revoke", "layer": "business"})
        result = names.assess(names.inventory(view), doc)
        self.assertFalse(result["valid"])
        self.assertIn({"category": "nodes", "id": "allowed"}, result["stale"])
        self.assertEqual({entry["locale"] for entry in result["missing"]}, {"en", "zh-CN"})
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as directory:
            names.install(directory, doc, items)
            with patch.object(names, "project_inventory", return_value=names.inventory(view)):
                self.assertFalse(names.check_project(directory)["valid"])

    def test_validation_rejects_malformed_locales_basis_and_long_names(self):
        valid = document(names.inventory(fixture()))
        for field, value in [
            ("locales", [[]]),
            ("locales", ["en", "en"]),
            ("basis", {"nodes": []}),
            ("names", []),
            ("schema", "unknown"),
        ]:
            with self.subTest(field=field, value=value):
                invalid = {**valid, field: value}
                with self.assertRaises(ValueError):
                    names.validate(invalid)
        for value in [{"en": "Share"}, {"en": "x" * 61, "zh-CN": "共享"}, "Share"]:
            invalid = deepcopy(valid)
            invalid["names"]["nodes"]["share"] = value
            with self.assertRaises(ValueError):
                names.validate(invalid)

    def test_capture_paths_match_viewer_and_skip_nonexistent_query_outcomes(self):
        view = fixture()
        view["concept_structure"]["nodes"].append(
            {"id": "allowed", "concept_kind": "operation", "capture": {}}
        )
        view["model"]["nodes"].append(
            {
                "id": "query",
                "label": "Read grants",
                "data_role": "query",
                "data_metadata": {"action": "select"},
                "capture": {"out": {"committed": "bool", "rows": "int"}},
            }
        )
        ids = {item["id"] for item in names.inventory(view)}
        self.assertIn("field:allowed:out:result:actor%2Fid", ids)
        self.assertIn("field:query:out:rows", ids)
        self.assertNotIn("field:query:out:committed", ids)

    def test_unconfigured_legacy_and_invalid_file_are_distinct(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as directory:
            self.assertEqual(names.check_project(directory)["status"], "not_configured")
            target = Path(directory) / names.FILE
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps({"schema": names.SCHEMA, "names": []}), encoding="utf-8")
            self.assertFalse(names.check_project(directory)["valid"])

    def test_design_inventory_and_overlay_work_before_source_exists(self):
        from test_concept_models import draft
        from bo_observer.web.bo_design import BODesign

        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as directory:
            root = Path(directory)
            (root / "discovery.json").write_text(json.dumps(draft()), encoding="utf-8")
            items = names.project_inventory(root)
            doc = document(items)
            names.install(root, doc, items)
            view = BODesign(root).view()
            self.assertEqual(view["events"], [])
            self.assertEqual(view["model"]["presentation"]["names"], doc["names"])
            self.assertTrue(names.check_project(root)["valid"])


if __name__ == "__main__":
    unittest.main()
