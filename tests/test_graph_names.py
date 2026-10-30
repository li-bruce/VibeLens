"""Optional explanations are bounded display metadata, not executable aliases."""

import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_contracts import validate_chart, validate_names
from bo_observer.protocol import schema_check


class GraphNameTests(unittest.TestCase):
    def setUp(self):
        self.model = json.loads(
            (
                ROOT / "docs/review/recording-timeline/real-project-completion/v2-recording.json"
            ).read_text(encoding="utf-8")
        )["context"]["model"]

    def test_names_leave_execution_unchanged(self):
        before = copy.deepcopy(self.model)
        self.model["presentation"]["names"] = {
            "nodes": {"login": {"en": "Sign in", "zh-CN": "登录"}},
            "states": {"shared": "Shared with recipients"},
        }
        schema_check(self.model, "model")
        validate_chart(self.model)
        self.assertEqual(self.model["machine"], before["machine"])
        self.assertEqual(self.model["nodes"], before["nodes"])
        self.assertEqual(self.model["edges"], before["edges"])

    def test_invalid_metadata_is_rejected(self):
        for names in [
            {"source": {}},
            {"nodes": []},
            {"nodes": {"login": ""}},
            {"nodes": {"login": "x" * 61}},
            {"edges": {"e": "a\nb"}},
            {"states": {"s": {"de": "State"}}},
            {"nodes": {"login": ["Label"]}},
            {"events": {"": "Event"}},
        ]:
            with self.subTest(names=names):
                self.model["presentation"]["names"] = names
                with self.assertRaises(ValueError):
                    validate_names(self.model)
                with self.assertRaises(ValueError):
                    schema_check(self.model, "model")

    def test_old_model_still_loads(self):
        validate_chart(self.model)


if __name__ == "__main__":
    unittest.main()
