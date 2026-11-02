"""Recording boundaries drain actual async probe queues and preserve failures."""

from pathlib import Path
import os
import sys
import tempfile
import threading
import unittest
from copy import deepcopy
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from test_multilanguage import project_fixture
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.observation.session import GraphSession


class CaptureSettlementTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.folder.name)
        self.project = project_fixture(self.root)
        self.session = GraphSession(self.root)
        self.gate = threading.Event()
        self.gate.set()

        def receive(value, kind):
            if not self.gate.wait(3):
                raise TimeoutError("Test receiver was not released")
            return self.session.event(value) if kind == "events" else self.session.snapshot(value)

        self.probe = BOProbe(self.project, self.session.manifest["build_id"], sink=receive)
        self.session.bo_bind_capture(
            scope_setter=self.probe.bo_set_scope,
            flush_capture=lambda: self.probe.flush(2),
            health=self.probe.bo_health,
        )

    def tearDown(self):
        self.gate.set()
        self.probe.flush(3)
        self.probe.close()
        self.session.close()
        self.folder.cleanup()

    def event(self):
        return self.probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})

    def test_stop_drains_queued_events_before_freezing_the_saved_interval(self):
        identifier = self.session.recordings.start()["id"]
        self.gate.clear()
        emitted = [self.event() for _ in range(40)]
        self.assertLess(len(self.session.history.snapshot()), len(emitted))
        release = threading.Timer(0.05, self.gate.set)
        release.start()
        try:
            self.session.recordings.stop()
        finally:
            release.join()
        saved = self.session.recordings.get(identifier)
        self.assertEqual([event["id"] for event in saved["events"]], emitted)
        self.assertEqual(
            saved["producer_settlement"],
            {"flushed": True, "target": 40, "completed": 40, "submitted": 40, "pending": 0},
        )
        self.assertEqual(saved["gaps"], [])
        self.assertEqual(saved["status"], "stopped")

    def test_start_drains_old_work_into_context_instead_of_the_new_interval(self):
        emitted = [self.event() for _ in range(4)]
        identifier = self.session.recordings.start()["id"]
        self.session.recordings.stop()
        saved = self.session.recordings.get(identifier)
        self.assertEqual([event["id"] for event in saved["context"]["events"]], emitted)
        self.assertEqual(saved["events"], [])

    def test_saving_a_recording_does_not_block_event_admission(self):
        identifier = self.session.recordings.start()["id"]
        first = self.event()
        self.assertTrue(self.probe.flush(2))
        entered, release = threading.Event(), threading.Event()
        writer = self.session.recordings._write

        def gated_write(value):
            entered.set()
            if not release.wait(3):
                raise TimeoutError("test writer was not released")
            return writer(value)

        with patch.object(self.session.recordings, "_write", side_effect=gated_write):
            sampler = threading.Thread(target=self.session.recordings.sample)
            sampler.start()
            try:
                self.assertTrue(entered.wait(2))
                second = self.event()
                self.assertTrue(
                    self.probe.flush(0.5), "Disk serialization blocked the incoming queue"
                )
            finally:
                release.set()
                sampler.join(3)
        self.session.recordings.stop()
        saved = self.session.recordings.get(identifier)
        self.assertEqual([e["id"] for e in saved["events"]], [first, second])
        self.assertEqual(saved["gaps"], [])
        self.assertEqual(self.probe.bo_health()["dropped"], 0)

    def test_checkpoint_and_metadata_reads_do_not_rescan_the_project_tree(self):
        identifier = self.session.recordings.start()["id"]
        expected = self.event()
        self.assertTrue(self.probe.flush(2))
        with patch.object(
            self.session.web.code_graph, "view", side_effect=AssertionError("source tree rescan")
        ):
            self.session.recordings.sample()
            self.session.recordings.stop()
            with patch.object(
                self.session.graph, "bo_instances", side_effect=AssertionError("runtime assembled")
            ):
                self.assertIsNone(self.session.recordings.list()["active"])
                saved = self.session.recordings.get(identifier)
            self.assertEqual([event["id"] for event in saved["events"]], [expected])
            self.assertGreater(saved["context"]["project_structure"]["loaded_nodes"], 0)
            self.assertEqual(saved["gaps"], [])
        self.assertGreater(self.session.view()["project_structure"]["loaded_nodes"], 0)

    def test_runtime_reader_preserves_existing_no_argument_view_overrides(self):
        class NativeSession(GraphSession):
            def view(self):
                result = super().view()
                result["machine"]["adapter_projection"] = "native"
                return result

        self.session.close()
        self.session = NativeSession(self.root)
        self.session.bo_bind_capture(
            scope_setter=self.probe.bo_set_scope,
            flush_capture=lambda: self.probe.flush(2),
            health=self.probe.bo_health,
        )
        identifier = self.session.recordings.start()["id"]
        with patch.object(
            self.session.web.code_graph, "view", side_effect=AssertionError("source tree rescan")
        ):
            self.session.recordings.sample()
            self.session.recordings.stop()
        saved = self.session.recordings.get(identifier)
        self.assertEqual(saved["context"]["machine"]["adapter_projection"], "native")
        self.assertEqual(saved["final"]["machine"]["adapter_projection"], "native")
        self.assertGreater(saved["context"]["project_structure"]["loaded_nodes"], 0)
        self.assertEqual(saved["gaps"], [])

    def test_changed_source_during_scope_selection_rejects_recording_start(self):
        path = self.root / "worker.py"
        original = path.read_bytes()
        before = self.session.recordings.bo_scope_setter

        def change_source(nodes):
            before(nodes)
            path.write_bytes(original + b"\n# Changed during capture selection\n")

        self.session.recordings.bo_scope_setter = change_source
        try:
            with self.assertRaisesRegex(ValueError, "changed while recording started"):
                self.session.recordings.start()
            self.assertIsNone(self.session.recordings.active)
            self.assertIsNone(self.probe.bo_capture_nodes)
        finally:
            path.write_bytes(original)

    def test_large_view_copy_has_one_boundary_without_holding_admission_lock(self):
        first = self.event()
        self.assertTrue(self.probe.flush(2))
        entered, release = threading.Event(), threading.Event()
        views = []

        def copy_payload(value):
            if isinstance(value, list) and value and value[0].get("id") == first:
                entered.set()
                if not release.wait(3):
                    raise TimeoutError("test view copy was not released")
            return deepcopy(value)

        with patch("bo_observer.observation.session.deepcopy", side_effect=copy_payload):
            reader = threading.Thread(target=lambda: views.append(self.session.view()))
            reader.start()
            try:
                self.assertTrue(entered.wait(2))
                self.event()
                self.assertTrue(
                    self.probe.flush(0.5), "View payload copying held the admission lock"
                )
            finally:
                release.set()
                reader.join(3)
        self.assertEqual(len(views), 1)
        self.assertEqual(views[0]["health"]["attempted"], 1)
        self.assertEqual([e["id"] for e in views[0]["events"]], [first])
        views[0]["events"][0]["outputs"]["state"] = "edited view"
        self.assertEqual(self.session.history.snapshot()[0]["outputs"]["state"], "running")

    def test_timed_out_stop_retains_partial_evidence_as_interrupted(self):
        ready = [True]
        self.session.recordings.bo_capture_flush = lambda: ready[0]
        identifier = self.session.recordings.start()["id"]
        self.gate.clear()
        self.event()
        ready[0] = False
        self.session.recordings.stop()
        saved = self.session.recordings.get(identifier)
        self.assertEqual(saved["status"], "interrupted")
        self.assertFalse(saved["producer_settlement"]["flushed"])
        self.assertTrue(any("did not drain" in gap for gap in saved["gaps"]))

    def test_capture_failure_is_not_a_clean_stopped_recording(self):
        identifier = self.session.recordings.start()["id"]
        self.probe.record("advance", "return", lambda: {"outputs": {"state": object()}})
        self.session.recordings.stop()
        saved = self.session.recordings.get(identifier)
        self.assertEqual(saved["status"], "interrupted")
        self.assertTrue(any("capture or transport failed" in gap for gap in saved["gaps"]))

    def test_late_exception_capture_reports_its_boundary_without_leaking_message(self):
        identifier = self.session.recordings.start()["id"]
        # Python clears an except target before the outer context exits. This
        # reproduces a real HTTP adapter bug without inventing a business event.
        try:
            raise ValueError("Private application details")
        except ValueError as error:
            values = lambda: {"outputs": {"state": str(error)}}
        self.probe.record("advance", "return", values)
        self.session.recordings.stop()
        saved = self.session.recordings.get(identifier)
        self.assertEqual(saved["status"], "interrupted")
        self.assertEqual(
            self.probe.bo_health()["last_error"],
            {"stage": "capture", "type": "NameError", "node": "advance", "phase": "return"},
        )
        self.assertNotIn("Private application details", str(saved))

    def test_focused_capture_filters_before_building_and_restores_full_capture(self):
        identifier = self.session.recordings.start(scope={"mode": "focused", "roots": ["advance"]})[
            "id"
        ]
        allowed = self.session.recordings.active["capture"]["nodes"]
        omitted = next(
            node["id"] for node in self.project["model"]["nodes"] if node["id"] not in allowed
        )

        def must_not_run():
            self.fail("An excluded capture builder was evaluated")

        self.assertIsNone(self.probe.record(omitted, "enter", must_not_run))
        expected = self.event()
        self.session.recordings.stop()
        saved = self.session.recordings.get(identifier)
        self.assertEqual([event["id"] for event in saved["events"]], [expected])
        self.assertEqual(self.probe.bo_health()["filtered"], 1)
        self.assertEqual(self.probe.bo_health()["enqueued"], 1)
        self.assertEqual(saved["gaps"], [])
        self.assertIsNone(self.probe.bo_capture_nodes)
        self.assertIsNotNone(self.probe.record(omitted, "enter", lambda: {}))

    def test_disabled_producer_does_not_create_an_empty_successful_recording(self):
        self.probe.bo_enabled = False
        with self.assertRaisesRegex(ValueError, "disabled"):
            self.session.recordings.start()
        self.assertIsNone(self.session.recordings.active)
        self.probe.bo_enabled = True

    def test_controller_and_scope_arguments_are_validated(self):
        with self.assertRaisesRegex(ValueError, "known node"):
            self.probe.bo_set_scope(["missing"])
        with self.assertRaisesRegex(ValueError, "known node"):
            self.probe.bo_set_scope("advance")
        with self.assertRaisesRegex(ValueError, "callbacks"):
            self.session.bo_bind_capture(scope_setter=None, flush_capture=None, health=None)
        self.session.recordings.start()
        with self.assertRaisesRegex(ValueError, "during recording"):
            self.session.bo_bind_capture(
                scope_setter=self.probe.bo_set_scope,
                flush_capture=lambda: True,
                health=self.probe.bo_health,
            )
        self.session.recordings.stop()

    def test_same_size_same_timestamp_source_edit_still_rejects_runtime_events(self):
        path = self.root / "worker.py"
        before = path.stat()
        original = path.read_bytes()
        changed = original.replace(b"running", b"waiting", 1)
        self.assertNotEqual(original, changed)
        self.assertEqual(len(original), len(changed))
        path.write_bytes(changed)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(self.session.binding()["status"], "stale")
        self.event()
        self.assertTrue(self.probe.flush(2))
        self.assertEqual(self.session.history.snapshot(), [])
        self.assertEqual(self.probe.bo_errors, 1)


if __name__ == "__main__":
    unittest.main()
