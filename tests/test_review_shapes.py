"""Malformed iteration reviews fail as diagnostics, never as attribute errors."""

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tests")]

import cochange_fixture
from bo_observer.behavior.iteration import protected_errors
from bo_observer.workflow.change_sync import review_errors
from test_behavior_evidence import snapshot


class ReviewShapeTests(unittest.TestCase):
    def test_domain_guard_rejects_malformed_requirement_reasons(self):
        before = snapshot()
        before["requested_requirements"] = ["R1"]
        for value in (None, [], "approved", {"R1": []}, {"R1": 1}, {"R1": " "}):
            with self.subTest(value=value):
                result = protected_errors(before, deepcopy(before), {"requirement_changes": value})
                self.assertTrue(result)
                self.assertEqual(result[0]["code"], "invalid_requirement_change_review")

    def test_review_shape_is_checked_before_other_review_consumers(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            for value in (
                [],
                None,
                {"requirement_changes": []},
                {"decisions": []},
                {"decisions": {"business": []}},
                {"excluded_symbols": []},
                {"excluded_symbols": {"a.py::run": False}},
            ):
                with self.subTest(value=value):
                    (root / "review.json").write_text(json.dumps(value), encoding="utf-8")
                    result = review_errors(root, {}, {}, {})
                    self.assertTrue(result)
                    self.assertEqual(result[-1]["code"], "invalid_change_review")
                    self.assertIn("path", result[-1])

    def test_inspect_and_verify_report_the_same_invalid_review(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = cochange_fixture.prepare(Path(folder) / "app")
            code, result = cochange_fixture.sync(
                root,
                "begin",
                "--change",
                ".stategraph/review-shape",
                "--request",
                "Check malformed review diagnostics without changing native behavior.",
            )
            self.assertEqual(code, 0, result)
            (root / ".stategraph/review-shape/review.json").write_text("[]", encoding="utf-8")
            for command in ("inspect", "verify"):
                with self.subTest(command=command):
                    code, result = cochange_fixture.sync(root, command)
                    self.assertNotEqual(code, 0)
                    self.assertIn("invalid_change_review", json.dumps(result))
            self.assertFalse((root / ".stategraph/review-shape/accepted.json").exists())


if __name__ == "__main__":
    unittest.main()
