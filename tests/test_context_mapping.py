"""Native identity facts and captured metadata are compared independently of HTTP success."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.workflow.mapping_contract import (
    assess,
    assess_context_fields,
    context_coverage_errors,
    protected_plan_errors,
    validate_plan,
)


class ContextMappingTests(unittest.TestCase):
    def setUp(self):
        self.field = {
            "id": "native-principal",
            "case": "rejected-login",
            "node": "login",
            "phase": "enter",
            "actual": ["native", "authenticated_actor"],
            "mapped": ["provenance", "actor"],
            "source": "Native request authentication state, read before credential validation",
        }
        self.plan = {
            "schema": "bo-mapping/v1",
            "source": "Native rows and request state",
            "cases": ["rejected-login"],
            "modes": ["on", "off", "fault"],
            "actual_collection": ["rows"],
            "actual_id": ["id"],
            "fields": [
                {"id": key, "node": "login", "actual": [key], "mapped": [key]}
                for key in ("state", "revision", "build_id", "context")
            ],
            "export": {"case": "rejected-login", "mode": "on"},
            "context_fields": [self.field],
        }
        self.model = {
            "nodes": [{"id": "login"}],
            "machine": {"context": {"slots": {"type": "integer"}}},
        }
        self.event = {
            "id": "observed-login",
            "node": "login",
            "phase": "enter",
            "provenance": {"actor": None},
        }
        self.payload = {
            "runs": [
                {
                    "case": "rejected-login",
                    "mode": "on",
                    "native": {"authenticated_actor": None},
                    "observations": {"http_status": 401},
                    "events": [self.event],
                }
            ]
        }

    def test_correct_401_does_not_make_a_claimed_username_an_authenticated_actor(self):
        self.event["provenance"]["actor"] = {"id": "submitted-name", "kind": "user"}
        self.assertEqual(self.payload["runs"][0]["observations"]["http_status"], 401)
        result = assess_context_fields(self.payload, self.plan)
        self.assertFalse(result["valid"])
        self.assertIsNone(result["errors"][0]["actual"])

    def test_explicit_null_is_witnessed_absence_but_missing_is_not(self):
        self.assertTrue(assess_context_fields(self.payload, self.plan)["valid"])
        del self.event["provenance"]["actor"]
        self.assertFalse(assess_context_fields(self.payload, self.plan)["valid"])
        self.event["provenance"]["actor"] = None
        self.payload["runs"][0]["events"] = []
        self.assertFalse(assess_context_fields(self.payload, self.plan)["valid"])

    def test_metadata_checks_are_protected_and_native_paths_are_required(self):
        validate_plan(self.plan, self.model)
        after = deepcopy(self.plan)
        after["context_fields"] = []
        self.assertTrue(protected_plan_errors(self.plan, after))
        for mutation in (
            {"case": "not-a-case"},
            {"mapped": ["outputs", "status"]},
            {"actual": []},
            {"source": ""},
        ):
            bad = deepcopy(self.plan)
            bad["context_fields"][0].update(mutation)
            with self.assertRaises(ValueError):
                validate_plan(bad, self.model)

    def test_recorded_metadata_components_need_independent_context_comparisons(self):
        self.assertEqual(context_coverage_errors(self.payload, self.plan), [])
        self.assertTrue(context_coverage_errors(self.payload, {"context_fields": []}))
        self.event["provenance"]["objects"] = [{"type": "File", "id": "f1", "role": "output"}]
        self.assertEqual(
            context_coverage_errors(self.payload, self.plan),
            ["native context mapping omits observed component: rejected-login/login/enter/objects"],
        )

    def test_context_coverage_is_specific_to_case_node_and_phase(self):
        for mutation in ({"node": "upload"}, {"phase": "return"}):
            other = deepcopy(self.event)
            other.update(mutation)
            self.payload["runs"][0]["events"].append(other)
            self.assertTrue(context_coverage_errors(self.payload, self.plan))
            self.payload["runs"][0]["events"].pop()
        other = deepcopy(self.payload["runs"][0])
        other["case"] = "accepted-login"
        self.payload["runs"].append(other)
        self.assertTrue(context_coverage_errors(self.payload, self.plan))

    def test_malformed_context_plan_is_a_diagnostic_not_an_acceptance_crash(self):
        for rows in (None, {}, [None], [{}], [{**self.field, "actual": ["events", 0]}]):
            bad = {**self.plan, "context_fields": rows}
            self.assertFalse(assess_context_fields(self.payload, bad)["valid"])
            self.assertTrue(context_coverage_errors(self.payload, bad))
            self.assertFalse(assess(self.payload, plan=bad, model=self.model)["valid"])
            with self.assertRaises(ValueError):
                validate_plan(bad, self.model)

    def test_physical_exception_type_can_use_the_same_native_mapping_plan(self):
        field = {
            **self.field,
            "id": "native-exception",
            "phase": "error",
            "actual": ["native", "exception_type"],
            "mapped": ["exception", "type"],
        }
        plan = {**self.plan, "context_fields": [field]}
        validate_plan(plan, self.model)
        self.event.update(phase="error", exception={"type": "ValueError"})
        self.payload["runs"][0]["native"]["exception_type"] = "ValueError"
        self.assertTrue(assess_context_fields(self.payload, plan)["valid"])
        self.event["exception"]["type"] = "RuntimeError"
        self.assertFalse(assess_context_fields(self.payload, plan)["valid"])

    def joined_calls(self):
        """Two native principals call the same method; trace order is immaterial."""
        field = {
            **self.field,
            "actual": ["actor"],
            "each": {
                "collection": ["native_calls"],
                "actual_key": [["trace_id"], ["span_id"]],
                "mapped_key": [["trace", "trace_id"], ["trace", "span_id"]],
            },
        }
        run = self.payload["runs"][0]
        run["native_calls"] = [
            {"trace_id": "trace-a", "span_id": "same-span", "actor": None},
            {
                "trace_id": "trace-b",
                "span_id": "same-span",
                "actor": {"id": "admin-2", "kind": "user"},
            },
        ]
        run["events"] = [
            {
                **deepcopy(self.event),
                "id": f"event-{index}",
                "trace": {"trace_id": record["trace_id"], "span_id": record["span_id"]},
                "provenance": {"actor": record["actor"]},
            }
            for index, record in reversed(list(enumerate(run["native_calls"])))
        ]
        return run, {**self.plan, "context_fields": [field]}

    def test_repeated_calls_join_native_facts_by_full_identity_without_order_pairing(self):
        run, plan = self.joined_calls()
        validate_plan(plan, self.model)
        result = assess_context_fields(self.payload, plan)
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["checks"], 2)
        self.assertEqual(context_coverage_errors(self.payload, plan), [])
        run["events"][0]["provenance"]["actor"] = None
        self.assertFalse(assess_context_fields(self.payload, plan)["valid"])

    def test_join_requires_both_native_and_observed_sides_and_unique_native_keys(self):
        for side in ("events", "native_calls"):
            run, plan = self.joined_calls()
            run[side].pop()
            self.assertFalse(assess_context_fields(self.payload, plan)["valid"])
        run, plan = self.joined_calls()
        run["native_calls"].append(deepcopy(run["native_calls"][0]))
        self.assertFalse(assess_context_fields(self.payload, plan)["valid"])

    def test_join_does_not_cover_unmatched_events_or_derive_native_values_from_events(self):
        run, plan = self.joined_calls()
        run["events"].append(
            {
                **deepcopy(run["events"][0]),
                "id": "extra",
                "trace": {"trace_id": "trace-c", "span_id": "same-span"},
            }
        )
        self.assertTrue(context_coverage_errors(self.payload, plan))
        for mutation in (
            {"collection": ["events"]},
            {"actual_key": []},
            {"mapped_key": [["trace", "trace_id"]]},
            {"collection": "native_calls"},
        ):
            _, plan = self.joined_calls()
            plan["context_fields"][0]["each"].update(mutation)
            self.assertFalse(assess_context_fields(self.payload, plan)["valid"])
            with self.assertRaises(ValueError):
                validate_plan(plan, self.model)


if __name__ == "__main__":
    unittest.main()
