"""Bounded file replacement during stopped-record persistence on Windows."""

from copy import deepcopy
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.observation.recording_session import Recordings


class RecordingBoundaryTests(unittest.TestCase):
    def test_event_during_initial_snapshot_keeps_a_valid_start_boundary(self):
        scratch = ROOT / ".validation/recording-boundary"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            view = {
                "model": {"nodes": []},
                "manifest": {"build_id": "build"},
                "machine": {},
                "authority": {"parameters": {}},
                "health": {"run_id": "run", "attempted": 0},
                "events": [],
                "binding_status": {"status": "current"},
                "historical": False,
            }
            calls = 0

            def provider():
                nonlocal calls
                calls += 1
                snapshot = deepcopy(view)
                if calls == 2:
                    event = {
                        "id": "event-1",
                        "seq": 1,
                        "run_id": "run",
                        "node": "check",
                        "inputs": {},
                        "outputs": {},
                        "observed_at": datetime.now(timezone.utc).isoformat(),
                    }
                    view["events"].append(event)
                    view["health"]["attempted"] = 1
                    recorder.bo_event(event)
                    time.sleep(0.01)
                return snapshot

            recorder = Recordings(directory, provider, {}, interval=60)
            try:
                ident = recorder.start()["id"]
                recorder.stop()
                saved = recorder.get(ident)
                self.assertEqual(len(saved["events"]), 1)
                self.assertLessEqual(saved["started_at"], saved["events"][0]["observed_at"])
            finally:
                recorder.close()


@unittest.skipUnless(sys.platform == "win32", "Windows file-sharing semantics")
class AtomicRecordingTests(unittest.TestCase):
    def test_brief_external_reader_does_not_turn_stop_into_interruption(self):
        scratch = ROOT / ".validation/recording-atomicity"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            view = {
                "model": {"nodes": []},
                "manifest": {"build_id": "build"},
                "machine": {},
                "authority": {"parameters": {}},
                "health": {"run_id": "run", "attempted": 0},
                "events": [],
                "binding_status": {"status": "current"},
                "historical": False,
            }
            recording = Recordings(directory, lambda: deepcopy(view), {}, interval=60)
            ident = recording.start()["id"]
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.CreateFileW.argtypes = [
                wintypes.LPCWSTR,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.LPVOID,
                wintypes.DWORD,
                wintypes.DWORD,
                wintypes.HANDLE,
            ]
            kernel.CreateFileW.restype = wintypes.HANDLE
            kernel.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel.CloseHandle.restype = wintypes.BOOL
            # This real reader allows read/write but briefly excludes replacement.
            handle = kernel.CreateFileW(
                str(recording._path(ident)), 0x80000000, 3, None, 3, 0, None
            )
            self.assertNotEqual(handle, ctypes.c_void_p(-1).value)

            def release():
                time.sleep(0.015)
                kernel.CloseHandle(handle)

            thread = threading.Thread(target=release)
            thread.start()
            try:
                stopped = recording.stop()
                self.assertEqual(stopped["status"], "stopped", recording.last_error)
                on_disk = json.loads(recording._path(ident).read_text(encoding="utf-8"))
                self.assertEqual(on_disk["status"], "stopped")
            finally:
                thread.join()
                recording.close()


if __name__ == "__main__":
    unittest.main()
