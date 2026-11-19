"""Finite queues must be real declared values, not hidden exporter state."""

from copy import deepcopy
import unittest

from test_behavior_contract import fixture, literal, variable, operation
from bo_observer.behavior import assess


def queue_fixture():
    contract, discovery = fixture()
    owner = next(obj for obj in discovery["objects"] if obj["id"] == "grant")
    owner.setdefault("fields", {})["pending"] = ["boolean"]
    discovery["facts"].append(
        {
            "id": "pending",
            "object": "grant",
            "field": "pending",
            "type": ["boolean"],
            "read_basis": {"timing": "operation entry", "scope": "grant instance"},
            "source_refs": ["U1"],
        }
    )
    contract["domains"].append(
        {
            "id": "queue",
            "type": "sequence",
            "element_domain": "flag",
            "max_items": 2,
            "bound_origin": "application_limit",
            "source_refs": ["U1"],
        }
    )
    contract["variables"].append(
        {
            "id": "pending",
            "domain": "queue",
            "owner": "object:grant",
            "concept_ref": "fact:pending",
            "persistence": "persistent",
            "source_refs": ["U1"],
        }
    )
    contract["initial"]["args"].append(
        operation("eq", variable("pending"), literal([], "queue"))
    )
    for action in contract["actions"]:
        action["unchanged"].append("pending")
    action = deepcopy(contract["actions"][0])
    action.pop("transition_ref")
    action.update(
        id="enqueue",
        model_refs=["object:grant"],
        parameters={"payload": "flag"},
        enabled=literal(True),
        reads=["pending"],
        writes=["pending"],
        unchanged=["grant-status", "archive-status"],
        updates={
            "pending": operation(
                "append", variable("pending"), {"op": "param", "id": "payload"}
            )
        },
    )
    contract["actions"].append(action)
    return contract, discovery


class AnalysisCollectionTests(unittest.TestCase):
    def test_typed_queue_is_a_selected_observable_fact(self):
        contract, discovery = queue_fixture()
        result = assess(contract, discovery)
        self.assertTrue(result["valid"], result)
        self.assertIn("pending", result["variables"])

    def test_collection_type_and_appended_payload_must_match(self):
        contract, discovery = queue_fixture()
        discovery["facts"][-1]["type"] = ["string"]
        self.assertFalse(assess(contract, discovery)["valid"])
        contract, discovery = queue_fixture()
        contract["actions"][-1]["updates"]["pending"]["args"][1] = literal(
            "active", "status"
        )
        self.assertFalse(assess(contract, discovery)["valid"])

    def test_length_and_tail_are_typed_and_unchanged_stays_strict(self):
        contract, discovery = queue_fixture()
        contract["domains"].append(
            {
                "id": "size",
                "type": "integer",
                "min": 0,
                "max": 2,
                "bound_origin": "application_limit",
                "source_refs": ["U1"],
            }
        )
        action = contract["actions"][-1]
        action["enabled"] = operation(
            "lt", literal(0, "size"), operation("length", variable("pending"))
        )
        action["updates"]["pending"] = operation("tail", variable("pending"))
        self.assertTrue(assess(contract, discovery)["valid"])
        action["reads"] = []
        self.assertFalse(assess(contract, discovery)["valid"])


if __name__ == "__main__":
    unittest.main()
