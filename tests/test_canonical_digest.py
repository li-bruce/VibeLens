"""Model hash reuse must preserve canonical meaning and detect every nested edit."""

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from bo_observer.graph.behavior_model import digest
from bo_observer.graph.canonical_digest import CanonicalDigest
from bo_observer.observation.session import GraphSession
from test_multilanguage import project_fixture


class CanonicalDigestTests(unittest.TestCase):
    def test_repeat_value_reuses_only_the_canonical_result(self):
        compute = Mock(side_effect=digest)
        cached = CanonicalDigest(compute)
        value = {"nodes": [{"id": "file", "labels": ["可共享", None, 3]}]}
        expected = digest(value)
        self.assertEqual(cached(value), expected)
        self.assertEqual(cached(value), expected)
        self.assertEqual(compute.call_count, 1)
        changed = deepcopy(value)
        changed["nodes"][0]["labels"][0] = "已撤销"
        self.assertEqual(cached(changed), digest(changed))
        self.assertNotEqual(cached(changed), expected)
        self.assertEqual(cached(value), expected)

    def test_equal_python_numbers_keep_distinct_json_meanings(self):
        cached = CanonicalDigest(digest)
        values = [1, True, 1.0, 0, False, 0.0, -0.0, None, "1"]
        for value in values:
            model = {"states": [{"initial": value}]}
            self.assertEqual(cached(model), digest(model))

    def test_key_order_and_aliases_do_not_change_canonical_identity(self):
        cached = CanonicalDigest(digest)
        child = {"value": 1}
        models = [
            {"first": child, "second": child},
            {"second": {"value": 1}, "first": {"value": 1}},
        ]
        self.assertEqual(cached(models[0]), cached(models[1]))

    def test_failed_or_unsupported_values_do_not_reuse_an_earlier_result(self):
        cached = CanonicalDigest(digest)
        good = {"value": 1}
        self.assertEqual(cached(good), digest(good))
        with self.assertRaises(TypeError):
            cached({"value": object()})
        cyclic = []
        cyclic.append(cyclic)
        with self.assertRaises(ValueError):
            cached(cyclic)
        self.assertEqual(cached(good), digest(good))

    def test_session_binding_detects_nested_in_memory_mutation_and_restore(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as directory:
            root = Path(directory)
            project_fixture(root)
            session = GraphSession(root)
            try:
                self.assertEqual(session.binding()["status"], "current")
                self.assertEqual(session.binding()["status"], "current")
                node = next(item for item in session.model["nodes"] if item["id"] == "advance")
                fields = node["capture"]["out"]
                before = deepcopy(fields)
                fields["state"] = "boolean"
                report = session.binding()
                self.assertEqual(report["status"], "stale")
                self.assertTrue(report["model_changed"])
                fields.clear()
                fields.update(before)
                self.assertEqual(session.binding()["status"], "current")
            finally:
                session.close()


if __name__ == "__main__":
    unittest.main()
