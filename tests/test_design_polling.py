"""Frequent discussion reads retain exact-byte validation without repeated work."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.web import bo_design
from bo_observer.web.interface_language import set_language


class DesignPollingTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.path = self.root / "discovery.json"
        self.original = (
            ROOT / "skills/vibelens/assets/discovery.concepts.example.json"
        ).read_bytes()
        self.path.write_bytes(self.original)
        self.design = bo_design.BODesign(self.root)

    def test_identical_bytes_are_validated_once_even_for_concurrent_readers(self):
        with patch.object(bo_design, "assess", wraps=bo_design.assess) as assess:
            with ThreadPoolExecutor(max_workers=4) as pool:
                values = list(pool.map(lambda _: self.design.document(), range(12)))
            self.assertEqual(assess.call_count, 1)
        values[0]["networks"].clear()
        self.assertTrue(self.design.document()["networks"])
        self.assertTrue(values[1]["networks"])

    def test_same_size_same_timestamp_invalid_change_cannot_reuse_validation(self):
        self.design.document()
        stamp = self.path.stat()
        changed = self.original.replace(b'"networks"', b'"invalids"', 1)
        self.assertNotEqual(changed, self.original)
        self.assertEqual(len(changed), len(self.original))
        self.path.write_bytes(changed)
        os.utime(self.path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        with self.assertRaisesRegex(ValueError, "Invalid discovery record"):
            self.design.snapshot()
        self.path.write_bytes(self.original)
        self.assertTrue(self.design.snapshot()["available"])
        self.path.unlink()
        self.assertFalse(self.design.snapshot()["available"])

    def test_focus_and_language_are_fresh_when_discovery_bytes_are_unchanged(self):
        initial = self.design.snapshot()
        folder = self.root / "bo_stategraph/config"
        folder.mkdir(parents=True, exist_ok=True)
        focus = folder / "design-focus.json"
        focus.write_text(
            json.dumps({"schema": 1, "nodes": ["new-focus"], "label": "Current"}), encoding="utf-8"
        )
        set_language(self.root, "zh-CN", "Current test conversation")
        changed = self.design.snapshot()
        self.assertEqual(changed["nodes"], ["new-focus"])
        self.assertEqual(changed["locale"], "zh-CN")
        self.assertNotEqual(changed["revision"], initial["revision"])
        focus.write_text('{"schema":2,"nodes":[],"label":""}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "focus configuration"):
            self.design.snapshot()


if __name__ == "__main__":
    unittest.main()
