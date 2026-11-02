"""Source discovery skips generated trees but still inspects ordinary exclusions."""

import os
import ast
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.workflow.bo_sync import source_inventory


class SourceInventoryWalkTests(unittest.TestCase):
    def test_generated_directories_are_pruned_before_descending(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            (root / "worker.py").write_text("def run():\n    return 1\n", encoding="utf-8")
            blocked = {root / name for name in ("node_modules", ".stategraph", ".validation")}
            for directory in blocked:
                directory.mkdir()
                (directory / "hidden.py").write_text("def ignored(): pass\n", encoding="utf-8")
            scanned = []
            original = os.scandir

            def inspect(directory):
                path = Path(directory)
                scanned.append(path)
                if path in blocked:
                    raise AssertionError("Generated tree was traversed: " + str(path))
                return original(directory)

            with patch("os.scandir", side_effect=inspect):
                result = source_inventory(root, {"source_scope": {"roots": ["."]}})
            self.assertEqual(list(result["files"]), ["worker.py"])
            self.assertTrue(scanned)
            self.assertFalse(set(scanned) & blocked)

    def test_ordinary_exclusion_cannot_hide_application_or_route(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            directory = root / "private"
            directory.mkdir()
            (directory / "service.py").write_text(
                "@app.get('/hidden')\ndef hidden():\n    return 1\n", encoding="utf-8"
            )
            result = source_inventory(
                root,
                {
                    "source_scope": {
                        "roots": ["."],
                        "exclude": {"private/**": "Reviewed excluded directory"},
                    }
                },
            )
            self.assertEqual(result["files"], {})
            self.assertEqual(result["excluded_implementations"], ["private/service.py"])
            self.assertIn("private/service.py", result["excluded_entrypoints"])

    def test_cached_inspection_keeps_errors_and_rereads_same_stat_source(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            (root / "private").mkdir()
            path = root / "private/service.py"
            body = b"@app.get('/hidden')\ndef hidden():\n    return 1\n"
            path.write_bytes(body)
            stamp = path.stat()
            cfg = {"source_scope": {"roots": ["."], "exclude": {"private/**": "Review"}}}
            cache = {}
            first = source_inventory(root, cfg, inspection_cache=cache)
            with patch.object(
                ast, "parse", side_effect=AssertionError("Unchanged source reparsed")
            ):
                second = source_inventory(root, cfg, inspection_cache=cache)
            self.assertEqual(first, second)
            self.assertIn("private/service.py", second["excluded_entrypoints"])
            path.write_bytes(body.replace(b"/hidden", b"/toggle"))
            os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            third = source_inventory(root, cfg, inspection_cache=cache)
            self.assertNotEqual(first["excluded_entrypoints"], third["excluded_entrypoints"])
            self.assertEqual(third["excluded_implementations"], ["private/service.py"])


if __name__ == "__main__":
    unittest.main()
