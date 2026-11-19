"""A future phase or an incomplete matrix must not appear as accepted work."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_behavior_plan import PLAN, baseline_blob, check_inventory, test_entrypoints, read_evidence


class BehaviorPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads(PLAN.read_text(encoding="utf-8"))

    def test_complete_pending_inventory_keeps_the_original_git_fixtures(self):
        self.assertEqual(check_inventory(self.plan), [])

    def test_removed_requirement_or_case_is_detected(self):
        for key in ("requirements", "cases", "phases"):
            plan = deepcopy(self.plan)
            plan[key].pop()
            self.assertTrue(check_inventory(plan), key)

    def test_future_phase_cannot_skip_a_dependency(self):
        plan = deepcopy(self.plan)
        # Make the missing prerequisite explicit: the real ledger progresses.
        plan["phases"][6]["status"] = "pending"
        plan["phases"][7]["status"] = "in_progress"
        self.assertIn("P7: prerequisite not complete", check_inventory(plan))

    def test_no_completion_from_a_test_name_or_a_document(self):
        plan = deepcopy(self.plan)
        plan["cases"][0].update(status="passed", evidence=["missing-evidence.json"])
        self.assertIn("A01: no executed acceptance evidence", check_inventory(plan))

    def test_partial_or_other_case_receipts_cannot_close_this_case(self):
        plan = deepcopy(self.plan)
        plan["cases"][0].update(status="passed", evidence=["receipt.json"])
        for results in (
            {},
            {"A01": {"status": "partial", "evidence": ["run.log"]}},
            {"A02": {"status": "passed", "evidence": ["run.log"]}},
        ):
            errors = check_inventory(
                plan,
                load_evidence=lambda name: (
                    {"case_results": results} if name == "receipt.json" else read_evidence(name)
                ),
            )
            self.assertIn("A01: no executed acceptance evidence", errors)

    def test_explicit_executed_case_claim_is_recognized(self):
        plan = deepcopy(self.plan)
        plan["cases"][0].update(status="passed", evidence=["receipt.json"])
        receipt = {"case_results": {"A01": {"status": "passed", "evidence": ["run.log"]}}}
        self.assertEqual(
            check_inventory(
                plan,
                load_evidence=lambda name: receipt if name == "receipt.json" else read_evidence(name),
            ),
            [],
        )

    def test_baseline_content_cannot_silently_change(self):
        def modified(revision, path):
            return baseline_blob(revision, path) if path == "tools/verify.py" else b"changed"

        errors = check_inventory(self.plan, read_blob=modified)
        self.assertTrue(any(error.startswith("baseline: changed reference") for error in errors))

    def test_runner_inventory_is_derived_without_running_commands(self):
        self.assertEqual(
            test_entrypoints('run(ROOT, "tests/test_old.py"); run(ROOT, "setup.py")'),
            {"tests/test_old.py"},
        )


if __name__ == "__main__":
    unittest.main()
