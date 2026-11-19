"""Conversation previews preserve source identities and localize only presentation."""

from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))

from bo_observer.graph.focus_graph import extract
from bo_observer.web.bo_design import BODesign
from bo_observer.web.design_preview import diagram
from bo_observer.web.interface_language import set_language
from bo_observer.web import semantic_names
from test_semantic_names import document as names_document


class DesignPreviewTests(unittest.TestCase):
    def test_preview_reads_installed_localized_names_without_renaming_definitions(self):
        """The Web and chat must explain the same state IDs in the requested language."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            source = root / "discovery.json"
            source.write_bytes(
                (ROOT / "skills/vibelens/assets/discovery.concepts.example.json").read_bytes()
            )
            design = BODesign(root)
            items = semantic_names.inventory(design.view())
            names = names_document(items)
            self.assertTrue(semantic_names.install(root, names, items)["valid"])
            before = source.read_bytes()
            zh = design.preview(
                "http://localhost:8000/graph", view="state", max_nodes=100, locale="zh-CN"
            )
            en = design.preview(
                "http://localhost:8000/graph", view="state", max_nodes=100, locale="en"
            )
            self.assertIn("示例名称", zh["markdown"])
            self.assertNotIn("示例名称", en["markdown"])
            self.assertEqual(zh["focus"], en["focus"])
            self.assertEqual(source.read_bytes(), before)

    def test_shared_boundary_has_one_glyph_and_every_original_relation(self):
        graph = {
            "revision": "design-1",
            "nodes": [
                {"id": ident, "label": label, "kind": "action"}
                for ident, label in [("share", "共享"), ("revoke", "撤销"), ("owner", "所有者")]
            ],
            "edges": [
                {"id": ident, "from": ident, "to": "owner", "type": "requires_decision"}
                for ident in ("share", "revoke")
            ],
        }
        view = extract(graph, ["share", "revoke"], depth=0)
        original = deepcopy(view)
        result = diagram(view, "zh-CN")
        self.assertEqual(len(re.findall(r"^  b\d+\[", result, flags=re.MULTILINE)), 1)
        self.assertEqual(result.count('-.->|"依据判断"| b0'), 2)
        self.assertEqual(view, original)
        self.assertEqual({item["edge_id"] for item in view["boundaries"]}, {"share", "revoke"})

    def test_equal_names_do_not_merge_different_boundary_identities(self):
        graph = {
            "revision": "design-1",
            "nodes": [
                {"id": ident, "label": "Shared name", "kind": "action"}
                for ident in ("inside", "outside-a", "outside-b")
            ],
            "edges": [
                {"id": ident, "from": "inside", "to": ident, "type": "guard"}
                for ident in ("outside-a", "outside-b")
            ],
        }
        result = diagram(extract(graph, ["inside"], depth=0), "en")
        self.assertEqual(len(re.findall(r"^  b\d+\[", result, flags=re.MULTILINE)), 2)

    def test_authored_edge_captions_and_guard_polarity_survive(self):
        graph = {
            "revision": "design-1",
            "nodes": [{"id": ident, "label": ident, "kind": "state"} for ident in ("a", "b")],
            "edges": [
                {"id": "positive", "from": "a", "to": "b", "type": "guarded_by"},
                {
                    "id": "negative",
                    "from": "b",
                    "to": "a",
                    "type": "guarded_by",
                    "negated": True,
                },
                {
                    "id": "authored",
                    "from": "a",
                    "to": "b",
                    "type": "flow",
                    "label": "审核后发布",
                },
            ],
        }
        result = diagram(extract(graph, ["a", "b"]), "zh-CN")
        for label in ("条件成立", "条件不成立", "审核后发布"):
            self.assertIn(label, result)

    def test_saved_language_and_explicit_preview_language_leave_design_unchanged(self):
        (ROOT / ".validation").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            document = json.loads(
                (ROOT / "skills/vibelens/assets/discovery.concepts.example.json").read_text(
                    encoding="utf-8"
                )
            )
            document["networks"][0]["nodes"][0]["label"] = "共享文件"
            source = root / "discovery.json"
            source.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
            original = source.read_bytes()
            set_language(root, "zh-CN", "Synthetic Chinese conversation")
            design = BODesign(root)
            chinese = design.preview("http://127.0.0.1:8830/graph")
            english = design.preview("http://127.0.0.1:8830/graph", locale="en")
            states = design.preview("http://127.0.0.1:8830/graph", view="state", max_nodes=50)
            self.assertTrue(chinese["markdown"].startswith("# 业务网\n"))
            self.assertIn("共享文件", chinese["markdown"])
            self.assertIn("打开动态图", chinese["markdown"])
            self.assertIn("条件成立", states["markdown"])
            self.assertNotIn("Requires true", states["markdown"])
            self.assertTrue(english["markdown"].startswith("# Business network\n"))
            self.assertEqual(chinese["focus"], english["focus"])
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(design.snapshot()["locale"], "zh-CN")
            with self.assertRaises(ValueError):
                design.preview("http://127.0.0.1:8830/graph", locale="unsupported")


if __name__ == "__main__":
    unittest.main()
