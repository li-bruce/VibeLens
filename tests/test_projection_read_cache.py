"""Projection read caches reuse parsing only for exactly matching current bytes."""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from test_multilanguage import project_fixture
from bo_observer.code_graph.service import CodeGraph


class ProjectionReadCacheTests(unittest.TestCase):
    def test_unchanged_model_reuses_validation_without_sharing_mutable_payload(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            project_fixture(root)
            graph = CodeGraph(root, persist=False)
            _, first = graph.inputs()
            with patch(
                "bo_observer.code_graph.service.model_from_value",
                side_effect=AssertionError("Unchanged declaration reparsed"),
            ):
                _, second = graph.inputs()
            self.assertEqual(first, second)
            second["nodes"][0]["label"] = "Local display edit"
            self.assertEqual(graph.inputs()[1], first)

    def test_same_size_same_timestamp_invalid_model_cannot_reuse_old_validation(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            project = project_fixture(root)
            graph = CodeGraph(root, persist=False)
            graph.inputs()
            path = root / "bo_stategraph/project.json"
            original, stamp = path.read_bytes(), path.stat()
            old = project["selection"]["mode"].encode()
            changed = original.replace(b'"' + old + b'"', b'"' + b"x" * len(old) + b'"', 1)
            self.assertNotEqual(original, changed)
            self.assertEqual(len(original), len(changed))
            path.write_bytes(changed)
            os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            with self.assertRaises(ValueError):
                graph.inputs()


if __name__ == "__main__":
    unittest.main()
