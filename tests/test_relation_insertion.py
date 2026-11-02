"""Construction-time relation decisions preserve physical facts and original IDs."""

from copy import deepcopy
from itertools import permutations
import json
from pathlib import Path
import random
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))

from bo_observer.graph.relations import RelationIndex


CONTEXT = {
    "scope": "sharing",
    "revision": "v1",
    "basis": "design:user-1",
    "bindings": {"project": "current"},
    "conditions": {"enabled": True},
}


def rules(*, transitive=False):
    """Only the conceptual summary, never the execution edges, is composable."""
    return {
        "schema": "bo-relation-rules/v1",
        "definitions": [
            {
                "id": "implements",
                "mode": "direct",
                "match": {"type": "maps", "origin": "implementation"},
            },
            {"id": "reads", "mode": "direct", "match": {"type": "data", "origin": "source"}},
            {
                "id": "uses",
                "mode": "summary",
                "transitive": transitive,
                "match": {
                    "type": "maps",
                    "origin": "relation-summary",
                    "semantic_relation": "uses",
                },
            },
        ],
        "compositions": [
            {"id": "implementation-reads", "result": "uses", "path": ["implements", "reads"]}
        ],
    }


def entry(ident, start, end, relation="uses", **kw):
    edge = {"id": ident, "from": start, "to": end, "type": "maps", "evidence": "declaration:user-1"}
    if relation == "uses":
        edge.update(origin="relation-summary", semantic_relation="uses")
    elif relation == "implements":
        edge.update(origin="implementation")
    elif relation == "reads":
        edge.update(type="data", origin="source")
    value = {"edge": edge, "context": deepcopy(CONTEXT)}
    if relation:
        value["relation"] = relation
    value.update(kw)
    return value


def triangle():
    return [
        entry("ab", "a", "b", "implements"),
        entry("bc", "b", "c", "reads"),
        entry("ac", "a", "c"),
    ]


def insert_all(index, entries):
    return index.apply([{"op": "insert", "entry": value} for value in entries])


class InsertionTests(unittest.TestCase):
    def index(self, **kw):
        return RelationIndex(["a", "b", "c", "d", "e"], rules(), **kw)

    def test_idempotence_and_conflicting_id_are_atomic(self):
        index = self.index()
        index.insert(triangle()[0])
        before = index.export()
        result = index.insert(triangle()[0])
        self.assertEqual(result["actions"][0]["action"], "idempotent")
        self.assertEqual(index.export(), before)
        changed = triangle()[0]
        changed["edge"]["label"] = "Different display name"
        with self.assertRaisesRegex(ValueError, "Conflicting relation ID"):
            index.insert(changed)
        self.assertEqual(index.export(), before)

    def test_new_witness_revisits_existing_summary_and_remove_restores_it(self):
        index = self.index()
        index.insert(triangle()[2])
        self.assertEqual(index.decision("ac")["status"], "retained")
        insert_all(index, triangle()[:2])
        self.assertEqual(index.decision("ac")["leaf_path"], ["ab", "bc"])
        self.assertEqual([e["id"] for e in index.edges], ["ab", "bc"])
        result = index.remove("bc")
        self.assertIn("ac", result["restored"])
        self.assertEqual(index.decision("ac")["status"], "retained")
        self.assertEqual(len(index.export()["entries"]), 2)

    def test_insertion_order_does_not_change_path_decisions(self):
        for values in permutations(triangle()):
            index = self.index()
            for value in values:
                index.insert(value)
            self.assertEqual(index.decision("ac")["leaf_path"], ["ab", "bc"])
            self.assertEqual(set(index.export()["canonical_edges"]), {"ab", "bc"})

    def test_explicit_identical_definition_is_an_alias_with_original_id(self):
        index = self.index()
        first = entry("ab", "a", "b", "implements", definition_key="binding-1")
        alias = deepcopy(first)
        alias["edge"].update(id="alias", label="Human explanation")
        insert_all(index, [first, alias])
        self.assertEqual(
            index.decision("alias"),
            {"status": "duplicate", "reason": "same_definition", "duplicate_of": "ab"},
        )
        self.assertEqual(len(index.export()["entries"]), 2)
        self.assertEqual(index.edges[0]["id"], "ab")
        index.remove("ab")
        self.assertEqual(index.edges[0]["id"], "alias")
        self.assertEqual(index.decision("alias")["status"], "retained")

    def test_same_endpoints_do_not_establish_duplicate_identity(self):
        index = self.index()
        values = [entry("one", "a", "b", "implements"), entry("two", "a", "b", "implements")]
        insert_all(index, values)
        self.assertEqual(len(index.edges), 2)
        for key in ("callsite", "source", "trace", "event_id", "parameters", "guard", "evidence"):
            with self.subTest(key=key):
                index = self.index()
                first = entry("one", "a", "b", "implements", definition_key="same")
                second = deepcopy(first)
                second["edge"].update(id="two", **{key: "different"})
                insert_all(index, [first, second])
                self.assertEqual(len(index.edges), 2)

    def test_each_context_dimension_must_match_exactly(self):
        for field, value in (
            ("scope", "other"),
            ("revision", "v2"),
            ("basis", "runtime:1"),
            ("bindings", {"project": "other"}),
            ("conditions", {"enabled": False}),
        ):
            with self.subTest(field=field):
                index = self.index()
                values = triangle()
                values[2]["context"][field] = value
                insert_all(index, values)
                self.assertEqual(index.decision("ac")["status"], "retained")
        index = self.index()
        values = triangle()
        values[0]["context"]["conditions"] = {"enabled": 1}
        insert_all(index, values)
        self.assertEqual(index.decision("ac")["status"], "retained")

    def test_missing_and_unknown_context_remain_visible(self):
        for value in (None, {}, {**CONTEXT, "basis": None}):
            index = self.index()
            values = triangle()
            values[2]["context"] = value
            insert_all(index, values)
            self.assertEqual(index.decision("ac")["reason"], "unknown_context")

    def test_unknown_meanings_and_physical_relations_are_never_contracted(self):
        for kind in (
            "flow",
            "data",
            "guard",
            "resource",
            "join",
            "contains",
            "maps",
            "call",
            "transition",
        ):
            with self.subTest(kind=kind):
                index = self.index()
                values = [
                    entry("ab", "a", "b", None),
                    entry("bc", "b", "c", None),
                    entry("ac", "a", "c", None),
                ]
                for value in values:
                    value["edge"]["type"] = kind
                insert_all(index, values)
                self.assertEqual(len(index.edges), 3)
        index = self.index()
        insert_all(
            index,
            [
                entry("ab", "a", "b", "implements"),
                entry("bc", "b", "c", "implements"),
                entry("ac", "a", "c", "implements"),
            ],
        )
        self.assertEqual(len(index.edges), 3)

    def test_wrong_composition_order_or_unregistered_types_do_not_match(self):
        index = self.index()
        values = triangle()
        values[0] = entry("ab", "a", "b", "reads")
        values[1] = entry("bc", "b", "c", "implements")
        insert_all(index, values)
        self.assertEqual(index.decision("ac")["reason"], "no_equivalent_path")

    def test_transitive_query_cannot_mix_other_relation_types(self):
        spec = rules(transitive=True)
        spec["compositions"] = []
        index = RelationIndex(["a", "b", "c"], spec)
        insert_all(index, triangle())
        self.assertEqual(index.decision("ac")["status"], "retained")
        index = RelationIndex(["a", "b", "c"], spec)
        insert_all(index, [entry("ab", "a", "b"), entry("bc", "b", "c"), entry("ac", "a", "c")])
        self.assertEqual(index.decision("ac")["leaf_path"], ["ab", "bc"])

    def test_independent_runtime_and_source_evidence_protects_summaries(self):
        for key in (
            "source",
            "callsite",
            "call_id",
            "trace",
            "span_id",
            "event_id",
            "event_ids",
            "witnesses",
            "observed",
            "independent",
        ):
            with self.subTest(key=key):
                index = self.index()
                values = triangle()
                (values[2] if key == "independent" else values[2]["edge"])[key] = (
                    True if key in {"observed", "independent"} else "witness-1"
                )
                insert_all(index, values)
                self.assertEqual(index.decision("ac")["reason"], "independent_evidence")

    def test_source_change_restores_summary_and_cas_prevents_lost_updates(self):
        index = self.index()
        insert_all(index, triangle())
        revision = index.revision
        changed = triangle()[1]
        changed["context"]["revision"] = "v2"
        self.assertIn("ac", index.update("bc", changed, expected_revision=revision)["restored"])
        before = index.export()
        with self.assertRaisesRegex(ValueError, "revision conflict"):
            index.remove("ab", expected_revision=revision)
        self.assertEqual(index.export(), before)

    def test_cycle_is_retained_instead_of_global_dag_reduction(self):
        index = self.index()
        insert_all(index, triangle() + [entry("ca", "c", "a", "implements")])
        self.assertEqual(index.decision("ac")["reason"], "cyclic_relation_family")
        self.assertEqual(len(index.edges), 4)

    def test_rule_contract_rejects_unsafe_and_undefined_semantics(self):
        invalid = []
        value = rules()
        value["definitions"][0]["transitive"] = True
        invalid.append(value)
        value = rules()
        value["definitions"][2]["match"] = {"type": "call"}
        invalid.append(value)
        value = rules()
        value["compositions"][0]["path"] = ["uses", "reads"]
        invalid.append(value)
        value = rules()
        value["compositions"][0]["path"] = ["absent", "reads"]
        invalid.append(value)
        value = rules()
        value["compositions"][0]["result"] = "reads"
        invalid.append(value)
        for value in invalid:
            with self.assertRaises(ValueError):
                RelationIndex(["a", "b", "c"], value)
        for key in ("guard", "event", "units", "code_relation", "data_relation"):
            index = self.index()
            value = triangle()[2]
            value["edge"][key] = "physical"
            with self.assertRaises(ValueError):
                index.insert(value)

    def test_nested_compositions_export_only_real_retained_witnesses(self):
        spec = rules()
        spec["definitions"].append(
            {
                "id": "indirect",
                "mode": "summary",
                "match": {
                    "type": "maps",
                    "origin": "relation-summary",
                    "semantic_relation": "indirect",
                },
            }
        )
        spec["compositions"].append(
            {"id": "nested", "result": "indirect", "path": ["uses", "reads"]}
        )
        index = RelationIndex(["a", "b", "c", "d"], spec)
        outer = entry("ad", "a", "d")
        outer["relation"] = outer["edge"]["semantic_relation"] = "indirect"
        insert_all(index, triangle() + [entry("cd", "c", "d", "reads"), outer])
        self.assertEqual(index.decision("ad")["leaf_path"], ["ab", "bc", "cd"])
        self.assertTrue(
            set(index.decision("ad")["leaf_path"]) <= set(index.export()["canonical_edges"])
        )

    def test_budget_exhaustion_retains_instead_of_guessing(self):
        for limits in ({"max_work": 0}, {"max_candidates": 0}):
            index = self.index(limits=limits)
            insert_all(index, triangle())
            self.assertEqual(index.decision("ac")["reason"], "search_budget")
            self.assertEqual(len(index.edges), 3)

    def test_invalid_batch_and_node_removal_rollback_all_changes(self):
        index = self.index()
        index.insert(triangle()[0])
        before = index.export()
        for operations, nodes in (
            ([{"op": "insert", "entry": triangle()[1]}, {"op": "remove", "id": "absent"}], None),
            ([], ["a", "c"]),
        ):
            with self.assertRaises(ValueError):
                index.apply(operations, nodes=nodes)
            self.assertEqual(index.export(), before)
        index.apply([{"op": "remove", "id": "ab"}], nodes=["a", "c"])
        self.assertEqual(index.edges, [])

    def test_json_persistence_recomputes_and_rejects_altered_claims_or_decisions(self):
        index = self.index()
        insert_all(index, triangle())
        saved = json.loads(json.dumps(index.export()))
        self.assertEqual(RelationIndex.restore(saved).export(), saved)
        for field in ("decisions", "canonical_edges", "revision", "entries"):
            value = deepcopy(saved)
            if field == "decisions":
                value[field]["ac"]["path"] = ["bc", "ab"]
            elif field == "canonical_edges":
                value[field].append("ac")
            elif field == "revision":
                value[field] = "altered"
            else:
                value[field][0]["edge"]["label"] = "Changed outside insertion"
            with self.assertRaises(ValueError):
                RelationIndex.restore(value)

    def test_strict_portable_json_and_defensive_copies(self):
        index = self.index()
        for value in (float("nan"), 9007199254740992, {1: "not a string key"}):
            item = triangle()[0]
            item["edge"]["value"] = value
            with self.assertRaises((ValueError, TypeError)):
                index.insert(item)
        item = triangle()[0]
        index.insert(item)
        item["edge"]["from"] = "bad"
        edges = index.edges
        edges[0]["from"] = "bad"
        saved = index.export()
        saved["entries"][0]["edge"]["from"] = "bad"
        self.assertEqual(index.edges[0]["from"], "a")

    def test_large_physical_graph_does_not_pay_for_path_queries(self):
        count = 3000
        index = RelationIndex([str(i) for i in range(count + 1)])
        values = [entry("e" + str(i), str(i), str(i + 1), None) for i in range(count)]
        started = time.perf_counter()
        insert_all(index, values)
        elapsed = time.perf_counter() - started
        self.assertEqual(len(index.edges), count)
        print(
            json.dumps(
                {
                    "measurement": "physical_insert_batch",
                    "edges": count,
                    "seconds": round(elapsed, 4),
                }
            )
        )

    def test_randomized_transitive_dag_keeps_reachability_and_leaf_proofs(self):
        spec = rules(transitive=True)
        spec["compositions"] = []
        values = [entry(f"e{i}-{j}", str(i), str(j)) for i in range(10) for j in range(i + 1, 10)]
        chain = {f"e{i}-{i + 1}" for i in range(9)}
        for seed in range(6):
            shuffled = deepcopy(values)
            random.Random(seed).shuffle(shuffled)
            index = RelationIndex([str(i) for i in range(10)], spec)
            for item in shuffled:
                index.insert(item)
            self.assertEqual(set(index.export()["canonical_edges"]), chain)
            for i in range(10):
                for j in range(i + 2, 10):
                    self.assertEqual(
                        index.decision(f"e{i}-{j}")["leaf_path"],
                        [f"e{k}-{k + 1}" for k in range(i, j)],
                    )
            self.assertEqual(RelationIndex.restore(index.export()).export(), index.export())

    def test_duplicate_context_changes_and_distinct_parameters_retain_both_claims(self):
        for key in CONTEXT:
            index = self.index()
            first = entry("ab", "a", "b", "implements", definition_key="binding")
            alias = deepcopy(first)
            alias["edge"]["id"] = "other"
            alias["context"][key] = (
                "changed" if key in {"scope", "revision", "basis"} else {"changed": True}
            )
            insert_all(index, [first, alias])
            self.assertEqual(len(index.edges), 2)

    def test_invalid_configuration_and_nested_non_json_values_fail_closed(self):
        for limits in (
            [],
            {"max_work": -1},
            {"max_work": True},
            {"max_work": 10_000_001},
            {"unknown": 0},
        ):
            with self.assertRaises(ValueError):
                self.index(limits=limits)
        for payload in ({"nested": (1, 2)}, {"nested": {1, 2}}, {"nested": (9007199254740992,)}):
            index = self.index()
            item = triangle()[0]
            item["edge"]["extra"] = payload
            with self.assertRaises(ValueError):
                index.insert(item)
        spec = rules()
        spec["compositions"][0]["id"] = "transitive:uses"
        with self.assertRaises(ValueError):
            RelationIndex(["a", "b", "c"], spec)

    def test_shared_composition_dependency_is_not_mistaken_for_a_cycle(self):
        spec = rules()
        for ident in ("outer", "other"):
            spec["definitions"].append(
                {
                    "id": ident,
                    "mode": "summary",
                    "match": {
                        "type": "maps",
                        "origin": "relation-summary",
                        "semantic_relation": ident,
                    },
                }
            )
            spec["compositions"].append(
                {"id": ident + "-rule", "result": ident, "path": ["uses", "reads"]}
            )
        RelationIndex(["a", "b", "c"], spec)


if __name__ == "__main__":
    unittest.main()
