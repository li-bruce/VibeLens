"""State instances keep their identity through live views and saved replay frames."""

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


class SnapshotIdentityTests(unittest.TestCase):
    def test_shared_caller_does_not_collapse_native_state_instances(self):
        (ROOT / ".validation").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            project = project_fixture(root)
            session = GraphSession(root)
            probe = BOProbe(project, session.manifest["build_id"], sink=session.bo_sink)
            session.bo_bind_capture(
                scope_setter=probe.bo_set_scope,
                flush_capture=lambda: probe.flush(3),
                health=probe.bo_health,
            )
            try:
                recording_id = session.recordings.start()["id"]
                evidence = []
                supplied = {"attempt": "application", "phase": "pending", "journal": []}
                original = deepcopy(supplied)
                for native, state, revision, slots, configuration in (
                    ("file:1", "pending", 0, 1, supplied),
                    ("share:1", "pending", 0, 0, None),
                    ("file:1", "running", 1, 1, None),
                    ("share:1", "waiting", 1, 0, None),
                ):
                    event = probe.record(
                        "advance",
                        "change",
                        lambda: {"outputs": {"state": state}},
                        entity="application",
                        attempt="application",
                        scope="entity",
                        revision=revision,
                    )
                    probe.snapshot(
                        native,
                        state,
                        {"slots": slots},
                        revision,
                        event,
                        event="start" if revision else None,
                        guards={"available": bool(slots)} if revision else None,
                        configuration=configuration,
                    )
                    self.assertTrue(probe.flush(3))
                    evidence.append((event, native, state))
                self.assertEqual(supplied, original, "Projection metadata changed native input")
                view = session.view()
                configurations = view["machine"]["configurations"]
                self.assertEqual(len(configurations), 2)
                by_native = {cfg["native_instance_id"]: cfg for cfg in configurations}
                self.assertEqual(by_native["file:1"]["phase"], "running")
                self.assertEqual(by_native["share:1"]["phase"], "waiting")
                self.assertEqual({cfg["attempt"] for cfg in configurations}, {"application"})
                self.assertEqual(len({cfg["snapshot_instance"] for cfg in configurations}), 2)
                # Native graph storage is unchanged; metadata belongs to the observer view.
                stored = session.graph.bo_instances()[0]["observed"]
                if stored.get("configuration"):
                    self.assertNotIn("snapshot_instance", stored["configuration"])
                session.recordings.stop()
                saved = session.recordings.get(recording_id)
                self.assertEqual(saved["gaps"], [])
                self.assertEqual(saved["final"]["machine"]["configurations"], configurations)
                frames = {f["event_id"]: f for f in saved["runtime_frames"]["frames"]}
                events = {e["id"]: e for e in saved["events"]}
                for event_id, native, state in evidence:
                    cfg = frames[event_id]["machine"]["configurations"][0]
                    self.assertEqual(cfg["native_instance_id"], native)
                    self.assertEqual(
                        cfg["snapshot_instance"], events[event_id]["run_id"] + ":" + native
                    )
                    self.assertEqual(cfg["phase"], state)
                self.assertEqual(probe.bo_health()["errors"], 0)
            finally:
                probe.close()
                session.close()


if __name__ == "__main__":
    unittest.main()
