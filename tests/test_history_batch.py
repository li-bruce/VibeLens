"""Grouped publication retains exact log rotation, delivery and isolation rules."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.observation.bo_retention import EventHistory


class HistoryBatchTests(unittest.TestCase):
    def test_grouped_log_matches_single_event_rotation_byte_for_byte(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            root = Path(folder)
            single = EventHistory(path=root / "single.jsonl", limits={"log_bytes": 256})
            grouped = EventHistory(path=root / "grouped.jsonl", limits={"log_bytes": 256})
            events = [{"seq": index, "text": "value " * 8} for index in range(18)]
            for event in events:
                single.append(event)
            grouped.append_many(events)
            for suffix in ("", ".1", ".2"):
                a, b = root / ("single.jsonl" + suffix), root / ("grouped.jsonl" + suffix)
                self.assertEqual(a.read_bytes(), b.read_bytes())
                self.assertLessEqual(b.stat().st_size, 256)
            self.assertEqual(single.snapshot(), grouped.snapshot())
            self.assertEqual(grouped.health()["log_errors"], 0)

    def test_group_uses_one_file_handle_and_delivers_each_original_in_order(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            path = Path(folder) / "events.jsonl"
            history = EventHistory(path=path, limits={"memory_events": 3})
            values = [{"seq": index, "inputs": {"value": index}} for index in range(64)]
            received, opened = [], []
            history.subscribe(lambda event: received.append(event["seq"]))
            original = Path.open

            def observe_open(file, *args, **kwargs):
                if file == path:
                    opened.append(args[0] if args else kwargs.get("mode"))
                return original(file, *args, **kwargs)

            with patch.object(Path, "open", observe_open):
                history.append_many(values)
            self.assertEqual(opened, ["ab"])
            self.assertEqual(received, list(range(64)))
            self.assertEqual(history.health()["evicted_events"], 61)
            values[-1]["inputs"]["value"] = "edited caller payload"
            self.assertEqual(history.snapshot()[-1]["inputs"]["value"], 63)
            public = history.snapshot()
            public[-1]["inputs"]["value"] = "edited public view"
            self.assertEqual(history.snapshot()[-1]["inputs"]["value"], 63)

    def test_errors_and_oversize_events_are_counted_individually(self):
        with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
            path = Path(folder) / "events.jsonl"
            history = EventHistory(path=path, limits={"log_bytes": 100})
            received = []

            def fail(event):
                raise ValueError("listener unavailable")

            history.subscribe(fail)
            history.subscribe(lambda event: received.append(event["seq"]))
            history.append_many([{"seq": 1}, {"seq": 2, "text": "x" * 101}, {"seq": 3}])
            self.assertEqual(received, [1, 2, 3])
            self.assertEqual(history.health()["listener_errors"], 3)
            self.assertEqual(history.health()["log_errors"], 1)
            self.assertEqual(path.read_text(encoding="utf-8"), '{"seq": 1}\n{"seq": 3}\n')
            self.assertEqual(len(history.snapshot()), 3)


if __name__ == "__main__":
    unittest.main()
