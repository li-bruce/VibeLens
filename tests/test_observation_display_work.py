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

    def test_recording_catalog_needs_identity_not_a_materialized_graph(self):
        """Listing or reading an interval must not rebuild its static context."""
        identifier = self.session.recordings.start()["id"]
        emitted = self.event()
        self.assertTrue(self.probe.flush(2))
        self.session.recordings.stop()
        with patch.object(
            self.session, "_view_model", side_effect=AssertionError("Full model was copied")
        ), patch.object(
            self.session.bo_concept_context,
            "view",
            side_effect=AssertionError("Concept graph was copied"),
        ), patch.object(
            self.session.graph,
            "bo_instances",
            side_effect=AssertionError("Runtime was copied"),
        ):
            catalog = self.session.recordings.list()
            saved = self.session.recordings.get(identifier)
            self.assertIsNone(catalog["active"])
            self.assertEqual([event["id"] for event in saved["events"]], [emitted])
            self.assertEqual(saved["context"]["manifest"]["build_id"], self.probe.bo_build)
            saved["context"]["model"]["nodes"][0]["label"] = "Caller edit"
            self.assertNotEqual(
                self.session.recordings.get(identifier)["context"]["model"]["nodes"][0]["label"],
                "Caller edit",
            )

    def test_view_and_recording_keep_independent_event_payloads(self):
        """Display edits cannot change retained observations or the saved interval."""
        identifier = self.session.recordings.start()["id"]
        emitted = self.event()
        self.assertTrue(self.probe.flush(2))
        view = self.session.view()
        event = next(item for item in view["events"] if item["id"] == emitted)
        original = dict(event)
        event["outputs"]["caller_edit"] = ["changed"]
        self.session.recordings.stop()
        saved = self.session.recordings.get(identifier)
        retained = next(item for item in saved["events"] if item["id"] == emitted)
        self.assertNotIn("caller_edit", retained["outputs"])
        self.assertEqual(retained["node"], original["node"])
        self.assertNotIn("caller_edit", self.session.history.snapshot()[-1]["outputs"])


if __name__ == "__main__":
    unittest.main()
