"""Logical traces retain values/loops without pretending to be runtime recordings."""

from copy import deepcopy
import unittest
from test_behavior_contract import fixture
from bo_observer.analysis.trace import project_trace
from bo_observer.concepts.common import digest


def trace_fixture():
    contract, discovery = fixture()
    trace = {
        "schema": "bo-analysis-trace/v1",
        "origin": "model_analysis",
        "subject": "design_model",
        "analysis_id": "run-1",
        "definition_sha256": digest(contract),
        "property_refs": ["archive-unchanged"],
        "states": [
            {"grant-status": "inactive", "archive-status": "inactive"},
            {"grant-status": "active", "archive-status": "inactive"},
        ],
        "steps": [{"action": "grant-share", "parameters": {"allowed": True}}],
        "loop_back": None,
    }
    return trace, contract, discovery


class AnalysisTraceTests(unittest.TestCase):
    def setUp(self):
        self.trace, self.contract, self.discovery = trace_fixture()

    def result(self):
        return project_trace(self.trace, self.contract, self.discovery)

    def test_locates_exact_state_action_and_business_route_without_timestamps(self):
        result = self.result()
        step = result["projected_steps"][0]
        self.assertIn("state:grant:active", step["nodes"])
        self.assertIn("share", step["nodes"])
        self.assertIn("share-requests-event", step["edges"])
        self.assertEqual(
            step["changes"],
            [
                {
                    "variable": "grant-status",
                    "before": "inactive",
                    "after": "active",
                    "concept_ref": "state-model:grant",
                }
            ],
        )
        self.assertEqual(result["axis"], "logical_step")
        self.assertFalse(result["execution_authority"])
        self.assertNotIn("observed_at", str(result))
        self.assertNotIn("duration", str(result))

    def test_rejects_runtime_origin_stale_definition_and_undeclared_action(self):
        for key, value in [
            ("origin", "runtime"),
            ("definition_sha256", "0" * 64),
            ("call_id", "invented"),
        ]:
            original = deepcopy(self.trace)
            self.trace[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.result()
            self.trace = original
        self.trace["steps"][0]["action"] = "missing"
        with self.assertRaisesRegex(ValueError, "Unknown trace action"):
            self.result()

    def test_loop_retains_repeated_state_and_original_step(self):
        self.trace["states"].append(deepcopy(self.trace["states"][-1]))
        self.trace["steps"].append({"action": None, "parameters": {}})
        self.trace["loop_back"] = 1
        self.assertEqual(self.result()["loop_back"], 1)
        self.trace["loop_back"] = 0
        with self.assertRaisesRegex(ValueError, "repeated state"):
            self.result()

    def test_missing_state_parameter_or_illegal_frame_fails(self):
        mutations = [
            lambda: self.trace["states"][1].pop("archive-status"),
            lambda: self.trace["steps"][0]["parameters"].clear(),
            lambda: self.trace["states"][1].update({"archive-status": "active"}),
        ]
        for mutate in mutations:
            self.trace, _, _ = trace_fixture()
            mutate()
            with self.subTest(trace=self.trace), self.assertRaises(ValueError):
                self.result()

    def test_invalid_model_value_remains_visible_as_a_domain_finding(self):
        self.trace["states"][1]["grant-status"] = "invalid-observed-model-state"
        result = self.result()
        self.assertEqual(result["states"][1]["grant-status"], "invalid-observed-model-state")
        self.assertEqual(result["domain_findings"][0]["status"], "outside_declared_domain")

    def test_projector_is_detached_and_does_not_mutate_contract(self):
        before = deepcopy((self.trace, self.contract, self.discovery))
        result = self.result()
        result["states"].clear()
        self.assertEqual((self.trace, self.contract, self.discovery), before)


if __name__ == "__main__":
    unittest.main()
