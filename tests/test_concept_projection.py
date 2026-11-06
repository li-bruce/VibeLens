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
from bo_observer.concepts.occurrences import separate_occurrences  # noqa: E402


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

    def test_same_native_identifier_does_not_erase_a_different_concept(self):
        graph = {
            "nodes": [
                {"id": "status", "concept_kind": "action", "layer": "business"},
                {"id": "use", "concept_kind": "action", "parent": "status"},
            ],
            "edges": [{"id": "next", "from": "status", "to": "use", "type": "flow"}],
            "graph_roots": ["status"],
        }
        native = {
            "nodes": [{"id": "status", "kind": "data", "source": {"symbol": "status"}}],
            "edges": [{"id": "next", "from": "status", "to": "status", "type": "data"}],
        }
        original = deepcopy(native)
        aliases = separate_occurrences(graph, native)
        self.assertEqual(aliases, {"status": "concept-view:status"})
        self.assertEqual(graph["nodes"][0]["concept_id"], "status")
        self.assertEqual(graph["nodes"][1]["parent"], "concept-view:status")
        self.assertEqual(graph["graph_roots"], ["concept-view:status"])
        self.assertEqual(graph["edges"][0]["from"], "concept-view:status")
        self.assertEqual(graph["relation_occurrences"], {"next": "concept-relation:next"})
        self.assertEqual(native, original)

    def test_network_review_cannot_mistake_containment_for_execution(self):
        from bo_observer.concepts.network_review import network_review

        graph = build(self.document)["graph"]
        complete = network_review(graph)
        self.assertGreater(complete["business"]["behavior_relations"], 0)
        self.assertGreater(complete["state"]["behavior_relations"], 0)
        self.assertGreater(complete["rules"]["behavior_relations"], 0)
        graph["edges"] = [edge for edge in graph["edges"] if edge["type"] == "contains"]
        incomplete = network_review(graph)
        for layer in ("business", "state", "rules"):
            self.assertEqual(incomplete[layer]["behavior_relations"], 0)
            self.assertTrue(incomplete[layer]["review_required"])
            self.assertTrue(incomplete[layer]["unconnected"])

    def test_bound_collision_retains_network_and_native_capture_targets(self):
        from test_concept_models import bound_fixture
        from bo_observer.concepts import bind_projection

        document, model, acceptance = bound_fixture()
        # An existing application's physical function happens to use the same
        # identity as the confirmed business action. Neither identity is rewritten.
        model = json.loads(json.dumps(model).replace("native:share", "share"))
        acceptance = json.loads(json.dumps(acceptance).replace("native:share", "share"))
        original = deepcopy(model)
        projection = bind_projection(document, model, acceptance=acceptance)
        by_id = {node["id"]: node for node in projection["nodes"]}
        self.assertEqual(by_id["concept-view:share"]["layer"], "business")
        self.assertEqual(by_id["share"]["source"], {"path": "sharing.py", "symbol": "share"})
        self.assertTrue(
            any(
                edge["from"] == "concept-view:share"
                and edge["to"] == "share"
                and edge.get("mapping_role") == "implements"
                for edge in projection["edges"]
            )
        )
        self.assertTrue(
            any(
                edge["from"] == "concept-view:share" and edge["type"] == "action_requests_event"
                for edge in projection["edges"]
            )
        )
        self.assertEqual(model, original)

    def test_rule_network_retains_shared_fact_paths_and_compact_recall(self):
        from bo_observer.concepts.network_review import network_review
        from bo_observer.workflow.concept_review import compact_report

        graph = {
            "nodes": [
                {"id": "fact", "layer": "rules", "concept_kind": "rule_input"},
                {"id": "a", "layer": "rules", "concept_kind": "rule_expression"},
                {"id": "b", "layer": "rules", "concept_kind": "rule_expression"},
            ],
            "edges": [{"from": "fact", "to": key, "type": "data"} for key in ("a", "b")],
        }
        report = network_review(graph)
        self.assertEqual(report["rules"]["components"], [["a", "b"]])
        self.assertFalse(report["rules"]["review_required"])
        compact = compact_report({"graph": graph})
        self.assertEqual(compact["networks"]["rules"]["component_count"], 1)
        self.assertNotIn("components", compact["networks"]["rules"])
        self.assertEqual(report["rules"]["components"], [["a", "b"]])


if __name__ == "__main__":
    unittest.main()
