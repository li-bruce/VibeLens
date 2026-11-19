"""Freeze forest semantics before adding construction or behavior-contract services.

The fixture is explicitly synthetic. Its independent profile route is intentional;
removing the sharing route below is an intentional omission. Neither is diagnosed
from topology alone: the expected distinction comes from the fixture's source.
"""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.concepts import assess
from bo_observer.concepts.network_review import network_review

FIXTURE = ROOT / "tests/fixtures/behavior-contracts/forest.discovery.json"


class BehaviorBaselineTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_source_free_forest_keeps_independent_business_and_state_owners(self):
        original = deepcopy(self.document)
        result = assess(self.document)
        self.assertTrue(result["valid"], result)
        self.assertFalse(result["ready"])
        self.assertEqual(self.document, original)
        review = network_review(result["graph"])
        self.assertEqual(
            review["business"]["components"], [["read", "revoke", "share"], ["view-profile"]]
        )
        self.assertEqual(
            review["state"]["components"],
            [
                ["state:archive:active", "state:archive:inactive"],
                ["state:grant:active", "state:grant:inactive"],
            ],
        )
        self.assertFalse(any("source" in node for node in result["graph"]["nodes"]))

    def test_shared_rule_remains_one_definition_with_several_consumers(self):
        graph = assess(self.document)["graph"]
        self.assertEqual(sum(node["id"] == "policy:is_owner" for node in graph["nodes"]), 1)
        guarded = {
            edge["from"] for edge in graph["edges"] if edge["to"] == "policy-operation:manage"
        }
        self.assertTrue({"share", "revoke"} <= guarded)
        self.assertTrue(any("archive" in node for node in guarded))
        self.assertTrue(any("grant" in node for node in guarded))

    def test_known_omission_is_preserved_as_a_distinct_baseline_gap(self):
        network = self.document["networks"][0]
        network["edges"] = [edge for edge in network["edges"] if edge["id"] != "share-read"]
        result = assess(self.document)
        self.assertTrue(result["valid"], result)
        review = network_review(result["graph"])["business"]
        self.assertEqual(review["components"], [["read", "revoke"], ["share"], ["view-profile"]])
        self.assertTrue(review["review_required"])
        # P0 records the gap. P1/P2 must add source-backed obligations rather than
        # claiming this structural warning can infer which component is missing.
        self.assertFalse(any(edge["id"] == "share-read" for edge in result["graph"]["edges"]))


if __name__ == "__main__":
    unittest.main()
