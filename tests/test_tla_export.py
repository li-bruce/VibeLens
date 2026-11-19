"""Translation checks precede actual TLC; neither substitutes for the other."""

import unittest
from test_analysis_admission import AdmissionTests
from bo_observer.analysis.tla.exporter import export_model


class ExportTests(unittest.TestCase):
    def setUp(self):
        fixture = AdmissionTests()
        fixture.setUp()
        self.contract, self.discovery, self.profile = (
            fixture.contract,
            fixture.discovery,
            fixture.profile,
        )

    def test_complete_deterministic_export_keeps_state_and_transition_ids(self):
        result = export_model(self.contract, self.discovery, self.profile)
        self.assertEqual(
            result, export_model(self.contract, self.discovery, self.profile)
        )
        self.assertEqual(len(result["source_map"]["variables"]), 2)
        self.assertEqual(len(result["source_map"]["actions"]), 8)
        self.assertIn("INVARIANT CheckedProperty", result["cfg"])
        self.assertNotIn("CONSTRAINT", result["cfg"])
        self.assertIn("VLCheck' =", result["tla"])

    def test_original_contract_and_profile_are_unchanged(self):
        from copy import deepcopy

        before = deepcopy((self.contract, self.discovery, self.profile))
        result = export_model(self.contract, self.discovery, self.profile)
        result["contract"]["variables"].clear()
        self.assertEqual(before, (self.contract, self.discovery, self.profile))


if __name__ == "__main__":
    unittest.main()
