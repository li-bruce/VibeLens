"""Time observer methods in a real unchanged trial; never create business events."""

from collections import Counter
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

metrics, failures, barriers, samples, probes = {}, [], [], Counter(), []
lock = threading.Lock()
path = OUT / "native-thread-profile-09.json"
stopping = threading.Event()


def save():
    with lock:
        payload = {"methods": metrics, "batch_failures": failures, "barriers": barriers,
                   "samples": dict(samples.most_common(70)),
                   "probe_health": [probe.bo_health() for probe in probes]}
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
    (Recordings, "get"),
):
    instrument(cls, name)

original_flush = BOProbe.flush
original_init = BOProbe.__init__


def registered(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    probes.append(self)


BOProbe.__init__ = registered


def observed_flush(self, *args, **kwargs):
    before = self.bo_health()
    started = time.perf_counter()
    result = original_flush(self, *args, **kwargs)
    with lock:
        barriers.append({"before": before, "after": self.bo_health(),
                         "seconds": time.perf_counter()-started, "result": result})
    save()
    return result


BOProbe.flush = observed_flush


def sample_threads():
    """Read frames while holding the Python GIL; never use native stack dumping."""
    count = 0
    while not stopping.wait(0.05):
        frames = sys._current_frames()
        names = {thread.ident: thread.name for thread in threading.enumerate()}
        for identity, frame in frames.items():
            parts = []
            while frame is not None and len(parts) < 7:
                if Path(frame.f_code.co_filename).name != Path(__file__).name:
                    parts.append(Path(frame.f_code.co_filename).name + ':' + frame.f_code.co_name)
                frame = frame.f_back
            if parts:
                with lock:
                    samples[names.get(identity, str(identity)) + ' | ' + ' > '.join(parts)] += 1
        count += 1
        if count % 20 == 0:
            save()


sampler = threading.Thread(target=sample_threads,daemon=True,name='review-observer-sampler')
sampler.start()
module_spec = importlib.util.spec_from_file_location("trial_dev", TRIAL / "dev.py")
module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(module)
sys.argv = [str(TRIAL / "dev.py"), "--app-port", "50957", "--graph-port", "50958"]
try:
    module.main()
finally:
    stopping.set()
    sampler.join(3)
    save()
