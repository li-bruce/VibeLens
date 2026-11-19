"""Boundary cases for finite representations and canonical policy references.

Hand-derived counts and reordered representations are independent expectations.
Nothing in these tests invokes a native application or claims model exploration.
"""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.behavior import assess
from bo_observer.behavior.domains import load_domains
from bo_observer.behavior.diagnostics import ContractError
from bo_observer.behavior.expressions import Expressions, UNKNOWN, known_value


def record(ident, kind, **fields):
    return {"id": ident, "type": kind, "source_refs": ["U1"], **fields}


def lit(value, domain="flag"):
    return {"op": "literal", "value": value, "domain": domain}


def expr(op, *args):
    return {"op": op, "args": list(args)}


def domains(*extra):
    return load_domains([record("flag", "boolean"), record("text", "string"), *extra])


class DomainRepresentationTests(unittest.TestCase):
    def test_sequence_and_set_counts_preserve_distinct_semantics(self):
        ds = domains(
            record(
                "seq", "sequence", element_domain="flag", max_items=2, bound_origin="analysis_bound"
            ),
            record("set", "set", element_domain="flag"),
        )
        self.assertEqual(ds["seq"].finite_capability()["cardinality"], 7)
        self.assertEqual(ds["set"].finite_capability()["cardinality"], 4)
        self.assertTrue(ds["seq"].accepts([True, True]))
        self.assertFalse(ds["set"].accepts([True, True]))
        self.assertEqual(ds["set"].value_key([True, False]), ds["set"].value_key([False, True]))
        self.assertNotEqual(ds["seq"].value_key([True, False]), ds["seq"].value_key([False, True]))

    def test_bounded_length_does_not_bound_payload(self):
        ds = domains(
            record(
                "queue",
                "sequence",
                element_domain="text",
                max_items=2,
                bound_origin="analysis_bound",
            )
        )
        self.assertEqual(ds["queue"].finite_capability()["reason"], "unbounded_element")

    def test_unbounded_sequence_is_not_a_finite_set(self):
        ds = domains(record("queue", "sequence", element_domain="flag"))
        self.assertEqual(ds["queue"].finite_capability()["reason"], "unbounded_length")

    def test_empty_collection_is_finite_even_over_unbounded_payload(self):
        ds = domains(
            record(
                "queue",
                "sequence",
                element_domain="text",
                max_items=0,
                bound_origin="application_limit",
            )
        )
        self.assertEqual(ds["queue"].finite_capability()["cardinality"], 1)

    def test_map_counts_and_key_identity_are_not_json_object_coercions(self):
        ds = domains(
            record("keys", "enum", values=[True, 1]),
            record("map", "map", element_domain="flag", key_domain="keys"),
        )
        mapping = ds["map"]
        entries = [{"key": True, "value": False}, {"key": 1, "value": True}]
        self.assertTrue(mapping.accepts(entries))
        self.assertFalse(mapping.accepts([entries[0], entries[0]]))
        self.assertFalse(mapping.accepts({"true": False}))
        self.assertEqual(mapping.finite_capability()["cardinality"], 9)
        self.assertEqual(mapping.value_key(entries), mapping.value_key(list(reversed(entries))))

    def test_map_with_unbounded_keys_stays_unbounded(self):
        ds = domains(
            record(
                "map",
                "map",
                element_domain="flag",
                key_domain="text",
                max_items=1,
                bound_origin="analysis_bound",
            )
        )
        self.assertEqual(ds["map"].finite_capability()["reason"], "unbounded_key")

    def test_duplicate_nested_sets_do_not_evade_uniqueness_with_order(self):
        ds = domains(
            record("inner", "set", element_domain="flag"),
            record("outer", "set", element_domain="inner"),
        )
        self.assertFalse(ds["outer"].accepts([[True, False], [False, True]]))

    def test_reversed_declaration_order_resolves_but_cycles_fail(self):
        ds = domains(
            record("outer", "set", element_domain="inner"),
            record("inner", "set", element_domain="flag"),
        )
        self.assertEqual(ds["outer"].finite_capability()["cardinality"], 16)
        with self.assertRaises(ContractError) as error:
            domains(record("a", "set", element_domain="b"), record("b", "set", element_domain="a"))
        self.assertEqual(error.exception.diagnostic.code, "domain_cycle")

    def test_unknown_dependency_and_missing_bound_origin_fail(self):
        for value, code in [
            (record("s", "set", element_domain="missing"), "unknown_domain"),
            (record("s", "set", element_domain="flag", max_items=2), "bound_origin_required"),
        ]:
            with self.assertRaises(ContractError) as error:
                domains(value)
            self.assertEqual(error.exception.diagnostic.code, code)

    def test_live_instance_limit_does_not_bound_identity_history(self):
        ds = domains(
            record(
                "id",
                "identity",
                object_ref="object:grant",
                identity_policy="monotonic",
                max_live=2,
                bound_origin="application_limit",
            )
        )
        self.assertEqual(ds["id"].finite_capability()["reason"], "unbounded_identity_history")

    def test_fixed_pool_bounds_values_without_merging_object_domains(self):
        ds = domains(
            record(
                "id",
                "identity",
                object_ref="object:grant",
                identity_policy="fixed_pool",
                values=["1", "2"],
            )
        )
        self.assertEqual(ds["id"].finite_capability()["cardinality"], 2)
        self.assertTrue(ds["id"].accepts("1"))
        self.assertFalse(ds["id"].accepts(1))
        self.assertFalse(ds["id"].accepts("3"))

    def test_huge_finite_size_is_not_materialized_or_declared_unbounded(self):
        ds = domains(
            record("n", "integer", min=0, max=9007199254740991, bound_origin="analysis_bound"),
            record("s", "set", element_domain="n"),
        )
        result = ds["s"].finite_capability()
        self.assertTrue(result["supported"])
        self.assertIsNone(result["cardinality"])

    def test_numeric_map_keys_are_values_not_json_lexical_spellings(self):
        ds = domains(
            record("number", "number"),
            record("map", "map", element_domain="flag", key_domain="number"),
        )
        self.assertFalse(
            ds["map"].accepts([{"key": 1, "value": True}, {"key": 1.0, "value": False}])
        )

    def test_numeric_equality_does_not_create_a_false_initial_contradiction(self):
        checker = Expressions(domains(record("number", "number")), {})
        condition = expr("eq", lit(1, "number"), lit(1.0, "number"))
        checker.expect_boolean(condition, "/initial")
        self.assertTrue(known_value(condition, {}, checker))

    def test_finite_count_includes_the_exact_portable_boundary(self):
        ds = domains(
            record(
                "bits",
                "sequence",
                element_domain="flag",
                max_items=52,
                bound_origin="analysis_bound",
            )
        )
        self.assertEqual(ds["bits"].finite_capability()["cardinality"], 9007199254740991)


class CollectionExpressionTests(unittest.TestCase):
    def setUp(self):
        self.domains = domains(
            record("n", "integer"),
            record("set", "set", element_domain="flag"),
            record(
                "seq", "sequence", element_domain="flag", max_items=2, bound_origin="analysis_bound"
            ),
            record("map", "map", element_domain="flag", key_domain="flag"),
        )
        self.checker = Expressions(self.domains, {})

    def checked_value(self, expression):
        self.checker.check(expression, "/test")
        return known_value(expression, {}, self.checker)

    def test_equality_uses_collection_semantics(self):
        self.assertTrue(
            self.checked_value(expr("eq", lit([True, False], "set"), lit([False, True], "set")))
        )
        self.assertFalse(
            self.checked_value(expr("eq", lit([True, False], "seq"), lit([False, True], "seq")))
        )

    def test_membership_and_total_lookup(self):
        self.assertTrue(self.checked_value(expr("member", lit(False), lit([True, False], "set"))))
        self.assertFalse(
            self.checked_value(expr("select", lit([True], "seq"), lit(8, "n"), lit(False)))
        )
        self.assertTrue(
            self.checked_value(
                expr("select", lit([{"key": False, "value": True}], "map"), lit(False), lit(False))
            )
        )

    def test_lookup_type_and_named_container_mismatch_fail(self):
        for value in (
            expr("select", lit([True], "seq"), lit(True), lit(False)),
            expr("eq", lit([True], "seq"), lit([True], "set")),
        ):
            with self.assertRaises(ContractError):
                self.checker.check(value, "/test")

    def test_quantifier_is_finite_typed_and_not_falsely_evaluated(self):
        value = {
            "op": "forall",
            "domain": "flag",
            "bind": "candidate",
            "body": {"op": "param", "id": "candidate"},
        }
        self.checker.expect_boolean(value, "/test")
        self.assertIs(known_value(value, {}, self.checker), UNKNOWN)
        value["domain"] = "text"
        with self.assertRaises(ContractError) as error:
            self.checker.check(value, "/test")
        self.assertEqual(error.exception.diagnostic.code, "unsupported_quantifier_domain")

    def test_quantifier_cannot_shadow_action_parameter(self):
        value = {
            "op": "exists",
            "domain": "flag",
            "bind": "candidate",
            "body": {"op": "param", "id": "candidate"},
        }
        with self.assertRaises(ContractError) as error:
            self.checker.check(value, "/test", parameters={"candidate": "flag"})
        self.assertEqual(error.exception.diagnostic.code, "parameter_shadowing")


class PolicyReferenceTests(unittest.TestCase):
    def setUp(self):
        folder = ROOT / "tests/fixtures/behavior-contracts"
        self.contract, self.discovery = (
            json.loads((folder / name).read_text(encoding="utf-8"))
            for name in ("scalar.behavior.json", "forest.discovery.json")
        )
        # A standalone Boolean-input decision has no opaque native predicate.
        self.discovery["policy"]["inputs"]["confirmed"] = "boolean"
        self.discovery["policy"]["nodes"].append(
            {"id": "confirmed", "op": "input", "name": "confirmed", "source_refs": ["U1"]}
        )
        self.discovery["policy"]["operations"].append(
            {"id": "confirmation", "root": "confirmed", "source_refs": ["U1"]}
        )
        self.contract["scope"]["model_refs"].append("policy-operation:confirmation")
        self.contract["actions"][0]["enabled"] = {
            "op": "policy_ref",
            "id": "policy-operation:confirmation",
            "bindings": {"confirmed": lit(True)},
        }

    def result(self):
        return assess(self.contract, self.discovery)

    def test_reference_uses_canonical_definition_and_preserves_inputs(self):
        before = deepcopy((self.contract, self.discovery))
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertEqual(
            result["policy_references"]["policy-operation:confirmation"]["input_types"],
            {"confirmed": "boolean"},
        )
        self.assertEqual((self.contract, self.discovery), before)
        self.assertEqual(result["analysis"], "not_run")
        self.assertFalse(result["definition_capabilities"]["finite_export"]["runner_available"])

    def test_missing_extra_and_wrong_type_bindings_fail(self):
        for bindings, code in [
            ({}, "policy_bindings"),
            ({"confirmed": lit(True), "extra": lit(True)}, "policy_bindings"),
            ({"confirmed": lit("active", "status")}, "policy_binding_type"),
        ]:
            self.contract["actions"][0]["enabled"]["bindings"] = bindings
            result = self.result()
            self.assertFalse(result["valid"], result)
            self.assertEqual(result["errors"][0]["code"], code, result)

    def test_policy_outside_scope_and_alias_do_not_bind(self):
        self.contract["scope"]["model_refs"].pop()
        self.assertEqual(self.result()["errors"][0]["code"], "policy_scope")
        self.contract["actions"][0]["enabled"]["id"] = "confirmation"
        self.assertEqual(self.result()["errors"][0]["code"], "unknown_reference")

    def test_nested_policy_bindings_preserve_reads(self):
        self.contract["actions"][0]["enabled"]["bindings"]["confirmed"] = expr(
            "eq", {"op": "var", "id": "archive-status", "phase": "before"}, lit("active", "status")
        )
        self.assertEqual(self.result()["errors"][0]["code"], "undeclared_read")
        self.contract["actions"][0]["reads"].append("archive-status")
        self.assertTrue(self.result()["valid"], self.result())

    def test_identity_domain_owner_must_exist_and_be_selected(self):
        self.contract["domains"].append(
            record(
                "ident",
                "identity",
                identity_policy="fixed_pool",
                object_ref="object:missing",
                values=["1"],
            )
        )
        self.assertEqual(self.result()["errors"][0]["code"], "unknown_reference")

    def test_collection_domain_and_expression_pass_the_public_json_boundary(self):
        self.contract["domains"].append(record("flags", "set", element_domain="flag"))
        self.contract["actions"][0]["enabled"] = expr("member", lit(True), lit([True], "flags"))
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["domain_capabilities"]["flags"]["cardinality"], 4)
        self.contract["actions"][0]["enabled"]["args"][1]["value"] = [True, True]
        self.assertEqual(self.result()["errors"][0]["code"], "literal_type")

    def test_unbounded_native_predicate_is_never_interpreted_by_its_name(self):
        self.contract["domains"].append(record("text", "string"))
        self.contract["scope"]["model_refs"].append("policy-operation:manage")
        self.contract["actions"][0]["enabled"] = {
            "op": "policy_ref",
            "id": "policy-operation:manage",
            "bindings": {"actor": lit("1", "text"), "owner": lit("1", "text")},
        }
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertEqual(
            result["policy_references"]["policy-operation:manage"]["opaque_predicates"],
            ["same_identity"],
        )
        self.assertEqual(result["analysis"], "not_run")

    def test_strict_json_envelope_rejects_invalid_collection_bound(self):
        self.contract["domains"].append(
            record(
                "flags", "set", element_domain="flag", max_items=-1, bound_origin="analysis_bound"
            )
        )
        self.assertEqual(self.result()["errors"][0]["code"], "schema_minimum")


if __name__ == "__main__":
    unittest.main()
