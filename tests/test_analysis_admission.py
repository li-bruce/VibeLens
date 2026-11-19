"""Admission is a typed design check; it cannot stand in for a model-checker run."""

from copy import deepcopy
import unittest

from test_behavior_contract import fixture
from bo_observer.analysis.capabilities import admit


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.contract, self.discovery = fixture()
        self.contract.update(interactions=[], assumptions=[], refinements=[])
        # This fixture selects a guard-free finite design. Remove its corresponding
        # guard links as well; the canonical validator must still reject stale links.
        self.discovery["crosslinks"] = [
            link
            for link in self.discovery["crosslinks"]
            if link["relation"] != "transition_guarded_by"
        ]
        template = deepcopy(self.contract["actions"][0])
        self.contract["actions"] = []
        for model in self.discovery["state_models"]:
            state_var = model["id"] + "-status"
            for transition in model["transitions"]:
                transition["conditions"] = []
                self.contract["actions"].append(
                    {
                        **deepcopy(template),
                        "id": model["id"] + "-" + transition["trigger"],
                        "model_refs": ["state-model:" + model["id"]],
                        "transition_ref": "transition:"
                        + model["id"]
                        + ":"
                        + transition["id"],
                        "enabled": {"op": "literal", "value": True, "domain": "flag"},
                        "reads": [state_var],
                        "writes": [state_var],
                        "unchanged": [
                            v["id"]
                            for v in self.contract["variables"]
                            if v["id"] != state_var
                        ],
                    }
                )
        self.profile = {
            "schema": "bo-analysis-profile/v1",
            "id": "small",
            "subject": "design_model",
            "model_refs": self.contract["scope"]["model_refs"][:],
            "property_refs": ["archive-unchanged"],
            "assumption_refs": [],
            "bounds": {},
            "engine": "tlc",
            "budget": {"wall_seconds": 30, "memory_mb": 512},
            "required_for_acceptance": False,
        }

    def result(self):
        return admit(self.contract, self.discovery, self.profile)

    def test_supported_design_is_eligible_but_analysis_has_not_run(self):
        result = self.result()
        self.assertTrue(result["eligible"], result)
        self.assertEqual(result["analysis"], "not_run")
        self.assertTrue(result["capabilities"]["runner_available"])

    def test_hiding_an_independent_model_cannot_remove_its_scope(self):
        self.profile["model_refs"].pop()
        self.assertIn(
            "partial_model_scope", [i["code"] for i in self.result()["diagnostics"]]
        )

    def test_unconfigured_boundary_does_not_become_a_pass(self):
        self.contract.pop("interactions")
        self.assertEqual(self.result()["status"], "unresolved")

    def test_opaque_transition_guard_remains_unsupported(self):
        self.discovery["state_models"][0]["transitions"][0]["conditions"] = [
            "may_manage"
        ]
        self.assertFalse(self.result()["eligible"])

    def test_omitted_state_transition_does_not_produce_closed_model_admission(self):
        self.contract["actions"].pop()
        self.assertIn(
            "unmapped_model_transition",
            [i["code"] for i in self.result()["diagnostics"]],
        )

    def test_unknown_profile_property_fails(self):
        self.profile["property_refs"] = ["missing"]
        self.assertEqual(self.result()["status"], "invalid")

    def test_implementation_model_is_not_silently_relabelled_design(self):
        self.profile["subject"] = "implementation_model"
        self.assertEqual(self.result()["status"], "unsupported")

    def test_profile_bound_changes_only_the_detached_representation(self):
        self.contract["domains"].append(
            {"id": "count", "type": "integer", "source_refs": ["U1"]}
        )
        self.contract["actions"][0]["parameters"]["count"] = "count"
        self.assertEqual(self.result()["status"], "unsupported")
        self.profile["bounds"]["count"] = {
            "min": 0,
            "max": 2,
            "origin": "analysis_bound",
        }
        before = deepcopy(self.contract)
        result = self.result()
        self.assertTrue(result["eligible"], result)
        self.assertEqual(self.contract, before)
        self.assertNotEqual(result["definition_sha256"], result["original_sha256"])

    def test_live_identity_cap_does_not_make_the_domain_finite(self):
        self.contract["domains"].append(
            {
                "id": "ids",
                "type": "identity",
                "object_ref": "object:grant",
                "identity_policy": "monotonic",
                "max_live": 1,
                "bound_origin": "application_limit",
                "source_refs": ["U1"],
            }
        )
        self.contract["actions"][0]["parameters"]["job"] = "ids"
        self.assertEqual(self.result()["status"], "unsupported")

    def test_optional_dependency_absence_does_not_mutate_native_model(self):
        before = deepcopy(self.discovery)
        self.result()
        self.assertEqual(self.discovery, before)

    def test_termination_has_boolean_type_and_known_references(self):
        for condition in (
            {"op": "literal", "value": 2},
            {"op": "var", "id": "unknown", "phase": "before"},
        ):
            with self.subTest(condition=condition):
                self.profile["termination"] = {
                    "condition": condition,
                    "source_refs": ["U1"],
                }
                self.assertEqual(self.result()["status"], "invalid")

    def test_collection_export_budget_is_separate_from_definition(self):
        from bo_observer.analysis.tla.exporter import export_model
        from bo_observer.analysis.tla.values import ExportLimit

        self.contract["domains"].append(
            {
                "id": "large",
                "type": "integer",
                "min": 0,
                "max": 10000,
                "bound_origin": "application_limit",
                "source_refs": ["U1"],
            }
        )
        self.contract["actions"][0]["parameters"]["count"] = "large"
        self.assertTrue(self.result()["eligible"])
        with self.assertRaises(ExportLimit):
            export_model(
                self.contract,
                self.discovery,
                self.profile,
                self.profile["property_refs"][0],
            )


if __name__ == "__main__":
    unittest.main()
