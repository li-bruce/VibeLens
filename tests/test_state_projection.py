"""State projections must enumerate the same states as the executable declaration."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/vibelens/scripts"))
from bo_contracts import validate_runtime_definition


class StateProjectionTests(unittest.TestCase):
    def chart(self):
        return {
            "engine": "transitions.HierarchicalMachine", "version": "0.9.3",
            "states": [{"name": "review", "initial": "pending", "children": ["pending", "done"]}],
            "values": ["review", "review_pending", "review_done"],
            "initial": "review", "context": {}, "events": {}, "guards": {}, "transitions": [],
        }

    def test_complete_hierarchical_projection_is_accepted(self):
        validate_runtime_definition(self.chart())

    def test_missing_or_invented_state_is_rejected(self):
        for values in (["review_pending", "review_done"], ["review", "review_pending"],
                       ["review", "review_pending", "review_done", "imagined"]):
            with self.subTest(values=values):
                chart = deepcopy(self.chart())
                chart["values"] = values
                with self.assertRaisesRegex(ValueError, "exactly cover executable states"):
                    validate_runtime_definition(chart)


if __name__ == "__main__":
    unittest.main()
