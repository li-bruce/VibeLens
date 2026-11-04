"""One effect association may have several assertions, but never fewer obligations."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))

from bo_observer import concepts  # noqa: E402
from bo_observer.concepts.model import build  # noqa: E402
from bo_observer.concepts.registry import ConceptGraph  # noqa: E402
from bo_observer.concepts.runtime import runtime_errors  # noqa: E402
from bo_observer.control.selection import build_plan, validate_evidence  # noqa: E402
from bo_observer.graph.focus_graph import extract  # noqa: E402
from bo_observer.graph.relation_identity import relation_ids, relation_index  # noqa: E402
from bo_observer.web.bo_design import BODesign  # noqa: E402
from test_concept_models import approve, codes, effect_fixture, effect_observations  # noqa: E402

DECLARED = "transition-effect:grant:grant-share:store_grant"
EXPLICIT = "share-stores-grant"
TRANSITION = "transition:grant:grant-share"
EFFECT = "effect:grant:store_grant"


def associated_fixture():
    """Add a separately sourced crosslink without changing the declared effect."""
    document, model, acceptance = effect_fixture()
    document["crosslinks"].append(
        {
            "id": EXPLICIT,
            "from": TRANSITION,
            "to": EFFECT,
            "relation": "transition_has_effect",
            "label": "Persist the shared grant",
            "source_refs": ["U1"],
        }
    )
    document["confirmations"] = []
    approve(document)
    model["concepts"]["semantic_revision"] = concepts.assess(document)["semantic_revision"]
    model["concepts"]["crosslinks"][EXPLICIT] = ["store-grant"]
    return document, model, acceptance


class EffectProjectionTests(unittest.TestCase):
    def test_one_display_association_retains_both_assertions_and_source_records(self):
        document, _, _ = associated_fixture()
        data = build(document)
        edges = [edge for edge in data["graph"]["edges"] if edge["to"] == EFFECT]
        association = next(edge for edge in edges if edge["from"] == TRANSITION)
        self.assertEqual(len([edge for edge in edges if edge["from"] == TRANSITION]), 1)
        self.assertEqual(relation_ids(association), [DECLARED, EXPLICIT])
        original = association["equivalent_relations"][0]
        self.assertEqual(original["label"], "Persist the shared grant")
        self.assertEqual(original["source_refs"], ["U1"])
        self.assertEqual(association["source_refs"], ["U1"])
        self.assertEqual(data["records"][EXPLICIT]["relation"], "transition_has_effect")
        self.assertEqual(data["records"][DECLARED]["relation"], "has_effect")
        for ident in (DECLARED, EXPLICIT):
            self.assertEqual(data["dependencies"][ident], [TRANSITION, EFFECT])
            self.assertEqual(concepts.resolve(document, ident), ident)
        self.assertEqual(relation_index(data["graph"]["edges"])[EXPLICIT], association)

    def test_shared_effect_keeps_separate_transition_associations(self):
        document, _, _ = associated_fixture()
        document["state_models"][0]["transitions"][1]["effects"] = ["store_grant"]
        other = deepcopy(document["crosslinks"][-1])
        other.update(id="revoke-stores-grant", **{"from": "transition:grant:grant-revoke"})
        document["crosslinks"].append(other)
        edges = [edge for edge in build(document)["graph"]["edges"] if edge["type"] == "has_effect"]
        self.assertEqual(len(edges), 2)
        self.assertEqual({edge["from"] for edge in edges}, {TRANSITION, other["from"]})
        self.assertEqual({edge["to"] for edge in edges}, {EFFECT})
        self.assertEqual(
            {edge["equivalent_relations"][0]["id"] for edge in edges}, {EXPLICIT, other["id"]}
        )

    def test_several_explicit_assertions_preserve_every_original_identity(self):
        document, _, _ = associated_fixture()
        another = deepcopy(document["crosslinks"][-1])
        another.update(id="second-explanation", label="Store this recipient's access")
        document["crosslinks"].append(another)
        data = build(document)
        edge = relation_index(data["graph"]["edges"])[DECLARED]
        self.assertEqual(relation_ids(edge), [DECLARED, EXPLICIT, another["id"]])
        self.assertIn(another["id"], data["records"])
        self.assertEqual(data["dependencies"][another["id"]], [TRANSITION, EFFECT])

    def test_arguments_are_distinct_and_unknown_semantic_fields_are_rejected(self):
        document, _, _ = associated_fixture()
        document["crosslinks"][-1]["argument"] = "recipient_id"
        edges = build(document)["graph"]["edges"]
        association = [
            edge for edge in edges if edge["from"] == TRANSITION and edge["to"] == EFFECT
        ]
        self.assertEqual(len(association), 2)
        self.assertNotIn("equivalent_relations", association[0])
        self.assertEqual(association[1]["argument"], "recipient_id")
        document["crosslinks"][-1]["timing"] = "after_commit"
        with self.assertRaisesRegex(ValueError, "unknown=.*timing"):
            build(document)

    def test_ordinary_parallel_edges_and_extra_effect_semantics_remain_separate(self):
        registry = ConceptGraph()
        registry.relation("declared", "t", "e", "has_effect")
        registry.relation(
            "different-guard", "t", "e", "transition_has_effect", value={"negated": True}
        )
        registry.relation("other-role", "t", "e", "guard")
        registry.relation("another-role", "t", "e", "guard")
        self.assertEqual(
            [edge["id"] for edge in registry.edges],
            ["declared", "different-guard", "other-role", "another-role"],
        )

    def test_equivalence_rejects_ambiguous_ids_and_unrecognized_semantics(self):
        document, _, _ = associated_fixture()
        edge = relation_index(build(document)["graph"]["edges"])[DECLARED]
        for field, value in [
            ("argument", "other"),
            ("negated", True),
            ("timing", "later"),
            ("scope", "another"),
        ]:
            with self.subTest(field=field):
                invalid = deepcopy(edge)
                invalid["equivalent_relations"][0][field] = value
                with self.assertRaisesRegex(ValueError, "invalid equivalent"):
                    relation_index([invalid])
        collision = {"id": EXPLICIT, "from": "a", "to": "b", "type": "flow"}
        with self.assertRaisesRegex(ValueError, "ambiguous relation identity"):
            relation_index([edge, collision])
        with self.assertRaisesRegex(ValueError, "ambiguous relation identity"):
            relation_index([collision, edge])

    def test_binding_and_completion_obligations_survive_consolidation(self):
        document, model, acceptance = associated_fixture()
        valid = concepts.check_binding(document, model, acceptance=acceptance)
        self.assertTrue(valid["valid"], valid)
        missing_link = deepcopy(model)
        del missing_link["concepts"]["crosslinks"][EXPLICIT]
        self.assertIn(
            "unbound_cross_model_relation",
            codes(concepts.check_binding(document, missing_link, acceptance=acceptance)),
        )
        missing_completion = deepcopy(model)
        del missing_completion["concepts"]["transition_effects"]
        self.assertIn(
            "transition_effect_bindings_differ",
            codes(concepts.check_binding(document, missing_completion, acceptance=acceptance)),
        )
        document["state_models"][0]["transitions"][0]["effects"] = []
        with self.assertRaisesRegex(ValueError, "differs from its declared effects"):
            build(document)

    def test_runtime_projection_preserves_original_ids_without_rewriting_observations(self):
        document, model, acceptance = associated_fixture()
        original_model = deepcopy(model)
        observations = effect_observations()
        original_observations = deepcopy(observations)
        projected = concepts.bind_projection(document, model, acceptance=acceptance)
        edge = relation_index(projected["edges"])[EXPLICIT]
        self.assertEqual(edge["id"], DECLARED)
        self.assertIn(EXPLICIT, projected["index"])
        self.assertEqual(runtime_errors(document, model, observations), [])
        self.assertEqual(observations, original_observations)
        self.assertEqual(model, original_model)

    def test_focus_relation_filter_keeps_original_provenance_and_boundary(self):
        document, _, _ = associated_fixture()
        graph = {**concepts.assemble(document), "revision": "test"}
        focused = extract(graph, [TRANSITION], relations=["transition_has_effect"], depth=1)
        self.assertEqual([edge["id"] for edge in focused["edges"]], [DECLARED])
        self.assertIn(EFFECT, {node["id"] for node in focused["nodes"]})
        boundary_view = extract(graph, [TRANSITION], depth=0)
        boundary = next(item for item in boundary_view["boundaries"] if item["edge_id"] == DECLARED)
        self.assertEqual(relation_ids(boundary["relation"]), [DECLARED, EXPLICIT])
        self.assertEqual(boundary["relation"]["equivalent_relations"][0]["source_refs"], ["U1"])

    def test_control_plan_uses_one_display_edge_and_still_checks_its_inventory(self):
        document, model, acceptance = associated_fixture()
        model.update(revision="r1", project_id="effect-test")
        view = {
            "model": model,
            "concept_structure": concepts.bind_projection(document, model, acceptance=acceptance),
            "manifest": {"build_id": "test-build"},
            "events": [],
            "binding_status": {"status": "current"},
        }
        plan = build_plan(
            view, {"action": "view", "label": "Effect", "anchors": [TRANSITION, EFFECT], "depth": 0}
        )
        self.assertIn(DECLARED, plan["edge_ids"])
        self.assertNotIn(EXPLICIT, plan["edge_ids"])
        validate_evidence(plan, view)
        # Control plans are bound to the whole display inventory. Retained source
        # assertions participate in that hash; they cannot be dropped unnoticed.
        changed = deepcopy(view)
        relation_index(changed["concept_structure"]["edges"])[DECLARED].pop("equivalent_relations")
        with self.assertRaises(ValueError):
            validate_evidence(plan, changed)
        ambiguous = deepcopy(view)
        ambiguous["model"]["edges"].append(
            {"id": EXPLICIT, "from": "native:share", "to": "native:read", "type": "flow"}
        )
        with self.assertRaisesRegex(ValueError, "ambiguous relation identity"):
            build_plan(
                ambiguous,
                {"action": "view", "label": "Effect", "anchors": [TRANSITION], "depth": 0},
            )

    def test_saved_design_focus_and_preview_resolve_each_original_edge_id(self):
        document, _, _ = associated_fixture()
        (ROOT / ".validation").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            source = root / "discovery.json"
            source.write_text(json.dumps(document), encoding="utf-8")
            before = source.read_bytes()
            design = BODesign(root)
            for ident in (DECLARED, EXPLICIT):
                focus = design.focus([ident])
                self.assertEqual(set(focus["nodes"]), {TRANSITION, EFFECT})
                preview = design.preview("http://127.0.0.1:8830/graph", nodes=[ident], view="state")
                matches = [
                    edge
                    for edge in preview["focus"]["edges"]
                    if edge["from"] == TRANSITION and edge["to"] == EFFECT
                ]
                self.assertEqual(len(matches), 1)
                self.assertEqual(relation_ids(matches[0]), [DECLARED, EXPLICIT])
            self.assertEqual(source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
