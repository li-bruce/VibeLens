"""Capture failures block mapping acceptance even when application results match."""

from pathlib import Path
from copy import deepcopy
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.workflow.sync_verify import assess_observations, assess_probe_health
from bo_observer.workflow.change_sync import review_errors


class ProbeHealthTests(unittest.TestCase):
    def payload(self, health, mode="on"):
        return {
            "runs": [
                {
                    "case": "download",
                    "mode": mode,
                    "observations": {"allowed": False},
                    "probe_health": health,
                }
            ]
        }

    def test_capture_error_blocks_mapping_without_reclassifying_business_result(self):
        payload = self.payload({"errors": 1, "dropped": 0, "data_errors": 0})
        contract = {
            "checks": [
                {
                    "id": "deny",
                    "case": "download",
                    "requirement": "R1",
                    "path": ["allowed"],
                    "equals": False,
                }
            ]
        }
        self.assertEqual(assess_observations({}, contract, payload, ["on"]), [])
        report = assess_probe_health(payload, required=True)
        self.assertFalse(report["valid"])
        self.assertEqual(report["errors"][0]["counter"], "errors")

    def test_healthy_capture_passes_and_off_fault_remain_distinct(self):
        self.assertTrue(
            assess_probe_health(self.payload({"errors": 0, "dropped": 0}), required=True)["valid"]
        )
        for mode in ("off", "fault"):
            report = assess_probe_health(self.payload({"errors": 12, "dropped": 4}, mode))
            self.assertTrue(report["valid"])
            self.assertEqual(report["checked_runs"], 0)

    def test_missing_required_and_malformed_counters_cannot_pass(self):
        self.assertFalse(assess_probe_health({"runs": []}, required=True)["valid"])
        for value in (
            None,
            {},
            {"errors": False, "dropped": 0},
            {"errors": -1, "dropped": 0},
            {"errors": 0, "dropped": "0"},
            {"errors": 0, "dropped": 0, "data_errors": 1},
        ):
            with self.subTest(value=value):
                self.assertFalse(assess_probe_health(self.payload(value), required=True)["valid"])

    def test_legacy_omission_is_not_claimed_as_checked_health(self):
        report = assess_probe_health({"runs": [{"case": "old", "mode": "on"}]})
        self.assertTrue(report["valid"])
        self.assertEqual(report["checked_runs"], 0)

    def test_required_health_cannot_be_removed_by_a_later_candidate(self):
        base = {
            "intent": {"requirements": []},
            "acceptance": {"checks": []},
            "verification_contract": {"require_probe_health": True},
        }
        current = {**deepcopy(base), "id": "candidate", "verification_contract": {}}
        review = {
            "candidate_id": "candidate",
            "decisions": {
                name: {"action": "unchanged", "reason": "Independent regression"}
                for name in ("business", "state_machine", "abstraction", "probes")
            },
        }
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            (root / "review.json").write_text(json.dumps(review), encoding="utf-8")
            self.assertIn(
                {"weakened_verification": "require_probe_health"},
                review_errors(root, base, current, {"unmapped_changed_symbols": []}),
            )


if __name__ == "__main__":
    unittest.main()
