"""Loaded protocol reuse still validates each envelope and live capture contract."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from test_multilanguage import project_fixture
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.observation.session import GraphSession
from bo_observer.protocol import schema_check, validate_event


class ProtocolReuseTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.folder.name)
        self.project = project_fixture(self.root)
        self.session = GraphSession(self.root)
        received = []
        probe = BOProbe(
            self.project,
            self.session.manifest["build_id"],
            sink=lambda event, kind: received.append(event),
        )
        probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})
        self.assertTrue(probe.flush(2))
        probe.close()
        self.event = received[0]

    def tearDown(self):
        self.session.close()
        self.folder.cleanup()

    def test_loaded_schema_needs_no_per_event_disk_read_and_still_rejects(self):
        schema_check(self.event, "event")
        with patch.object(Path, "read_text", side_effect=AssertionError("Schema read per event")):
            for _ in range(32):
                schema_check(self.event, "event")
            with self.assertRaises(ValueError):
                schema_check({**self.event, "phase": "invented"}, "event")
            with self.assertRaises(ValueError):
                schema_check({**self.event, "seq": float("nan")}, "event")
        self.assertEqual(self.event["outputs"], {"state": "running"})

    def test_live_model_capture_checks_are_not_cached_with_the_protocol(self):
        validate_event(self.event, self.project, self.session.manifest["build_id"])
        project = deepcopy(self.project)
        node = next(node for node in project["model"]["nodes"] if node["id"] == "advance")
        node["capture"]["out"]["state"] = "boolean"
        with self.assertRaises(ValueError):
            validate_event(self.event, project, self.session.manifest["build_id"])
        with self.assertRaisesRegex(ValueError, "undeclared"):
            validate_event(
                {**self.event, "outputs": {"extra": True}},
                self.project,
                self.session.manifest["build_id"],
            )
        with self.assertRaisesRegex(ValueError, "unknown event node"):
            validate_event(
                {**self.event, "node": "invented"}, self.project, self.session.manifest["build_id"]
            )

    def test_concurrent_envelopes_share_no_validation_state(self):
        def validate(index):
            value = {**self.event, "phase": "invented" if index % 2 else "return"}
            try:
                schema_check(value, "event")
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=8) as workers:
            actual = list(workers.map(validate, range(128)))
        self.assertEqual(actual, [not index % 2 for index in range(128)])


if __name__ == "__main__":
    unittest.main()
