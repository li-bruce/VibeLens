"""Static graph rendering work cannot hold the native event-admission lock."""

from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
import test_capture_settlement as fixture


class ObservationDisplayWorkTests(unittest.TestCase):
    setUp = fixture.CaptureSettlementTests.setUp
    tearDown = fixture.CaptureSettlementTests.tearDown
    event = fixture.CaptureSettlementTests.event

    def check_copy(self, reader):
        """Hold only a static copy, and prove a real probe can still be admitted."""
        entered, release = threading.Event(), threading.Event()
        errors, views = [], []
        original = self.session._view_model

        def copy_model():
            entered.set()
            if not release.wait(5):
                raise TimeoutError("Test did not release the static copy")
            return original()

        def inspect():
            try:
                views.append(reader())
            except BaseException as error:
                errors.append(str(error))

        with patch.object(self.session, "_view_model", side_effect=copy_model):
            worker = threading.Thread(target=inspect)
            worker.start()
            try:
                self.assertTrue(entered.wait(3))
                emitted = self.event()
                self.assertTrue(
                    self.probe.flush(0.5), "Static declaration copy blocked native admission"
                )
                self.assertEqual(self.session.history.snapshot()[-1]["id"], emitted)
            finally:
                release.set()
                worker.join(5)
        self.assertEqual(errors, [])
        self.assertFalse(worker.is_alive())
        views[0]["model"]["nodes"][0]["label"] = "Local display edit"
        self.assertNotEqual(self.session.model["nodes"][0]["label"], "Local display edit")

    def test_recording_catalog_copy_preserves_event_admission(self):
        self.check_copy(self.session.recording_version_context)

    def test_live_view_copy_preserves_event_admission(self):
        self.check_copy(self.session.view)


if __name__ == "__main__":
    unittest.main()
