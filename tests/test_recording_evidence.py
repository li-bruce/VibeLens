"""Real collector recordings remain strict native verification inputs."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "skills/vibelens/scripts"), str(ROOT / "tools")]
from test_multilanguage import project_fixture
from bo_observer.adapters.python.bo_probe import BOProbe
from bo_observer.observation.session import GraphSession
from bo_observer.workflow.snapshot_evidence import assess_snapshot_admission
from bo_observer.protocol import validate_event


class RecordingEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / ".validation")
        self.root = Path(self.folder.name)
        self.project = project_fixture(self.root)
        self.session = GraphSession(self.root)
        self.build = self.session.manifest["build_id"]
        self.native = {"events": [], "snapshots": []}

        def collect(value, kind):
            self.native[kind].append(deepcopy(value))
            return self.session.bo_sink(value, kind)

        self.probe = BOProbe(self.project, self.build, sink=collect)
        self.session.bo_bind_capture(
            scope_setter=self.probe.bo_set_scope,
            flush_capture=lambda: self.probe.flush(3),
            health=self.probe.bo_health,
        )

    def tearDown(self):
        self.probe.close()
        self.session.close()
        self.folder.cleanup()

    def record(self):
        self.session.recordings.start()
        for _ in range(2):
            event = self.probe.record(
                "advance", "read", lambda: {"outputs": {"state": "pending"}}, revision=0
            )
            self.probe.snapshot("task:1", "pending", {"slots": 1}, 0, event)
        self.assertTrue(self.probe.flush(3))
        stopped = self.session.recordings.stop()
        return self.session.recordings.get(stopped["id"])

    def export(self, recording):
        from bo_observer.observation.recording_evidence import export_evidence

        return export_evidence(recording, self.project, self.build)

    def audit(self, evidence):
        return assess_snapshot_admission(
            self.project,
            self.build,
            {"runs": [{"case": "browser", "mode": "on", **evidence}]},
            required=True,
        )

    def test_recorder_retains_exact_native_snapshot_envelopes(self):
        recording = self.record()
        frames = recording["runtime_frames"]["frames"]
        self.assertEqual(
            [f.get("native_snapshot") for f in frames], self.native["snapshots"]
        )
        self.assertEqual([f.get("snapshot_seq") for f in frames], [1, 2])

    def test_full_export_restores_native_events_and_passes_snapshot_gate(self):
        recording = self.record()
        original = deepcopy(recording)
        evidence = self.export(recording)
        self.assertEqual(evidence["events"], self.native["events"])
        self.assertEqual(evidence["snapshots"], self.native["snapshots"])
        self.assertTrue(self.audit(evidence)["valid"])
        self.assertEqual(recording, original)
        # No policy or independent business result is invented by the exporter.
        self.assertNotIn("policy_evaluations", evidence)
        self.assertNotIn("observations", evidence)

    def test_wire_protocol_stays_strict_and_unknown_record_metadata_fails(self):
        recording = self.record()
        with self.assertRaises(ValueError):
            validate_event(recording["events"][0], self.project, self.build)
        for key, value in (
            ("unexpected", 1),
            ("stream_id", "other"),
            ("source_seq", 0),
            ("source_seq", True),
        ):
            with self.subTest(key=key, value=value):
                changed = deepcopy(recording)
                changed["events"][0][key] = value
                with self.assertRaises(ValueError):
                    self.export(changed)

    def test_receipt_sequence_is_distinct_from_native_producer_sequence(self):
        recording = self.record()
        # Moving only collector receipt positions must not change native identity.
        for event in recording["events"]:
            event["seq"] += 100
        self.assertEqual(self.export(recording)["events"], self.native["events"])

    def test_legacy_display_frames_do_not_supply_missing_native_snapshots(self):
        recording = self.record()
        for frame in recording["runtime_frames"]["frames"]:
            frame.pop("native_snapshot")
            frame.pop("snapshot_seq")
        evidence = self.export(recording)
        self.assertEqual(evidence["snapshots"], [])
        result = self.audit(evidence)
        self.assertFalse(result["valid"])
        self.assertTrue(all(e.get("missing_state_snapshot") for e in result["errors"]))

    def test_native_snapshot_identity_and_receipt_collisions_are_rejected(self):
        recording = self.record()
        for key, value in (
            ("evidence_id", "other"),
            ("producer_id", "other"),
            ("revision", 99),
            ("build_id", "old"),
        ):
            with self.subTest(key=key):
                changed = deepcopy(recording)
                changed["runtime_frames"]["frames"][0]["native_snapshot"][key] = value
                with self.assertRaises(ValueError):
                    self.export(changed)
        recording["runtime_frames"]["frames"][1]["snapshot_seq"] = 1
        with self.assertRaisesRegex(ValueError, "duplicate snapshot"):
            self.export(recording)

    def test_receipt_order_is_not_repaired_using_state_or_event_order(self):
        recording = self.record()
        frames = recording["runtime_frames"]["frames"]
        frames[0]["snapshot_seq"], frames[1]["snapshot_seq"] = 2, 1
        evidence = self.export(recording)
        self.assertEqual(
            evidence["snapshots"], list(reversed(self.native["snapshots"]))
        )
        self.assertIn("out of producer order", str(self.audit(evidence)["errors"]))

    def test_unsettled_stale_and_incomplete_recordings_are_rejected(self):
        recording = self.record()
        for key, value in (
            ("status", "recording"),
            ("gaps", ["missing"]),
            ("build_id", "other"),
            ("producer_settlement", {"flushed": False}),
        ):
            changed = {**recording, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.export(changed)

    def test_cli_exports_without_overwriting_recording_or_claiming_acceptance(self):
        recording = self.record()
        source, target = self.root / "recording.json", self.root / "evidence.json"
        source.write_text(json.dumps(recording), encoding="utf-8")
        original = source.read_bytes()
        command = [
            sys.executable,
            "-B",
            str(ROOT / "skills/vibelens/scripts/bo_trace.py"),
            "evidence",
            "--root",
            str(self.root),
            "--recording",
            str(source),
            "--out",
            str(target),
        ]
        result = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["acceptance"], "not_run")
        self.assertTrue(
            self.audit(json.loads(target.read_text(encoding="utf-8")))["valid"]
        )
        command[-1] = str(source)
        self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.assertEqual(source.read_bytes(), original)

    def test_two_models_keep_distinct_original_snapshots_for_the_same_instance(self):
        from test_model_networks import write_project
        from bo_observer.observation.recording_evidence import export_evidence

        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            project = write_project(root)
            session = GraphSession(root)
            probe = BOProbe(project, session.manifest["build_id"], sink=session.bo_sink)
            session.bo_bind_capture(
                scope_setter=probe.bo_set_scope,
                flush_capture=lambda: probe.flush(3),
                health=probe.bo_health,
            )
            try:
                session.recordings.start()
                for model in ("file", "approval"):
                    event = probe.record(
                        model + ":advance",
                        "read",
                        lambda: {"outputs": {"state": "idle"}},
                        revision=0,
                    )
                    probe.snapshot(
                        "same-instance", "idle", {}, 0, event, state_model_id=model
                    )
                self.assertTrue(probe.flush(3))
                stopped = session.recordings.stop()
                recording = session.recordings.get(stopped["id"])
                evidence = export_evidence(
                    recording, project, session.manifest["build_id"]
                )
                self.assertEqual(
                    {v["state_model_id"] for v in evidence["snapshots"]},
                    {"file", "approval"},
                )
                self.assertEqual(
                    {v["instance_id"] for v in evidence["snapshots"]}, {"same-instance"}
                )
                report = assess_snapshot_admission(
                    project,
                    session.manifest["build_id"],
                    {"runs": [{"case": "two-models", "mode": "on", **evidence}]},
                    required=True,
                )
                self.assertTrue(report["valid"], report)
            finally:
                probe.close()
                session.close()


if __name__ == "__main__":
    unittest.main()
