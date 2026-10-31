"""Declaration-byte fast paths retain strict semantic and physical binding checks."""

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from test_multilanguage import project_fixture
from bo_observer.observation.session import GraphSession


class ProjectIdentityTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.folder.name)
        self.project = project_fixture(self.root)
        self.path = self.root / "bo_stategraph/project.json"
        self.original = self.path.read_bytes()
        self.session = GraphSession(self.root)
        self.assertEqual(self.session.binding()["status"], "current")

    def tearDown(self):
        self.session.close()
        self.folder.cleanup()

    def test_same_stat_changed_declaration_is_stale_after_warming_the_fast_path(self):
        changed = dict(self.project, project_id="x" * len(self.project["project_id"]))
        raw = json.dumps(changed, indent=2).encode("utf-8")
        original = json.dumps(self.project, indent=2).encode("utf-8")
        self.path.write_bytes(original)
        self.assertEqual(self.session.binding()["status"], "current")
        before = self.path.stat()
        self.assertEqual(len(original), len(raw))
        self.path.write_bytes(raw)
        os.utime(self.path, ns=(before.st_atime_ns, before.st_mtime_ns))
        result = self.session.binding()
        self.assertEqual(result["status"], "stale")
        self.assertTrue(result["project_changed"])

    def test_semantically_identical_formatting_remains_current_then_changes_are_rejected(
        self,
    ):
        self.path.write_text(json.dumps(self.project, separators=(",", ":")), encoding="utf-8-sig")
        self.assertEqual(self.session.binding()["status"], "current")
        changed = dict(self.project, project_id="different-project")
        self.path.write_text(json.dumps(changed), encoding="utf-8")
        self.assertEqual(self.session.binding()["status"], "stale")
        self.path.write_bytes(self.original)
        self.assertEqual(self.session.binding()["status"], "current")

    def test_missing_or_malformed_declaration_is_stale(self):
        for raw in (b"{", b"\xff"):
            self.path.write_bytes(raw)
            self.assertEqual(self.session.binding()["status"], "stale")
        self.path.unlink()
        self.assertEqual(self.session.binding()["status"], "stale")

    def test_equal_bytes_at_an_outside_definition_target_are_not_accepted(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as outside:
            external = Path(outside) / "project.json"
            external.write_bytes(self.original)
            # The public source reader rejects an absolute/outside definition
            # even if a caller replaces the path with a byte-identical file.
            self.session.path = external
            self.assertEqual(self.session.binding()["status"], "stale")


if __name__ == "__main__":
    unittest.main()
