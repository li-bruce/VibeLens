"""Register byte-verified historical exports with the canonical frozen-source interface."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    evidence = read(OUT / "integrity-before.json")
    archive = "review/retest-20261031-03/core-extracted"
    files = {name[len(archive) + 1:]: value for name, value in evidence.items()
             if name.startswith(archive + "/")}
    assert files
    for name, value in files.items():
        assert hashlib.sha256((ROOT / archive / name).read_bytes()).hexdigest() == value
    write(OUT / "frozen-core-sources.json", {"schema": "trial-frozen-sources/v1", "files": files,
        "basis": "Pre-upgrade protected snapshot; historical standalone export, never imported by the active application."})
    config = read(ROOT / "sync.json")
    config["source_scope"].setdefault("frozen_sources", {})[archive] = "review/retest-20261101-01/frozen-core-sources.json"
    write(ROOT / "sync.json", config)
    previous = ROOT / "resume-first-integration-20261031/review.json"
    assert not (OUT / "previous-candidate-review.json").exists()
    (OUT / "previous-candidate-review.json").write_bytes(previous.read_bytes())
    print(json.dumps({"registered_historical_files": len(files), "active_source_roots_unchanged": True}))
