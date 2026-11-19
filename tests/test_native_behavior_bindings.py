"""Behavior bindings must cover the contract, not only existing graph nodes.

These fixtures check source obligations. Runtime correspondence has separate
tests; a source-bound declaration alone never establishes a completed action.
"""

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from test_behavior_contract import fixture
from bo_observer.behavior.contract import assess as definition
from bo_observer.sources import scan


def source(symbol):
    return {"path": "application.py", "symbol": symbol}


def value_binding(node, *, writer=True):
    return {
        "reader": source("read_native"),
        "writers": [source("share")] if writer else [],
        "observation": {"node": node, "phase": "read", "path": ["outputs", "state"]},
        "native": {
            "collection": ["native_values", node],
            "value": ["state"],
            "keys": [
                {"name": name, "actual": [name], "observed": path}
                for name, path in (
                    ("model", ["inputs", "owner"]),
                    ("instance", ["entity"]),
                    ("invocation", ["call_id"]),
                    ("attempt", ["attempt"]),
                    ("build", ["build_id"]),
                )
            ],
        },
        "cases": ["share"],
    }


def binding_fixture(root):
    contract, discovery = fixture()
    (root / "application.py").write_text(
        'def share(allowed):\n'
        '    """Grant access after checking the caller.\n\n'
        '    Args:\n        allowed: Current permission decision.\n    """\n'
        '    return allowed\n\n'
        'def commit():\n    """Commit the native grant write."""\n    return True\n\n'
        'def read_native():\n    """Read grant values from the native store."""\n'
        '    return {}\n', encoding="utf-8"
    )
    nodes = []
    for ident, symbol in (("grant", "share"), ("archive", "share"),
                          ("share", "share"), ("commit", "commit")):
        nodes.append({"id": ident, "kind": "function", "source": source(symbol),
                      "capture": {"in": {"owner": "string", "allowed": "boolean"},
                                  "out": {"state": "string", "transaction_id": "string"}}})
    parameter = value_binding("share", writer=False)
    parameter["observation"] = {"node": "share", "phase": "enter", "path": ["inputs", "allowed"]}
    parameter["native"]["value"] = ["allowed"]
    parameter["source_parameter"] = "allowed"
    parameter["cases"] = ["share", "error"]
    completion = value_binding("commit", writer=False)
    completion["observation"] = {"node": "commit", "phase": "commit", "path": ["outputs", "transaction_id"]}
    completion["native"]["value"] = ["transaction_id"]
    failure = value_binding("share", writer=False)
    failure["cases"] = ["error"]
    failure["observation"] = {"node": "share", "phase": "error", "path": ["exception", "type"]}
    failure["native"]["value"] = ["exception_type"]
    binding = {
        "schema": "bo-behavior-bindings/v1",
        "definition_sha256": definition(contract, discovery)["definition_sha256"],
        "variables": {"grant-status": value_binding("grant"),
                      "archive-status": value_binding("archive", writer=False)},
        "actions": {"grant-share": {
            "entry": {"node": "share", "phase": "enter"},
            "completion": {"node": "commit", "phase": "commit"},
            "completion_witness": completion,
            "parameters": {"allowed": parameter},
            "exits": [{"kind": "exception", "site": {"node": "share", "phase": "error"}, "witness": failure}],
            "cases": [{"id": "share", "boundaries": ["complete"]},
                      {"id": "error", "boundaries": ["exception"]}],
        }},
        "interactions": {},
    }
    return contract, discovery, {"nodes": nodes, "behavior_bindings": binding}, scan(root, ["application.py"])


class NativeBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contract, self.discovery, self.model, self.index = binding_fixture(self.root)

    def result(self):
        from bo_observer.behavior.bindings import assess_bindings
        return assess_bindings(self.contract, self.discovery, self.model, index=self.index,
                               case_ids={"share", "error"})

    def reject(self, code):
        result = self.result()
        self.assertFalse(result["valid"], result)
        self.assertIn(code, {error["code"] for error in result["errors"]}, result)

    def test_complete_source_binding_retains_runtime_boundary(self):
        before = deepcopy((self.contract, self.discovery, self.model, self.index))
        result = self.result()
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["runtime"], "not_checked")
        self.assertEqual(set(result["models"]), {"state-model:grant", "state-model:archive"})
        self.assertEqual(before, (self.contract, self.discovery, self.model, self.index))

    def test_second_model_variable_cannot_disappear(self):
        del self.model["behavior_bindings"]["variables"]["archive-status"]
        self.reject("unbound_behavior_variable")

    def test_one_physical_boundary_cannot_count_as_two_outcomes(self):
        action = self.model["behavior_bindings"]["actions"]["grant-share"]
        action["exits"][0]["site"] = deepcopy(action["completion"])
        self.reject("duplicate_action_boundary")

    def test_witness_cannot_silently_narrow_its_declared_boundary(self):
        action = self.model["behavior_bindings"]["actions"]["grant-share"]
        action["completion_witness"]["observation"]["when"] = [{"path": ["entity"], "equals": "only-one-user"}]
        self.reject("completion_witness_site")

    def test_selector_cannot_reference_an_uncollected_field(self):
        action = self.model["behavior_bindings"]["actions"]["grant-share"]
        action["entry"]["when"] = [{"path": ["outputs", "not_collected"], "equals": True}]
        self.reject("binding_capture_missing")

    def test_same_id_with_changed_definition_is_stale(self):
        self.contract["actions"][0]["completion"]["meaning"] = "Different completion meaning"
        self.reject("stale_behavior_binding")

    def test_return_is_not_a_transaction_commit(self):
        self.model["behavior_bindings"]["actions"]["grant-share"]["completion"]["phase"] = "return"
        self.reject("completion_phase_differs")

    def test_writer_cannot_certify_its_own_native_read(self):
        self.model["behavior_bindings"]["variables"]["grant-status"]["reader"] = source("share")
        self.reject("reader_is_writer")

    def test_source_and_capture_must_exist(self):
        self.model["nodes"][0]["source"] = source("missing")
        self.reject("binding_source_missing")

    def test_missing_parameter_is_not_covered_by_action_entry(self):
        self.model["behavior_bindings"]["actions"]["grant-share"]["parameters"] = {}
        self.reject("unbound_behavior_parameter")

    def test_unknown_fields_and_unknown_cases_fail(self):
        self.model["behavior_bindings"]["silent_default"] = True
        self.reject("schema_additionalProperties")
        self.model["behavior_bindings"].pop("silent_default")
        self.model["behavior_bindings"]["actions"]["grant-share"]["cases"][0]["id"] = "imaginary"
        self.reject("binding_case_missing")

    def test_native_reader_cannot_use_the_observation_as_its_oracle(self):
        self.model["behavior_bindings"]["variables"]["grant-status"]["native"]["collection"] = ["events"]
        self.reject("observation_derived_native_value")

    def test_model_and_attempt_keys_are_mandatory(self):
        native = self.model["behavior_bindings"]["variables"]["grant-status"]["native"]
        native["keys"] = [key for key in native["keys"] if key["name"] != "model"]
        self.reject("schema_minItems")
        native["keys"].append(deepcopy(native["keys"][0]))
        self.reject("native_identity_incomplete")


if __name__ == "__main__":
    unittest.main()
