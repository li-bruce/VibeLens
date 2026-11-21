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
from bo_observer.concepts import assess, confirm
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

    def test_split_network_keeps_actions_rules_and_states_but_requires_scope_review(self):
        """Separate a formerly grouped capability without inventing a flow edge."""
        before = deepcopy(self.document)
        profile = before["networks"].pop()
        before["networks"][0]["nodes"].extend(profile["nodes"])
        before["confirmations"].append(confirm(before, ["*"], ["U1"], "split-before"))
        after = deepcopy(before)
        after["networks"][0]["nodes"] = [
            node for node in after["networks"][0]["nodes"] if node["id"] != "view-profile"
        ]
        after["networks"].append(profile)
        after["sources"].append(
            {
                "id": "U2",
                "kind": "user",
                "locator": "Synthetic A33 split request",
                "text": "Keep profile viewing as its own capability; preserve sharing and its rules.",
            }
        )
        pending = assess(after, previous=before)
        self.assertTrue(pending["valid"], pending)
        self.assertFalse(pending["ready"])
        self.assertIn("business-network:profile", pending["blocked"])
        after["confirmations"].append(confirm(after, ["*"], ["U2"], "split-after"))
        accepted = assess(after, previous=before)
        self.assertTrue(accepted["ready"], accepted)
        self.assertEqual(after["state_models"], before["state_models"])
        self.assertEqual(after["policy"], before["policy"])
        self.assertEqual(
            {node["id"] for net in after["networks"] for node in net["nodes"]},
            {node["id"] for net in before["networks"] for node in net["nodes"]},
        )
        self.assertEqual(
            network_review(accepted["graph"])["business"]["components"],
            [["read", "revoke", "share"], ["view-profile"]],
        )

    def test_retired_network_stays_blocked_until_explicit_removal_review(self):
        """A narrowed active scope cannot silently erase an independent model."""
        before = deepcopy(self.document)
        before["confirmations"].append(confirm(before, ["*"], ["U1"], "retire-before"))
        after = deepcopy(before)
        after["networks"] = [net for net in after["networks"] if net["id"] != "profile"]
        after["applicability"] = [
            item for item in after["applicability"] if item["operation"] != "view-profile"
        ]
        after["scope"] = ["share"]
        pending = assess(after, previous=before)
        self.assertTrue(pending["valid"], pending)
        self.assertIn("retired:business-network:profile", pending["blocked"])
        after["sources"].append(
            {
                "id": "U2",
                "kind": "user",
                "locator": "Synthetic A33 removal request",
                "text": "Remove profile viewing; keep the complete sharing model unchanged.",
            }
        )
        after["confirmations"].append(confirm(after, ["*"], ["U2"], "retire-after"))
        accepted = assess(after, previous=before)
        self.assertTrue(accepted["ready"], accepted)
        self.assertNotIn("view-profile", {node["id"] for node in accepted["graph"]["nodes"]})
        self.assertEqual(after["state_models"], before["state_models"])
        self.assertEqual(after["policy"], before["policy"])


if __name__ == "__main__":
    unittest.main()
