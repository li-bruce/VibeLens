"""Independent expectations for the first portable behavior-contract slice.

These are definition checks. No test equates a passing definition with a correctly
instrumented implementation or an explored finite model.
"""

from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.behavior import assess
from bo_observer.behavior.domains import load_domains
from bo_observer.workflow.behavior_cli import main


def literal(value, domain="flag"):
    return {"op": "literal", "domain": domain, "value": value}


def variable(ident="grant-status", phase="before"):
    return {"op": "var", "id": ident, "phase": phase}


def operation(op, *args):
    return {"op": op, "args": list(args)}


def fixture():
    """Load pinned, source-free wire examples with two independently owned states."""
    folder = ROOT / "tests/fixtures/behavior-contracts"
    return tuple(
        json.loads((folder / name).read_text(encoding="utf-8"))
        for name in ("scalar.behavior.json", "forest.discovery.json")
    )


class BehaviorContractTests(unittest.TestCase):
    def setUp(self):
        self.contract, self.discovery = fixture()

    def result(self):
        return assess(self.contract, self.discovery)

    def reject(self, code, path=None):
        result = self.result()
        self.assertFalse(result["valid"], result)
        self.assertIn(code, {error["code"] for error in result["errors"]}, result)
        if path:
            self.assertTrue(any(error["path"] == path for error in result["errors"]), result)

    def test_source_free_contract_keeps_two_state_owners_and_no_runtime_claim(self):
        before = deepcopy((self.contract, self.discovery))
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["variables"], ["archive-status", "grant-status"])
        self.assertEqual(result["binding"], "not_checked")
        self.assertEqual(result["analysis"], "not_run")
        self.assertEqual((self.contract, self.discovery), before)

    def test_unknown_version_and_field_are_strict(self):
        self.contract["schema"] = "bo-behavior/v99"
        self.reject("schema_const", "/schema")
        self.contract, _ = fixture()
        self.contract["silent_default"] = True
        self.reject("schema_additionalProperties", "/")

    def test_unknown_and_wrong_kind_refs_are_not_aliases(self):
        self.contract["scope"]["model_refs"][0] = "grant"
        self.reject("unknown_reference", "/scope/model_refs/0")
        self.contract["scope"]["model_refs"][0] = "fact:active-grant"
        self.reject("reference_kind")

    def test_native_definition_errors_are_not_overridden(self):
        self.discovery["state_models"][1]["transitions"][0]["dest"] = "missing"
        self.reject("invalid_concept_definition", "/discovery")

    def test_foreign_project_is_rejected(self):
        self.contract["project_id"] = "another-project"
        self.reject("project_mismatch")

    def test_duplicate_ids_and_duplicate_variable_bindings_fail(self):
        self.contract["domains"].append(deepcopy(self.contract["domains"][0]))
        self.reject("duplicate_id")
        self.contract, _ = fixture()
        self.contract["variables"][1]["concept_ref"] = "state-model:grant"
        self.reject("duplicate_variable_binding")

    def test_same_state_labels_do_not_permit_wrong_model_ownership(self):
        self.contract["variables"][1]["owner"] = "state-model:grant"
        self.reject("variable_owner")

    def test_state_domain_cannot_remove_or_add_canonical_states(self):
        self.contract["domains"][0]["values"].append("deleted")
        self.reject("state_domain_mismatch")

    def test_written_and_unchanged_variables_partition_the_scope(self):
        action = self.contract["actions"][0]
        action["unchanged"] = []
        self.reject("frame_partition")
        action["unchanged"] = ["grant-status", "archive-status"]
        self.reject("frame_partition")

    def test_update_cannot_write_the_other_model_implicitly(self):
        action = self.contract["actions"][0]
        action["writes"].append("archive-status")
        action["unchanged"] = []
        action["updates"]["archive-status"] = literal("active", "status")
        self.reject("writer_outside_scope")

    def test_transition_keeps_model_qualified_identity(self):
        self.contract["actions"][0]["transition_ref"] = "transition:archive:grant-share"
        self.reject("transition_owner")

    def test_transition_update_cannot_be_redeclared(self):
        self.contract["actions"][0]["updates"]["grant-status"] = literal(True)
        self.reject("duplicate_transition_update")

    def test_arithmetic_and_boolean_composition_enforce_operand_types(self):
        self.contract["actions"][0]["enabled"] = operation("all", variable())
        self.reject("expression_type")

    def test_reads_include_guards_and_updates(self):
        self.contract["actions"][0]["reads"] = []
        self.reject("undeclared_read")

    def test_update_has_pre_state_semantics(self):
        self.contract["actions"][0]["enabled"] = operation(
            "eq", variable("grant-status", "after"), literal("active", "status")
        )
        self.reject("after_state_not_allowed")

    def test_only_transition_properties_read_after_state(self):
        self.contract["properties"][0]["kind"] = "state_invariant"
        self.contract["properties"][0]["action_refs"] = []
        self.reject("after_state_not_allowed")

    def test_literal_type_does_not_coerce_boolean_or_string(self):
        self.contract["actions"][0]["enabled"] = literal(1)
        self.reject("literal_type")

    def test_invalid_operator_and_arity_fail_before_evaluation(self):
        self.contract["actions"][0]["enabled"] = {"op": "python", "code": "True"}
        self.reject("schema_oneOf")
        self.contract["actions"][0]["enabled"] = operation("eq", literal(True))
        self.reject("schema_oneOf")

    def test_missing_parameter_is_not_unknown_truth(self):
        self.contract["actions"][0]["enabled"] = {"op": "param", "id": "missing"}
        self.reject("unknown_parameter")

    def test_missing_property_action_and_source_are_reported(self):
        self.contract["properties"][0]["action_refs"] = ["missing"]
        self.reject("unknown_action")
        self.contract, _ = fixture()
        self.contract["properties"][0]["source_refs"] = ["missing"]
        self.reject("unknown_source")

    def test_unresolved_scope_is_valid_but_not_silently_complete(self):
        self.contract["scope"]["unresolved"] = ["Confirm retry behavior"]
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["status"], "unresolved")

    def test_finite_domain_is_separate_from_finite_system(self):
        self.contract["domains"].extend(
            [
                {"id": "counter", "type": "integer", "source_refs": ["U1"]},
                {"id": "identity", "type": "string", "source_refs": ["U1"]},
                {
                    "id": "temperature",
                    "type": "number",
                    "min": 0,
                    "max": 1,
                    "bound_origin": "application_limit",
                    "source_refs": ["U1"],
                },
            ]
        )
        result = self.result()
        self.assertTrue(result["valid"], result)
        for ident in ("counter", "identity", "temperature"):
            self.assertFalse(result["domain_capabilities"][ident]["supported"])
        self.assertEqual(result["analysis"], "not_run")

    def test_numeric_bounds_have_an_origin_and_integer_bounds_are_integers(self):
        domain = {"id": "count", "type": "integer", "min": 0, "max": 2, "source_refs": ["U1"]}
        self.contract["domains"].append(domain)
        self.reject("bound_origin_required")
        domain["bound_origin"] = "analysis_bound"
        self.assertTrue(self.result()["valid"])
        domain["max"] = 2.1
        self.reject("domain_type")
        domain["max"] = -1
        self.reject("empty_domain")

    def test_analysis_bound_does_not_modify_any_application_definition(self):
        original = deepcopy(self.discovery)
        self.contract["domains"].append(
            {
                "id": "count",
                "type": "integer",
                "min": 0,
                "max": 2,
                "bound_origin": "analysis_bound",
                "source_refs": ["U1"],
            }
        )
        self.assertTrue(self.result()["valid"])
        self.assertEqual(self.discovery, original)

    def test_domain_identity_distinguishes_boolean_integer_and_string(self):
        domain = load_domains([{"id": "mixed", "type": "enum", "values": [True, 1]}])["mixed"]
        self.assertEqual(domain.finite_capability()["cardinality"], 2)
        self.assertTrue(domain.accepts(True))
        self.assertFalse(domain.accepts("1"))

    def test_floating_enum_identity_is_not_claimed_as_portable(self):
        self.contract["domains"].append(
            {"id": "decimal", "type": "enum", "values": [1.0], "source_refs": ["U1"]}
        )
        self.reject("unsupported_enum_number")
        self.assertEqual(self.result()["status"], "unsupported")

    def test_initial_condition_cannot_contradict_the_canonical_initial_state(self):
        self.contract["initial"] = operation("eq", variable(), literal("active", "status"))
        self.reject("empty_initial", "/initial")
        self.contract["initial"] = literal(False)
        self.reject("empty_initial")

    def test_transition_source_and_guard_remain_in_the_normalized_definition(self):
        result = self.result()
        action = result["action_definitions"]["grant-share"]
        self.assertEqual(action["canonical_transition"]["source"], "inactive")
        self.assertEqual(action["canonical_transition"]["conditions"], ["may_manage"])
        self.assertEqual(action["canonical_updates"], {"grant-status": literal("active", "status")})
        self.discovery["state_models"][0]["transitions"][0]["dest"] = "inactive"
        changed = self.result()
        self.assertTrue(changed["valid"], changed)
        self.assertEqual(
            changed["action_definitions"]["grant-share"]["canonical_updates"]["grant-status"][
                "value"
            ],
            "inactive",
        )
        self.assertNotEqual(result["concept_sha256"], changed["concept_sha256"])

    def test_fact_update_types_and_pre_state_reads(self):
        self.contract["variables"].append(
            {
                "id": "active-fact",
                "domain": "flag",
                "owner": "object:grant",
                "concept_ref": "fact:active-grant",
                "persistence": "persistent",
                "source_refs": ["U1"],
            }
        )
        action = self.contract["actions"][0]
        action["model_refs"].append("object:grant")
        action["writes"].append("active-fact")
        action["updates"]["active-fact"] = literal(True)
        self.assertTrue(self.result()["valid"], self.result())
        action["updates"]["active-fact"] = literal("active", "status")
        self.reject("update_type")
        action["updates"]["active-fact"] = variable("active-fact", "after")
        self.reject("after_state_not_allowed")

    def test_unknown_initial_facts_are_not_reported_as_proved_initialization(self):
        self.contract["variables"].append(
            {
                "id": "active-fact",
                "domain": "flag",
                "owner": "object:grant",
                "concept_ref": "fact:active-grant",
                "persistence": "persistent",
                "source_refs": ["U1"],
            }
        )
        self.contract["actions"][0]["unchanged"].append("active-fact")
        self.contract["initial"] = variable("active-fact")
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["initial_consistency"], "unresolved")

    def test_transition_property_cannot_have_an_empty_selected_action_set(self):
        self.contract["properties"][0]["action_refs"] = []
        self.reject("property_scope")

    def test_canonical_transition_reads_cannot_disappear_with_a_simple_condition(self):
        action = self.contract["actions"][0]
        action["enabled"] = literal(True)
        action["reads"] = []
        self.reject("undeclared_read")

    def test_internal_transition_does_not_create_a_state_write(self):
        self.discovery["state_models"][0]["transitions"][0]["dest"] = None
        self.reject("internal_transition_state_write")
        action = self.contract["actions"][0]
        action["writes"] = []
        action["unchanged"].append("grant-status")
        self.assertTrue(self.result()["valid"], self.result())

    def test_direct_state_update_requires_a_canonical_transition(self):
        del self.contract["actions"][0]["transition_ref"]
        self.reject("state_write_requires_transition")

    def test_deep_expressions_return_a_scoped_failure(self):
        expr = literal(True)
        for _ in range(65):
            expr = operation("not", expr)
        self.contract["initial"] = expr
        self.reject("expression_depth")

    def test_cli_uses_the_same_validator_and_never_writes_input_files(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            (root / "bo_stategraph").mkdir()
            paths = {
                root / "discovery.json": self.discovery,
                root / "bo_stategraph/behavior.json": self.contract,
            }
            for path, value in paths.items():
                path.write_text(json.dumps(value), encoding="utf-8")
            before = {path: path.read_bytes() for path in paths}
            output = io.StringIO()
            with redirect_stdout(output):
                status = main(["validate", "--root", str(root)])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(output.getvalue()), self.result())
            self.assertEqual(before, {path: path.read_bytes() for path in paths})
            self.assertFalse((root / ".stategraph").exists())

    def test_cli_reports_missing_input_and_path_escape(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            for name in ("missing.json", "../outside.json"):
                output = io.StringIO()
                with redirect_stdout(output):
                    status = main(["validate", "--root", folder, "--contract", name])
                self.assertEqual(status, 1)
                self.assertEqual(json.loads(output.getvalue())["status"], "input_error")

    def test_cli_rejects_duplicate_json_keys_before_last_value_can_win(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            path = Path(folder) / "behavior.json"
            path.write_text('{"schema":"unknown","schema":"bo-behavior/v1"}', encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                status = main(["validate", "--root", folder, "--contract", "behavior.json"])
            self.assertEqual(status, 1)
            self.assertIn(
                "Duplicate JSON key", json.loads(output.getvalue())["errors"][0]["message"]
            )


if __name__ == "__main__":
    unittest.main()
