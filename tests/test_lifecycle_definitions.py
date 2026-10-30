"""Declared lifecycle vocabularies must describe captured facts without executing rules."""

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_contracts import validate_graph, validate_lifecycle
from jsonschema import Draft202012Validator


def subject():
    return {
        "id": "share",
        "capture": {"in": {}, "out": {"status": "string", "allowed": "boolean"}},
        "lifecycle": {
            "states": [
                {"id": "checking", "label": "Checking access", "kind": "active"},
                {"id": "approved", "label": "Approved", "kind": "ended"},
                {"id": "rejected", "label": "Rejected", "kind": "ended"},
            ],
            "bindings": [
                {"phase": "enter", "state": "checking", "boundary": "start"},
                {
                    "phase": "return",
                    "state": "approved",
                    "boundary": "end",
                    "when": {"direction": "out", "field": "allowed", "equals": True},
                },
                {
                    "phase": "return",
                    "state": "rejected",
                    "boundary": "end",
                    "when": {"direction": "out", "field": "allowed", "equals": False},
                },
            ],
        },
    }


class LifecycleDefinitions(unittest.TestCase):
    def test_shared_schema_and_graph_accept_registered_observations(self):
        node = subject()
        schema = json.loads(
            (ROOT / "skills/vibelens/scripts/bo_observer/schemas/model.schema.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator(schema["$defs"]["nodeLifecycle"]).validate(node["lifecycle"])
        validate_lifecycle(node)
        model = json.loads(
            (ROOT / "examples/delivery/observer_generated/behavior.json").read_text(
                encoding="utf-8"
            )
        )
        target = next(n for n in model["nodes"] if n.get("capture"))
        target.update({k: node[k] for k in ("capture", "lifecycle")})
        validate_graph(model)
        target["lifecycle"]["bindings"][0]["state"] = "missing"
        with self.assertRaises(ValueError):
            validate_graph(model)

    def test_selector_must_be_observable_and_type_correct(self):
        for key, value in [("field", "not_captured"), ("direction", "both"), ("equals", 1)]:
            node = subject()
            node["lifecycle"]["bindings"][1]["when"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_lifecycle(node)

    def test_ambiguous_or_inconsistent_definitions_are_rejected(self):
        mutations = [
            lambda d: d["states"].append(copy.deepcopy(d["states"][0])),
            lambda d: d["bindings"].append(copy.deepcopy(d["bindings"][1])),
            lambda d: d["bindings"][1].pop("when"),
            lambda d: d["bindings"][0].update(boundary="end"),
            lambda d: d["bindings"][1].update(boundary="update"),
            lambda d: d["bindings"][0].update(phase=[]),
            lambda d: d["bindings"][0].update(state=[]),
            lambda d: d["states"][0].update(label="Bad\nlabel"),
            lambda d: d.update(executor="inferred"),
        ]
        for mutate in mutations:
            node = subject()
            mutate(node["lifecycle"])
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                validate_lifecycle(node)

    def test_absence_preserves_generic_mode_but_null_is_malformed(self):
        node = {"id": "share"}
        validate_lifecycle(node)
        self.assertNotIn("lifecycle", node)
        node["lifecycle"] = None
        with self.assertRaises(ValueError):
            validate_lifecycle(node)


if __name__ == "__main__":
    unittest.main()
