"""Time observer methods in a real unchanged trial; never create business events."""

import faulthandler
import importlib.util
import json
from pathlib import Path
import sys
import threading
import time

TRIAL = Path(sys.argv[1]).resolve().parent
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(TRIAL))
from observer_runtime.bo_observer.adapters.python.bo_probe import BOProbe
from observer_runtime.bo_observer.observation.session import GraphSession
from observer_runtime.bo_observer.observation.event_batch import BOSessionSink
from observer_runtime.bo_observer.observation.bo_retention import EventHistory
from observer_runtime.bo_observer.observation.recording_session import Recordings

metrics, failures, barriers = {}, [], []
lock = threading.Lock()
path = OUT / "native-thread-profile-07.json"
stacks = (OUT / "native-thread-stacks-07.log").open("w", encoding="utf-8")


def save():
    with lock:
        payload = {"methods": metrics, "batch_failures": failures, "barriers": barriers}
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def instrument(cls, name):
    original = getattr(cls, name)
    key = cls.__name__ + "." + name

    def timed(self, *args, **kwargs):
        started = time.perf_counter()
        try:
            return original(self, *args, **kwargs)
        except Exception as error:
            if cls is BOSessionSink:
                with lock:
                    failures.append({"type": type(error).__name__, "message": str(error)[:300]})
            raise
        finally:
            elapsed = time.perf_counter() - started
            with lock:
                entry = metrics.setdefault(key, {"calls": 0, "seconds": 0, "max_seconds": 0})
                entry["calls"] += 1
                entry["seconds"] += elapsed
                entry["max_seconds"] = max(entry["max_seconds"], elapsed)

    setattr(cls, name, timed)


for cls, name in (
    (GraphSession, "binding"), (GraphSession, "view"),
    (BOSessionSink, "bo_accept_many"), (EventHistory, "append_many"),
    (Recordings, "_capture"), (Recordings, "_write"),
):
    instrument(cls, name)

original_flush = BOProbe.flush


def observed_flush(self, *args, **kwargs):
    before = self.bo_health()
    started = time.perf_counter()
    faulthandler.dump_traceback_later(0.25, repeat=True, file=stacks)
    try:
        result = original_flush(self, *args, **kwargs)
    finally:
        faulthandler.cancel_dump_traceback_later()
    with lock:
        barriers.append({"before": before, "after": self.bo_health(),
                         "seconds": time.perf_counter()-started, "result": result})
    save()
    return result


BOProbe.flush = observed_flush
module_spec = importlib.util.spec_from_file_location("trial_dev", TRIAL / "dev.py")
module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(module)
sys.argv = [str(TRIAL / "dev.py"), "--app-port", "50957", "--graph-port", "50958"]
try:
    module.main()
finally:
    save()
    stacks.close()
