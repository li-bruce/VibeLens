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

    def test_metadata_reuses_validated_revision_without_cloning_the_document(self):
        doc = self.design.document()
        folder = self.root / "bo_stategraph/config"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "design-focus.json").write_text(
            json.dumps(
                {
                    "schema": 1,
                    "nodes": [],
                    "label": "Current",
                    "discovery_revision": bo_design.bo_digest(doc),
                }
            ),
            encoding="utf-8",
        )
        with patch.object(bo_design, "deepcopy", side_effect=AssertionError("full document copy")):
            self.assertFalse(self.design.snapshot()["stale"])
        doc["project_id"] = "changed-project"
        self.path.write_text(json.dumps(doc), encoding="utf-8")
        self.assertTrue(self.design.snapshot()["stale"])

    def test_server_primes_design_before_accepting_capture_traffic(self):
        # Startup ordering is deterministic; no machine-dependent timing limit.
        sys.path.insert(0, str(ROOT / "tools"))
        from test_multilanguage import project_fixture
        from bo_observer import service

        project_fixture(self.root)
        session = service.GraphSession(self.root)
        self.addCleanup(session.close)
        with patch.object(bo_design, "assess", wraps=bo_design.assess) as assess:
            original_server = service.BOHTTPServer.__init__

            def listen(server, *args, **kwargs):
                self.assertEqual(assess.call_count, 1, "Assess before opening the listener")
                return original_server(server, *args, **kwargs)

            with patch.object(service.BOHTTPServer, "__init__", listen):
                server = service.make_server(session, port=0)
            self.addCleanup(server.server_close)
            session.web.design.snapshot()
            self.assertEqual(assess.call_count, 1, "First poll must reuse validated bytes")

    def test_invalid_optional_draft_keeps_its_error_without_disabling_valid_runtime(self):
        sys.path.insert(0, str(ROOT / "tools"))
        from test_multilanguage import project_fixture
        from bo_observer import service

        project_fixture(self.root)
        self.path.write_text('{"schema":"invalid"}', encoding="utf-8")
        session = service.GraphSession(self.root)
        self.addCleanup(session.close)
        server = service.make_server(session, port=0)
        self.addCleanup(server.server_close)
        self.assertEqual(session.binding()["status"], "current")
        with self.assertRaisesRegex(ValueError, "Invalid discovery record"):
            session.web.design.snapshot()

    def test_reloaded_build_is_prepared_before_the_first_metadata_request(self):
        sys.path.insert(0, str(ROOT / "tools"))
        from test_multilanguage import project_fixture
        from bo_observer import service

        project_fixture(self.root)
        session = service.GraphSession(self.root)
        self.addCleanup(session.close)
        server = service.make_server(session, port=0)
        self.addCleanup(server.server_close)
        source = self.root / "worker.py"
        source.write_text(source.read_text() + "\n# Source-only iteration\n", encoding="utf-8")
        with patch.object(bo_design, "assess", wraps=bo_design.assess) as assess:
            self.assertTrue(server.bo_reload())
            self.assertEqual(assess.call_count, 1, "Prepare before publishing the new session")
            self.assertIsNot(server.bo_session, session)
            server.bo_session.web.design.snapshot()
            self.assertEqual(assess.call_count, 1, "First poll must reuse that preparation")


if __name__ == "__main__":
    unittest.main()
