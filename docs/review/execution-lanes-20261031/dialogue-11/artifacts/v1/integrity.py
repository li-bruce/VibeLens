"""Snapshot historical evidence and independently compare protected bytes."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
ROUND = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot():
    paths = [p for p in (ROOT / "review").rglob("*") if p.is_file() and ROUND not in p.parents]
    paths += [ROOT / p for p in ("acceptance.json", "intent.json", "mapping.json", "whitebox.json",
        "discovery.json", "resume-first-integration-20261031/baseline.json")]
    paths += [p for p in (ROOT / "app").rglob("*.py")]
    paths += list((ROOT / "bo_stategraph/data/recordings").glob("*.json"))
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}

if __name__ == "__main__":
    mode = sys.argv[1]
    path = ROUND / "integrity-before.json"
    if mode == "before":
        assert not path.exists()
        payload = snapshot()
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps({"snapshotted": len(payload), "baseline_sha256": payload["resume-first-integration-20261031/baseline.json"]}))
    else:
        before = json.loads(path.read_text(encoding="utf-8"))
        changed = [name for name, value in before.items() if not (ROOT / name).is_file() or digest(ROOT / name) != value]
        payload = {"protected_files": len(before), "changed": changed, "valid": not changed}
        (ROUND / "integrity-after.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload))
        assert not changed
