"""Compare accelerated event validation with the unchanged JSON Schema contract."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.protocol import SCHEMAS, _fast_event_validator, _validator, schema_check


class EventSchemaEngineTests(unittest.TestCase):
    def setUp(self):
        self.event = {
            "protocol": "bo-event/v1",
            "schema_version": 3,
            "project_id": "fixture",
            "model_revision": "r1",
            "build_id": "build",
            "run_id": "run",
            "producer_id": "producer",
            "seq": 1,
            "id": "event-1",
            "node": "upload",
            "phase": "enter",
            "entity": "file-1",
            "attempt": "attempt-1",
            "scope": "attempt",
            "call_id": "call-1",
            "parent_call_id": None,
            "parent_event_id": None,
            "basis": {},
            "inputs": {"name": "设计.txt", "size": 20},
            "outputs": {},
            "depends": [],
            "observed_at": "2026-11-22T01:00:00.000Z",
        }
        self.reference = _validator(SCHEMAS, "event")
        self.fast = _fast_event_validator(SCHEMAS)
        self.assertIsNotNone(self.fast, "Install the declared observer requirements for this gate")
        self.assertTrue(self.reference.is_valid(self.event))

    def test_mutations_of_every_top_level_property_match_reference(self):
        schema = self.reference.schema
        mutations = [None, False, True, 0, 1, -1, 0.5, "", "unknown", [], {}, [None]]
        checked = 0
        for name in schema["properties"]:
            for value in mutations:
                changed = {**self.event, name: value}
                with self.subTest(name=name, value=value):
                    self.assertEqual(self.fast.is_valid(changed), self.reference.is_valid(changed))
                checked += 1
        self.assertGreaterEqual(checked, 300)

    def test_required_fields_unknown_fields_and_nested_facts_match(self):
        variants = []
        for name in self.reference.schema["required"]:
            changed = deepcopy(self.event)
            changed.pop(name, None)
            variants.append(changed)
        for values in [
            {"unexpected": True},
            {"depends": [{"event": "other", "type": "control"}]},
            {"depends": [{"event": "other", "type": "invented"}]},
            {"depends": [{"event": 5, "type": "control"}]},
            {"depends": [{"event": "other", "type": "control", "extra": 1}]},
            {"exception": {"type": "ValueError"}},
            {"exception": {"type": 5}},
            {"exception": {"type": "Error", "message": "undeclared"}},
            {"context_only": True, "context_boundary": "end"},
            {"trace": {"trace_id": "bad", "span_id": "bad"}},
            {"inputs": {"nested": {"items": [None, True, 2, "值"]}}},
        ]:
            variants.append({**self.event, **values})
        for value in variants:
            with self.subTest(value=value):
                self.assertEqual(self.fast.is_valid(value), self.reference.is_valid(value))

    def test_safe_numbers_nonfinite_and_payload_limit_still_reject(self):
        for value in [2**53, -(2**53), float("nan"), float("inf")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                schema_check({**self.event, "inputs": {"value": value}}, "event")
        with self.assertRaisesRegex(ValueError, "payload limit"):
            schema_check(self.event, "event", max_bytes=10)

    def test_fallback_and_accelerated_paths_keep_identical_rejection_text(self):
        bad = {**self.event, "seq": False, "phase": "invented"}
        with self.assertRaises(ValueError) as accelerated:
            schema_check(bad, "event")
        with patch("bo_observer.protocol._fast_event_validator", return_value=None):
            schema_check(self.event, "event")
            with self.assertRaises(ValueError) as original:
                schema_check(bad, "event")
        self.assertEqual(str(accelerated.exception), str(original.exception))

    def test_unavailable_accelerator_keeps_the_original_validator(self):
        _fast_event_validator.cache_clear()
        try:
            with patch.dict(sys.modules, {"jsonschema_rs": None}):
                self.assertIsNone(_fast_event_validator(SCHEMAS))
                schema_check(self.event, "event")
                with self.assertRaises(ValueError):
                    schema_check({**self.event, "seq": 0}, "event")
        finally:
            _fast_event_validator.cache_clear()

    def test_event_schema_has_only_local_references(self):
        def references(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key in {"$ref", "$dynamicRef"}:
                        self.assertTrue(child.startswith("#"))
                    references(child)
            elif isinstance(value, list):
                for child in value:
                    references(child)

        references(self.reference.schema)
        # The exact loaded source remains the contract for both implementations.
        self.assertEqual(
            self.reference.schema,
            json.loads((SCHEMAS / "event.schema.json").read_text(encoding="utf-8")),
        )


if __name__ == "__main__":
    unittest.main()
