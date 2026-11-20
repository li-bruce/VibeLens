"""Repeated reads retain evidence without inventing a new native state revision."""

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from test_multilanguage import project_fixture
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.observation.session import GraphSession
from bo_observer.observation.snapshot_reads import matches_current_read
from test_model_networks import write_project


class SnapshotReadTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.folder.name)
        self.project = project_fixture(self.root)
        self.session = GraphSession(self.root)
        self.receipts = []
        self.envelopes = []

        def collect(value, kind):
            self.envelopes.append((kind, deepcopy(value)))
            result = self.session.bo_sink(value, kind)
            self.receipts.append((kind, result))
            return result

        self.probe = BOProbe(self.project, self.session.manifest["build_id"], sink=collect)

    def tearDown(self):
        self.probe.close()
        self.session.close()
        self.folder.cleanup()

    def observe(self, state="pending", revision=0, *, phase="read", context=None, **options):
        """Use a real producer event and its matching complete snapshot."""
        event_id = self.probe.record(
            "advance", phase, lambda: {"outputs": {"state": state}}, revision=revision
        )
        self.probe.snapshot(
            "task:1",
            state,
            {"slots": 1} if context is None else context,
            revision,
            event_id,
            **options,
        )
        self.assertTrue(self.probe.flush(3))
        self.assertEqual(self.receipts[-1][0], "snapshots")
        return event_id, self.receipts[-1][1]

    def test_new_read_keeps_same_revision_and_independent_frame(self):
        first, initial = self.observe()
        self.assertTrue(initial["accepted"])
        original = deepcopy(self.session.graph.bo_instances())
        second, repeated = self.observe()
        self.assertNotEqual(first, second)
        self.assertTrue(repeated["accepted"], repeated)
        self.assertEqual(self.session.graph.bo_instances(), original)
        self.assertEqual(set(self.session.frames), {first, second})
        frame = self.session.frames[second][0]
        self.assertEqual(frame["revision"], 0)
        self.assertEqual(frame["machine"]["journal"], [])
        self.assertEqual(frame["machine"]["current"], "pending")
        self.assertEqual(self.probe.bo_health()["errors"], 0)

    def test_read_after_commit_does_not_repeat_transition(self):
        self.observe()
        committed, result = self.observe(
            "running", 1, phase="commit", event="start", guards={"available": True}, payload={}
        )
        self.assertTrue(result["accepted"])
        original = deepcopy(self.session.graph.bo_instances())
        read, result = self.observe("running", 1)
        self.assertTrue(result["accepted"], result)
        self.assertEqual(self.session.graph.bo_instances(), original)
        self.assertEqual(len(self.session.frames[committed][0]["machine"]["journal"]), 1)
        self.assertEqual(self.session.frames[read][0]["machine"]["journal"], [])

    def test_same_revision_conflicting_content_or_new_transition_stays_rejected(self):
        self.observe()
        for args, options in (
            (("running", 0), {}),
            (("pending", 0), {"context": {"slots": 2}}),
            (("pending", 0), {"configuration": {"phase": "pending"}}),
            (("pending", 0), {"event": "start", "guards": {"available": True}}),
            (("pending", 0), {"phase": "commit"}),
        ):
            with self.subTest(args=args, options=options):
                event_id, result = self.observe(*args, **options)
                self.assertFalse(result["accepted"], result)
                self.assertNotIn(event_id, self.session.frames)
        self.assertEqual(self.session.graph.bo_instances()[0]["observed"]["revision"], 0)

    def test_old_read_cannot_replace_a_newer_revision(self):
        self.observe()
        self.observe("running", 1, phase="commit", event="start", guards={"available": True})
        event_id, result = self.observe("pending", 0)
        self.assertFalse(result["accepted"])
        self.assertNotIn(event_id, self.session.frames)
        self.assertEqual(self.session.graph.bo_instances()[0]["observed"]["revision"], 1)

    def test_retried_read_does_not_duplicate_frame_or_bytes(self):
        self.observe()
        self.observe()
        before = (len(self.session.frames), self.session.frame_bytes)
        value = self.envelopes[-1][1]
        receipt = self.session.snapshot(value)
        self.assertTrue(receipt["duplicate"], receipt)
        self.assertEqual((len(self.session.frames), self.session.frame_bytes), before)

    def test_recording_retains_reads_and_only_one_real_transition(self):
        self.session.bo_bind_capture(
            scope_setter=self.probe.bo_set_scope,
            flush_capture=lambda: self.probe.flush(3),
            health=self.probe.bo_health,
        )
        recording = self.session.recordings.start()["id"]
        first, _ = self.observe()
        second, _ = self.observe()
        committed, _ = self.observe(
            "running",
            1,
            phase="commit",
            event="start",
            guards={"available": True},
        )
        last, _ = self.observe("running", 1)
        self.session.recordings.stop()
        saved = self.session.recordings.get(recording)
        self.assertEqual(saved["gaps"], [])
        frames = {f["event_id"]: f for f in saved["runtime_frames"]["frames"]}
        self.assertEqual(set(frames), {first, second, committed, last})
        self.assertEqual(sum(len(f["machine"]["journal"]) for f in frames.values()), 1)
        self.assertEqual(
            [frames[e]["revision"] for e in (first, second, committed, last)], [0, 0, 1, 1]
        )

    def test_read_match_requires_valid_prior_state_and_exact_json_types(self):
        self.observe()
        entry = self.session.graph.bo_instances()[0]
        value = deepcopy(entry["observed"])
        self.assertTrue(matches_current_read(value, {"phase": "read"}, entry))
        for status in ("partial", "mismatch", "unknown"):
            self.assertFalse(
                matches_current_read(value, {"phase": "read"}, {**entry, "status": status})
            )
        value["context"]["slots"] = True
        self.assertFalse(matches_current_read(value, {"phase": "read"}, entry))

    def test_model_qualified_reads_keep_identical_native_ids_separate(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            project = write_project(root)
            session = GraphSession(root)
            probe = BOProbe(project, session.manifest["build_id"], sink=session.bo_sink)
            try:
                for _ in range(2):
                    for model in ("file", "approval"):
                        event = probe.record(
                            model + ":advance",
                            "read",
                            lambda: {"outputs": {"state": "idle"}},
                            revision=0,
                        )
                        probe.snapshot("1", "idle", {}, 0, event, state_model_id=model)
                self.assertTrue(probe.flush(3))
                self.assertEqual(probe.bo_health()["errors"], 0)
                self.assertEqual(len(session.frames), 4)
                self.assertEqual(len(session.graph.bo_instances()), 2)
                self.assertEqual(
                    {frame[0]["machine"]["state_model_id"] for frame in session.frames.values()},
                    {"file", "approval"},
                )
            finally:
                probe.close()
                session.close()


if __name__ == "__main__":
    unittest.main()
