"""Native invalidity, finite analysis and observation errors have separate results."""

from copy import deepcopy
import unittest

from test_native_behavior_bindings import value_binding
from bo_observer.behavior.domains import Domain
from bo_observer.behavior.native_values import compare_values


class NativeValueTests(unittest.TestCase):
    def setUp(self):
        self.witness = value_binding("grant")
        self.row = {"model": "m", "instance": "1", "invocation": "c",
                    "attempt": "a", "build": "b", "state": 1}
        self.event = {"id": "e", "node": "grant", "phase": "read", "inputs": {"owner": "m"},
                      "entity": "1", "call_id": "c", "attempt": "a", "build_id": "b",
                      "outputs": {"state": 1}}
        self.run = {"native_values": {"grant": [self.row]}, "events": [self.event]}

    def result(self, domain=None):
        return compare_values(self.run, self.witness, build_id="b", owners={"m"}, domain=domain)

    def test_analysis_bound_never_clamps_the_native_value(self):
        self.row["state"] = self.event["outputs"]["state"] = 20
        result = self.result(Domain("n", "integer", minimum=0, maximum=2, bound_origin="analysis_bound"))
        self.assertTrue(result["valid"])
        self.assertEqual(result["domains"][0]["status"], "outside_analysis_domain")
        self.assertEqual(result["checks"][0]["observed"], 20)

    def test_invalid_application_value_is_still_faithfully_observed(self):
        self.row["state"] = self.event["outputs"]["state"] = None
        result = self.result(Domain("s", "set", element=Domain("b", "boolean")))
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["domains"][0]["status"], "outside_application_domain")
        del self.event["outputs"]["state"]
        self.assertFalse(self.result()["valid"])

    def test_numeric_and_set_correspondence_uses_declared_types(self):
        self.event["outputs"]["state"] = 1.0
        self.assertTrue(self.result(Domain("n", "number"))["valid"])
        self.event["outputs"]["state"] = True
        self.assertFalse(self.result(Domain("n", "number"))["valid"])
        self.row["state"], self.event["outputs"]["state"] = [True, False], [False, True]
        self.assertTrue(self.result(Domain("s", "set", element=Domain("b", "boolean")))["valid"])
        self.assertFalse(self.result(Domain("s", "sequence", element=Domain("b", "boolean")))["valid"])

    def test_repeated_reads_need_sample_identity_on_both_sides(self):
        self.run["events"].append({**deepcopy(self.event), "id": "e2"})
        self.assertFalse(self.result()["valid"])
        self.run["native_values"]["grant"].append(deepcopy(self.row))
        self.assertFalse(self.result()["valid"])
        self.witness["native"]["keys"].append({"name": "sample", "actual": ["sample"],
                                                "observed": ["outputs", "sample"]})
        for i, (row, event) in enumerate(zip(self.run["native_values"]["grant"], self.run["events"])):
            row["sample"] = event["outputs"]["sample"] = i
        self.assertTrue(self.result()["valid"])


if __name__ == "__main__":
    unittest.main()
