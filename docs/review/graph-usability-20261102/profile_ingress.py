"""Profile replay admission in an isolated frozen-source copy, not a new business run."""
import cProfile
import io
import json
import os
from pathlib import Path
import pstats
import sys
import tempfile
import time
import zipfile

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "skills/vibelens/scripts"))
os.environ["BO_ADAPTER_HOME"] = str(REPO / "skills/vibelens/scripts/bo_observer/adapters/javascript")
from bo_observer.observation.session import GraphSession
from bo_observer.protocol import validate_event


def main():
    batch_size = int(os.environ.get("BO_PROFILE_BATCH", "16"))
    round_id = os.environ.get("BO_PROFILE_ROUND", "01")
    record = json.loads((OUT / "native-busy-browser-02/recording.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(dir=REPO / ".validation") as folder:
        root = Path(folder)
        with zipfile.ZipFile(REPO / "docs/review/otel-provenance-20261101/dialogue-04-v2-final-source.zip") as archive:
            for name in archive.namelist():
                if not (root / name).resolve().is_relative_to(root.resolve()):
                    raise ValueError("archive path escaped the isolated profile root")
            archive.extractall(root)
        # The original source archive excludes running processes/data. Constructors
        # below use only that copy; measured events are retained old observations.
        session = GraphSession(root)
        values = []
        for original in record["events"][:2048]:
            value = {k: v for k, v in original.items() if k not in {"source_seq", "stream_id", "context_only", "context_boundary"}}
            value["seq"] = original["source_seq"]
            values.append(value)
        profile = cProfile.Profile()
        started = time.perf_counter()
        try:
            profile.enable()
            for value in values[:256]:
                validate_event(value, session.project, session.manifest["build_id"])
            for _ in range(16):
                session.binding()
            for index in range(0, len(values), batch_size):
                session.bo_sink.bo_accept_many(values[index:index+batch_size])
            profile.disable()
        finally:
            session.close()
        stream = io.StringIO()
        pstats.Stats(profile, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(45)
        (OUT / ("ingress-profile-"+round_id+".txt")).write_text(stream.getvalue(), encoding="utf-8")
        print(json.dumps({"profile_events":len(values),"seconds":time.perf_counter()-started,
                          "scope":"isolated replay admission, not a fresh business execution"}))


if __name__ == "__main__":
    main()
