"""Independent definition checks for cross-model obligations, not runtime claims."""

from copy import deepcopy
import unittest

from test_behavior_contract import fixture, literal, operation, variable
from test_concept_models import activity_draft
from bo_observer.behavior import assess


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.contract, self.discovery = fixture()
        self.contract.update(interactions=[], assumptions=[], refinements=[], initial_alternatives=[])
        original = self.contract["actions"][0]
        self.contract["actions"].append({
            **deepcopy(original), "id": "archive-read", "model_refs": ["state-model:archive"],
            "reads": ["grant-status", "archive-status"], "writes": [], "updates": {},
            "unchanged": ["grant-status", "archive-status"], "enabled": literal(True),
            "completion": {"kind": "return", "meaning": "Read returns"},
        })
        self.contract["actions"][1].pop("transition_ref")

    def result(self):
        return assess(self.contract, self.discovery)

    def reject(self, code):
        result = self.result()
        self.assertFalse(result["valid"], result)
        self.assertIn(code, [item["code"] for item in result["errors"]], result)

    def interaction(self, kind, **fields):
        value = {"id": "boundary", "kind": kind,
                 "model_refs": ["state-model:grant", "state-model:archive"],
                 "action_refs": ["grant-share", "archive-read"], "source_refs": ["U1"], **fields}
        self.contract["interactions"] = [value]
        return value

    def assumption(self, **fields):
        value = {"id": "scheduler", "kind": "scheduling", "model_refs": ["state-model:grant"],
                 "action_refs": [], "statement": "Ready work is eventually scheduled",
                 "rationale": "Explicit test environment", "invalidated_by": ["scheduler_change"],
                 "status": "declared", "review_source_refs": [], "source_refs": ["U1"], **fields}
        self.contract["assumptions"] = [value]
        return value

    def identity(self):
        self.contract["domains"].append({"id": "run", "type": "identity",
            "object_ref": "object:grant", "identity_policy": "opaque", "source_refs": ["U1"]})

    def handoff(self):
        self.identity()
        self.contract["domains"].append({"id": "queue", "type": "sequence", "element_domain": "flag",
            "max_items": 2, "bound_origin": "analysis_bound", "source_refs": ["U1"]})
        return self.interaction("handoff", producer="grant-share", consumer="archive-read",
            payload_domain="flag", queue_domain="queue", correlation_domain="run", ordering="fifo",
            delivery="at_least_once", retry="bounded", max_attempts=3, deduplication="correlation",
            assumption_refs=[], on_cancel="Leave acknowledged work complete", on_failure="Retain failed attempt")

    def test_shared_read_retains_two_owners_and_no_claim_of_atomicity(self):
        self.interaction("shared_read", variable_ref="grant-status", reader_actions=["archive-read"],
                         consistency="independent", timing="before_effect")
        before = deepcopy((self.contract, self.discovery))
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["interaction_definitions"]["boundary"]["witnesses"], "not_checked")
        self.assertEqual((self.contract, self.discovery), before)

    def test_read_declaration_cannot_hide_a_missing_reader(self):
        self.interaction("shared_read", variable_ref="archive-status", reader_actions=["grant-share"],
                         consistency="independent", timing="before_effect")
        self.reject("interaction_read_missing")

    def test_shared_value_owner_cannot_be_hidden_outside_the_boundary(self):
        item = self.interaction("shared_read", variable_ref="grant-status",
                                reader_actions=["archive-read"], consistency="independent",
                                timing="before_effect")
        item.update(model_refs=["state-model:archive"], action_refs=["archive-read"])
        self.reject("interaction_owner")

    def test_assumption_actions_keep_their_model_scope(self):
        self.assumption(action_refs=["archive-read"])
        self.reject("assumption_action_owner")

    def test_revision_consistency_requires_a_recorded_revision_read(self):
        item = self.interaction("shared_read", variable_ref="grant-status", reader_actions=["archive-read"],
                                consistency="revision", timing="snapshot")
        self.reject("revision_variable")
        item["revision_variable"] = "grant-status"
        self.reject("revision_variable")

    def test_transaction_read_needs_a_commit_not_a_function_return(self):
        item = self.interaction("shared_read", variable_ref="grant-status", reader_actions=["archive-read"],
                                consistency="transaction", timing="snapshot", completion_action="archive-read")
        self.reject("completion_boundary")
        item["completion_action"] = "grant-share"
        self.assertTrue(self.result()["valid"], self.result())

    def test_interaction_does_not_drop_action_owner(self):
        item = self.interaction("shared_read", variable_ref="grant-status", reader_actions=["archive-read"],
                                consistency="independent", timing="before_effect")
        item["model_refs"] = ["state-model:grant"]
        self.reject("interaction_action_owner")

    def test_unknown_boundary_field_fails_strict_schema(self):
        self.handoff()["guess"] = True
        self.reject("schema_oneOf")

    def test_handoff_keeps_bounded_queue_and_growing_correlation_distinct(self):
        self.handoff()
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertTrue(result["domain_capabilities"]["queue"]["supported"])
        self.assertFalse(result["domain_capabilities"]["run"]["supported"])

    def test_queue_payload_mismatch_fails(self):
        self.handoff()["payload_domain"] = "status"
        self.reject("queue_payload")

    def test_unbounded_retry_cannot_keep_an_undeclared_cap(self):
        self.handoff()["retry"] = "unbounded"
        self.reject("retry_bound")

    def test_exactly_once_requires_a_stated_assumption(self):
        item = self.handoff()
        item["delivery"] = "exactly_once"
        self.reject("delivery_assumption")
        self.assumption(kind="consistency")
        item["assumption_refs"] = ["scheduler"]
        self.assertTrue(self.result()["valid"], self.result())

    def test_acknowledgement_is_not_a_commit_or_return(self):
        self.handoff()["acknowledgement_action"] = "grant-share"
        self.reject("completion_boundary")

    def test_transaction_keeps_its_commit_inside_member_actions(self):
        item = self.interaction("transaction", member_actions=["archive-read"],
            completion_action="grant-share", atomicity="database_transaction", conflict="abort", assumption_refs=[])
        self.reject("transaction_completion")
        item["member_actions"].append("grant-share")
        self.assertTrue(self.result()["valid"], self.result())

    def test_resource_and_join_reuse_canonical_activity_semantics(self):
        activity = activity_draft()["state_models"][0]
        self.discovery["state_models"][0]["execution"] = activity["execution"]
        self.discovery["state_models"][0]["guards"]["checks_complete"] = activity["guards"]["checks_complete"]
        self.discovery["state_models"][0]["transitions"][0]["conditions"].append("checks_complete")
        self.identity()
        self.interaction("resource", resource_ref="resource:grant:workers", acquire_actions=["grant-share"],
            release_actions=["archive-read"], holder_domain="run", on_cancel="Release held units", on_restart="Reconcile holders")
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["interaction_definitions"]["boundary"]["canonical_activity"]["max"], 2)
        self.interaction("join", join_ref="join:grant:checks", arrival_actions=["archive-read"],
                         release_action="grant-share", invocation_domain="run")
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["interaction_definitions"]["boundary"]["canonical_activity"]["policy"], "all")
        self.discovery["state_models"][0]["transitions"][0]["conditions"].remove("checks_complete")
        self.reject("invalid_concept_definition")

    def test_resource_capacity_cannot_be_redeclared_in_an_interaction(self):
        self.identity()
        self.interaction("resource", resource_ref="resource:grant:workers", acquire_actions=["grant-share"],
            release_actions=["archive-read"], holder_domain="run", on_cancel="Release", on_restart="Reconcile", capacity=99)
        self.reject("schema_oneOf")

    def test_assumption_confirmation_cannot_come_from_the_agent(self):
        self.discovery["sources"].append({"id": "A1", "kind": "assistant", "text": "I think so", "locator": "test:agent"})
        self.assumption(status="confirmed", review_source_refs=["A1"])
        self.reject("assumption_confirmation")

    def test_progress_is_typed_and_does_not_infer_fairness(self):
        prop = {"id": "finish", "kind": "progress_property", "action_refs": [],
                "trigger": literal(True), "expression": operation("eq", variable(), literal("active", "status")),
                "fairness": "weak", "assumption_refs": [], "source_refs": ["U1"]}
        self.contract["properties"].append(prop)
        self.reject("fairness_assumption")
        self.assumption()
        prop["assumption_refs"] = ["scheduler"]
        self.assertTrue(self.result()["valid"], self.result())

    def test_recovery_values_must_be_complete_and_typed(self):
        item = {"id": "restart", "values": {"grant-status": "active"}, "condition": literal(True), "source_refs": ["U1"]}
        self.contract["initial_alternatives"] = [item]
        self.reject("initial_value_scope")
        item["values"]["archive-status"] = "unknown"
        self.reject("initial_value_type")
        item["values"]["archive-status"] = "inactive"
        self.assertTrue(self.result()["valid"], self.result())

    def test_impossible_recovery_condition_fails(self):
        self.contract["initial_alternatives"] = [{"id": "restart", "values": {
            "grant-status": "active", "archive-status": "inactive"}, "condition": literal(False), "source_refs": ["U1"]}]
        self.reject("empty_initial_alternative")

    def refinement(self, **fields):
        item = {"id": "map", "variable_ref": "grant-status", "concrete_domain": "status",
                "mapping": {"kind": "identity"}, "property_refs": ["archive-unchanged"],
                "completion_action": "grant-share", "internal_actions": ["archive-read"],
                "justification": "The exact canonical values are emitted", "evidence_kind": "declared",
                "evidence_refs": [], "source_refs": ["U1"], **fields}
        self.contract["refinements"] = [item]
        return item

    def test_refinement_keeps_claim_and_actual_evidence_separate(self):
        self.refinement()
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["refinements"]["map"]["value_coverage"], "total")
        self.assertEqual(result["refinements"]["map"]["evidence_status"], "not_checked")

    def test_duplicate_mapping_inputs_fail(self):
        self.refinement(mapping={"kind": "table", "entries": [
            {"from": "inactive", "to": "inactive"}, {"from": "inactive", "to": "active"}], "unmapped": "unknown"})
        self.reject("duplicate_mapping_input")

    def test_internal_step_cannot_change_the_abstract_value(self):
        self.refinement(internal_actions=["grant-share"])
        self.reject("internal_step_changes_value")

    def test_mapping_evidence_claim_requires_references(self):
        self.refinement(evidence_kind="trace_checked")
        self.reject("refinement_evidence_missing")

    def test_partial_mapping_stays_partial(self):
        self.refinement(mapping={"kind": "table", "entries": [{"from": "inactive", "to": "inactive"}], "unmapped": "unknown"})
        self.assertEqual(self.result()["refinements"]["map"]["value_coverage"], "partial")

    def test_missing_sections_do_not_gain_configuration_from_defaults(self):
        self.contract.pop("refinements")
        self.assertEqual(self.result()["configuration"]["refinements"], "not_configured")


if __name__ == "__main__":
    unittest.main()
