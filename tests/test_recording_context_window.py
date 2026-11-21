"""Bounded pre-recording values retain witnessed call ancestry and closure."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.observation import capture_context
from bo_observer.observation.recording_session import checkpoint

MODEL = {"nodes": [{"id": name} for name in ("parent", "child", "other")]}


def event(seq, node="child", phase="read", call=None, parent=None, **changes):
    """Provide distinct witnessed identities, including reusable scoped call IDs."""
    return {
        "id": f"event-{seq}",
        "seq": seq,
        "project_id": "project",
        "model_revision": "r1",
        "build_id": "build",
        "run_id": "run",
        "producer_id": "producer",
        "stream_id": "stream",
        "entity": "object",
        "attempt": "attempt",
        "node": node,
        "phase": phase,
        "call_id": call,
        "parent_event_id": parent,
        "parent_call_id": None,
        "inputs": {"selected": seq},
        "outputs": {"value": seq},
        "basis": {"private": seq},
        "depends": [],
        "lifecycle": "span" if call else "point",
        **changes,
    }


def view(events, opened=()):
    return {
        "authority": {},
        "model": MODEL,
        "machine": {},
        "health": {},
        "binding_status": {"status": "current"},
        "manifest": {},
        "events": events,
        "open_invocations": list(opened),
    }


class RecordingContextWindowTests(unittest.TestCase):
    def test_checkpoint_keeps_available_parent_before_the_2000_value_tail(self):
        events = [event(1, "parent", "enter", "outer")]
        events += [event(i, parent="event-1") for i in range(2, 2006)]
        events += [event(2006, "parent", "return", "outer")]
        original = deepcopy(events)
        kept = checkpoint(view(events), context=True)["events"]
        parent = next((row for row in kept if row["id"] == "event-1"), None)
        self.assertIsNotNone(
            parent, "Available parent was cut off by the recent-value tail"
        )
        self.assertTrue(parent["context_only"])
        self.assertEqual(parent["inputs"], {})
        self.assertEqual(sum(not row.get("context_only") for row in kept), 2000)
        self.assertEqual(kept[-1]["phase"], "return")
        self.assertEqual(events, original)

    def window(self, events, opened=(), limit=2):
        return capture_context.recording_context(
            events, list(opened), MODEL, limit=limit
        )

    def test_closed_ancestor_has_both_boundaries_without_old_values(self):
        rows = [
            event(1, "parent", "enter", "p"),
            event(2, parent="event-1"),
            event(3, "parent", "return", "p"),
            event(4, parent="event-1"),
            event(5),
        ]
        kept, candidates = self.window(rows)
        self.assertEqual([row["seq"] for row in kept], [1, 3, 4, 5])
        self.assertEqual([row["seq"] for row in candidates], [1, 3, 4, 5])
        self.assertTrue(all(row["context_only"] for row in kept[:2]))
        self.assertTrue(
            all(
                row["inputs"] == row["outputs"] == row["basis"] == {}
                for row in kept[:2]
            )
        )

    def test_future_child_can_resolve_closed_parent_outside_initial_tail(self):
        rows = [
            event(1, "parent", "enter", "p"),
            event(2, "parent", "return", "p"),
            event(3),
            event(4),
        ]
        kept, candidates = self.window(rows)
        self.assertEqual([row["seq"] for row in kept], [3, 4])
        interval = [event(5, parent="event-1")]
        actual, context = capture_context.retain_recording(
            interval, candidates, {row["id"] for row in kept}, MODEL
        )
        self.assertEqual(actual, interval)
        self.assertEqual([row["seq"] for row in context], [1, 2, 3, 4])

    def test_entry_after_history_expiry_uses_only_open_header(self):
        opened = capture_context.minimal_boundary(event(1, "parent", "enter", "p"), {})
        kept, _ = self.window([event(8, parent="event-1"), event(9)], [opened])
        self.assertEqual([row["seq"] for row in kept], [1, 8, 9])
        self.assertTrue(kept[0]["context_only"])
        self.assertFalse(any(row["phase"] == "return" for row in kept))

    def test_reused_call_id_does_not_copy_unrelated_invocation(self):
        rows = [
            event(1, "parent", "enter", "same"),
            event(2, "parent", "return", "same"),
            event(3, "parent", "enter", "same"),
            event(4, "parent", "return", "same"),
            event(5, parent="event-3"),
            event(6),
        ]
        kept, _ = self.window(rows)
        self.assertEqual([row["seq"] for row in kept], [3, 4, 5, 6])

    def test_call_only_reference_is_scoped_to_its_producer(self):
        rows = [
            event(1, "parent", "enter", "same", producer_id="other"),
            event(2, "parent", "enter", "same"),
            event(3, parent_call_id="same"),
            event(4),
        ]
        kept, _ = self.window(rows)
        self.assertEqual([row["seq"] for row in kept], [2, 3, 4])

    def test_expired_parent_stays_missing_and_reference_is_unchanged(self):
        rows = [event(8, parent="expired"), event(9)]
        kept, _ = self.window(rows)
        self.assertEqual(kept, rows)
        self.assertEqual(kept[0]["parent_event_id"], "expired")

    def test_explicit_missing_parent_does_not_fall_back_to_reused_call_id(self):
        rows = [
            event(1, "parent", "enter", "same"),
            event(2, parent="expired", parent_call_id="same"),
            event(3),
        ]
        kept, _ = self.window(rows)
        self.assertEqual([row["seq"] for row in kept], [2, 3])

    def test_cyclic_references_terminate_without_creating_observations(self):
        rows = [
            event(1, "parent", "enter", "p", parent="event-2"),
            event(2, "child", "enter", "c", parent="event-1"),
            event(3, parent="event-2"),
        ]
        kept, _ = self.window(rows, limit=1)
        self.assertEqual([row["seq"] for row in kept], [1, 2, 3])

    def test_focused_scope_retains_shared_boundaries_without_other_values(self):
        rows = [
            event(1, "parent", "enter", "p"),
            event(2, "parent", "return", "p"),
            event(3, parent="event-1"),
            event(4, "other"),
        ]
        _, candidates = self.window(rows)
        candidates = capture_context.context_candidates(candidates, {"child"}, MODEL)
        interval, kept = capture_context.retain_scope([], candidates, {"child"}, MODEL)
        self.assertEqual(interval, [])
        self.assertEqual([row["seq"] for row in kept], [1, 2, 3])
        self.assertTrue(all(not row["inputs"] for row in kept[:2]))


if __name__ == "__main__":
    unittest.main()
