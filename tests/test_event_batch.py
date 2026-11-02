"""Batched local ingress preserves identities, strict rejection and snapshot order."""

from copy import deepcopy
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from test_multilanguage import project_fixture
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.observation.session import GraphSession


class GatedSink:
    """Hold real delivery long enough to form a deterministic queue backlog."""

    def __init__(self, sink):
        self.sink = sink
        self.entered = threading.Event()
        self.release = threading.Event()
        self.snapshot_entered = threading.Event()
        self.snapshot_release = threading.Event()
        self.snapshot_release.set()
        self.suffix_entered = threading.Event()
        self.suffix_release = threading.Event()
        self.suffix_release.set()
        self.batches = []

    def ready(self):
        self.entered.set()
        if not self.release.wait(3):
            raise TimeoutError("test sink was not released")

    def __call__(self, value, kind):
        self.ready()
        if kind == "snapshots":
            self.snapshot_entered.set()
            if not self.snapshot_release.wait(3):
                raise TimeoutError("test snapshot was not released")
        if value.get("outputs", {}).get("state") == "done":
            self.suffix_entered.set()
            if not self.suffix_release.wait(3):
                raise TimeoutError("test suffix was not released")
        return self.sink(value, kind)

    def bo_accept_many(self, values):
        self.ready()
        self.batches.append([value["id"] for value in values])
        return self.sink.bo_accept_many(values)


class EventBatchTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.folder.name)
        self.project = project_fixture(self.root)
        self.session = GraphSession(self.root)
        self.probes = []
        self.gates = []

    def tearDown(self):
        for sink in self.gates:
            sink.release.set()
            sink.snapshot_release.set()
            sink.suffix_release.set()
        for probe in self.probes:
            probe.flush(3)
            probe.close()
        self.session.close()
        self.folder.cleanup()

    def probe(self, sink):
        probe = BOProbe(self.project, self.session.manifest["build_id"], sink=sink)
        self.probes.append(probe)
        return probe

    def events(self, count=2):
        values = []
        probe = self.probe(lambda value, kind: values.append(value))
        for _ in range(count):
            probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})
        self.assertTrue(probe.flush(2))
        return values

    def unchanged(self):
        self.assertEqual(self.session.sequence, 0)
        self.assertEqual(self.session.gaps, 0)
        self.assertEqual(self.session.seen, {})
        self.assertEqual(self.session.producers, {})
        self.assertEqual(self.session.bo_open_invocations, {})
        self.assertEqual(self.session.bo_context_evictions, 0)
        self.assertEqual(self.session.history.snapshot(), [])

    def test_same_facts_and_duplicate_receipts_are_preserved(self):
        values = self.events(6)
        delivered = []
        unsubscribe = self.session.history.subscribe(lambda event: delivered.append(event["id"]))
        try:
            receipts = self.session.bo_sink.bo_accept_many(values)
            self.assertTrue(all(receipt["accepted"] for receipt in receipts))
            self.assertEqual(delivered, [value["id"] for value in values])
            stored = self.session.history.snapshot()
            self.assertEqual([value["source_seq"] for value in stored], list(range(1, 7)))
            self.assertEqual([value["inputs"] for value in stored], [v["inputs"] for v in values])
            again = self.session.bo_sink.bo_accept_many(values)
            self.assertTrue(all(receipt.get("duplicate") for receipt in again))
            self.assertEqual(len(self.session.history.snapshot()), 6)
        finally:
            unsubscribe()

    def test_invalid_envelope_never_publishes_the_valid_prefix(self):
        original = self.events()
        for field, value in (("node", "absent"), ("build_id", "wrong-build")):
            values = deepcopy(original)
            values[1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.session.bo_sink.bo_accept_many(values)
            self.unchanged()
        values = deepcopy(original)
        values[1]["outputs"]["undeclared"] = True
        with self.assertRaisesRegex(ValueError, "undeclared"):
            self.session.bo_sink.bo_accept_many(values)
        self.unchanged()

    def test_identity_collision_rejects_the_whole_group(self):
        first = self.events(1)[0]
        second = deepcopy(first)
        second["outputs"]["state"] = "done"
        with self.assertRaisesRegex(ValueError, "identity collision"):
            self.session.bo_sink.bo_accept_many([first, second])
        self.unchanged()

    def test_reordered_sequences_do_not_leak_staged_gap_counters(self):
        values = self.events()
        with self.assertRaisesRegex(ValueError, "reordered"):
            self.session.bo_sink.bo_accept_many(list(reversed(values)))
        self.unchanged()

    def test_cross_run_dependencies_do_not_publish_an_earlier_valid_event(self):
        values = self.events()
        values[0]["run_id"] = "other-run"
        values[1]["depends"] = [{"event": values[0]["id"], "type": "control"}]
        with self.assertRaisesRegex(ValueError, "cross-run"):
            self.session.bo_sink.bo_accept_many(values)
        self.unchanged()

    def test_same_stat_source_edit_during_preflight_rejects_every_event(self):
        values = self.events()
        original = GraphSession._accept_event
        for name, before, after in (
            ("worker.py", b"slots > 0", b"slots > 1"),
            ("bo_stategraph/project.json", b'"fixture"', b'"mixture"'),
            ("intent.json", b"Start", b"Pause"),
        ):
            path = self.root / name
            raw, info = path.read_bytes(), path.stat()
            changed = raw.replace(before, after)
            self.assertNotEqual(changed, raw)
            self.assertEqual(len(changed), len(raw))
            injected = False

            def source_edit(receiver, value):
                nonlocal injected
                result = original(receiver, value)
                if isinstance(receiver.history, list) and not injected:
                    injected = True
                    path.write_bytes(changed)
                    os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
                return result

            try:
                with (
                    self.subTest(path=name),
                    patch.object(GraphSession, "_accept_event", source_edit),
                ):
                    with self.assertRaisesRegex(ValueError, "changed during"):
                        self.session.bo_sink.bo_accept_many(values)
                self.assertTrue(injected)
                self.unchanged()
            finally:
                path.write_bytes(raw)
                os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))

    def test_bounds_and_snapshot_envelopes_cannot_bypass_event_validation(self):
        first = self.events(1)[0]
        for values in ([], [first] * 65, (first,)):
            with self.assertRaises(ValueError):
                self.session.bo_sink.bo_accept_many(values)
        wrong = dict(first, protocol="bo-snapshot/v1")
        with self.assertRaises(ValueError):
            self.session.bo_sink.bo_accept_many([wrong])
        with self.assertRaisesRegex(ValueError, "unknown observation"):
            self.session.bo_sink(first, "unknown")
        self.unchanged()

    def test_worker_preserves_snapshot_barriers_and_complete_recordings(self):
        sink = GatedSink(self.session.bo_sink)
        sink.snapshot_release.clear()
        self.gates.append(sink)
        probe = self.probe(sink)
        self.session.bo_bind_capture(
            scope_setter=probe.bo_set_scope,
            flush_capture=lambda: probe.flush(2),
            health=probe.bo_health,
        )
        identifier = self.session.recordings.start()["id"]
        emitted = [probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})]
        self.assertTrue(sink.entered.wait(2))
        for _ in range(20):
            emitted.append(
                probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})
            )
        evidence = probe.record(
            "advance",
            "change",
            lambda: {"outputs": {"state": "pending"}},
            entity="item",
            attempt="attempt",
            scope="entity",
            revision=1,
        )
        emitted.append(evidence)
        probe.snapshot("item", "pending", {"slots": 1}, 1, evidence)
        for _ in range(4):
            emitted.append(
                probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})
            )
        sink.release.set()
        self.assertTrue(sink.snapshot_entered.wait(2))
        self.assertFalse(probe.flush(0.01), "A deferred snapshot was incorrectly acknowledged")
        sink.snapshot_release.set()
        self.session.recordings.stop()
        saved = self.session.recordings.get(identifier)
        self.assertEqual(saved["status"], "stopped")
        self.assertEqual(saved["gaps"], [])
        self.assertEqual([event["id"] for event in saved["events"]], emitted)
        self.assertIn(evidence, self.session.frames)
        self.assertTrue(any(len(batch) > 1 for batch in sink.batches))
        self.assertTrue(all(len(batch) <= 16 for batch in sink.batches))
        self.assertEqual(probe.bo_health()["errors"], 0)
        self.assertEqual(probe.bo_health()["pending"], 0)

    def test_failed_batch_isolated_to_the_bad_original_wire_envelope(self):
        values = self.events(4)
        sink = GatedSink(self.session.bo_sink)
        self.gates.append(sink)
        probe = self.probe(sink)
        # Intentional wire corruption: valid siblings must still be delivered.
        probe.bo_put("events", values[0])
        self.assertTrue(sink.entered.wait(2))
        values[2]["node"] = "absent"
        for value in values[1:]:
            probe.bo_put("events", value)
        sink.release.set()
        self.assertTrue(probe.flush(2))
        self.assertEqual(probe.bo_health()["errors"], 1)
        self.assertEqual(probe.bo_health()["pending"], 0)
        self.assertEqual(
            [event["id"] for event in self.session.history.snapshot()],
            [value["id"] for index, value in enumerate(values) if index != 2],
        )

    def test_backlog_uses_bounded_groups_and_keeps_every_original_fact(self):
        sink = GatedSink(self.session.bo_sink)
        self.gates.append(sink)
        probe = self.probe(sink)
        emitted = [probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})]
        self.assertTrue(sink.entered.wait(2))
        for _ in range(160):
            emitted.append(
                probe.record("advance", "return", lambda: {"outputs": {"state": "running"}})
            )
        sink.release.set()
        self.assertTrue(probe.flush(3))
        self.assertTrue(any(len(batch) > 16 for batch in sink.batches))
        self.assertTrue(all(len(batch) <= 64 for batch in sink.batches))
        self.assertEqual([event["id"] for event in self.session.history.snapshot()], emitted)
        self.assertEqual(probe.bo_health()["errors"], 0)
        self.assertEqual(probe.bo_health()["dropped"], 0)

    def test_flush_settles_its_snapshot_prefix_under_continuing_traffic(self):
        """Later native requests cannot extend a recording's settlement barrier."""
        gate = GatedSink(self.session.bo_sink)
        gate.release.set()
        gate.snapshot_release.clear()
        self.gates.append(gate)
        gate.suffix_release.clear()
        probe = self.probe(gate)
        evidence = probe.record(
            "advance",
            "change",
            lambda: {"outputs": {"state": "pending"}},
            entity="item",
            attempt="item",
            scope="entity",
            revision=1,
        )
        probe.snapshot("item", "pending", {"slots": 1}, 1, evidence)
        self.assertTrue(gate.snapshot_entered.wait(2))
        result = []
        waiter = threading.Thread(target=lambda: result.append(probe.flush(1)))
        waiter.start()
        deadline = time.monotonic() + 1
        while probe.bo_health()["flush_target"] != 2 and time.monotonic() < deadline:
            threading.Event().wait(0.001)
        try:
            self.assertEqual(probe.bo_health()["flush_target"], 2)
            probe.record("advance", "return", lambda: {"outputs": {"state": "done"}})
            gate.snapshot_release.set()
            self.assertTrue(gate.suffix_entered.wait(2))
            waiter.join(2)
            self.assertEqual(result, [True])
            self.assertGreater(probe.bo_health()["pending"], 0)
            self.assertEqual(probe.bo_health()["errors"], 0)
            self.assertIn(evidence, self.session.frames)
        finally:
            gate.suffix_release.set()
            waiter.join(2)
        self.assertTrue(probe.flush(2))
        self.assertEqual(len(self.session.history.snapshot()), 2)


if __name__ == "__main__":
    unittest.main()
