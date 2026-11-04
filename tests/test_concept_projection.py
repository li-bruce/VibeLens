"""A model diagram must retain the conditions a developer is asked to confirm."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/vibelens"
sys.path.insert(0, str(SKILL / "scripts"))

from bo_observer.concepts.model import build  # noqa: E402
from bo_observer.concepts.registry import ConceptGraph  # noqa: E402


class ConceptProjectionTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(
            (SKILL / "assets/discovery.concepts.example.json").read_text(encoding="utf-8")
        )

    def test_guard_polarity_and_transition_metadata_survive_projection(self):
        positive = build(self.document)
        negative_doc = deepcopy(self.document)
        transition = negative_doc["state_models"][0]["transitions"][0]
        transition["unless"] = transition.pop("conditions")
        negative = build(negative_doc)
        guard_id = "transition-guard:grant:grant-share:may_manage"
        projected = [
            next(edge for edge in item["graph"]["edges"] if edge["id"] == guard_id)
            for item in (positive, negative)
        ]
        self.assertEqual([edge["negated"] for edge in projected], [False, True])
        self.assertEqual([edge["label"] for edge in projected], ["Requires true", "Requires false"])
        for model in (positive, negative):
            for edge in model["graph"]["edges"]:
                if edge["type"] == "transition":
                    record = model["records"][edge["id"]]
                    for field in ("transition", "trigger", "conditions", "unless"):
                        self.assertEqual(edge[field], record[field])

    def test_state_containment_has_a_typed_display_hint_without_a_fake_runtime_parent(self):
        projection = build(self.document)
        memberships = [
            edge
            for edge in projection["graph"]["edges"]
            if edge["id"].startswith("state-contains:")
        ]
        self.assertTrue(memberships)
        for edge in memberships:
            self.assertEqual(edge["containment_kind"], "state_hierarchy")
            self.assertNotIn("containment_kind", projection["records"][edge["id"]])
        for node in projection["graph"]["nodes"]:
            if node.get("concept_kind") == "state":
                self.assertNotIn("parent", node)
                self.assertEqual(node["capture"], {})

    def test_metadata_cannot_overwrite_edge_identity_and_is_detached(self):
        registry = ConceptGraph()
        fields = {
            "id": "wrong",
            "from": "wrong",
            "type": "wrong",
            "conditions": ["owner"],
            "units": 2,
        }
        registry.relation("r", "a", "b", "guard", value=fields)
        fields["conditions"].append("later")
        edge = registry.edges[0]
        self.assertEqual(
            (edge["id"], edge["from"], edge["to"], edge["type"]), ("r", "a", "b", "guard")
        )
        self.assertEqual(edge["conditions"], ["owner"])
        self.assertEqual(edge["units"], 2)

    def test_authored_rule_labels_do_not_change_semantic_identity(self):
        original = build(self.document)
        self.document["policy"]["predicates"][0]["label"] = "比较用户身份"
        self.document["policy"]["operations"][0]["label"] = "是否允许管理共享"
        localized = build(self.document)
        by_id = {node["id"]: node for node in localized["graph"]["nodes"]}
        predicate = self.document["policy"]["predicates"][0]["id"]
        operation = self.document["policy"]["operations"][0]["id"]
        self.assertEqual(by_id["policy-predicate:" + predicate]["label"], "比较用户身份")
        self.assertEqual(by_id["policy-operation:" + operation]["label"], "是否允许管理共享")
        self.assertEqual(localized["records"], original["records"])
        self.assertEqual(localized["dependencies"], original["dependencies"])
        self.assertEqual(localized["index"], original["index"])


if __name__ == "__main__":
    unittest.main()
