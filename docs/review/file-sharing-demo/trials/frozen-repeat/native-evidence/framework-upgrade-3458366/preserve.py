"""Preserve the accepted V2 source, evidence and exact comparison surface once."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
destination = OUT / "before.json"
if destination.exists():
    raise RuntimeError("The upgrade preservation snapshot already exists; never replace it.")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))

version = read("bo_stategraph/runtime-version.json")
manifest = read("manifest.json")
source_names = sorted(set(manifest["files"]) | set(version["files"]) |
                      {"bo_stategraph/project.json", "manifest.json", "review/evidence_checks.py", "review/framework-upgrade-b78f03a/keyboard_source_acceptance.py"})
source_zip = OUT / "b78-source.zip"
with zipfile.ZipFile(source_zip, "x", zipfile.ZIP_DEFLATED) as archive:
    for name in source_names:
        archive.write(ROOT / name, name)

evidence_names = set()
for folder in ("review", ".stategraph/revocation-v2", ".stategraph/initial-v1",
               ".stategraph/initial-v1-browser-evidence", ".stategraph/framework-upgrade-b78f03a", "dist", "bo_stategraph/data/recordings"):
    for path in (ROOT / folder).rglob("*"):
        if path.is_file() and not path.is_relative_to(OUT) and "scratch" not in path.parts:
            evidence_names.add(path.relative_to(ROOT).as_posix())
evidence_zip = OUT / "b78-evidence.zip"
with zipfile.ZipFile(evidence_zip, "x", zipfile.ZIP_DEFLATED) as archive:
    for name in sorted(evidence_names):
        archive.write(ROOT / name, name)

protected_names = sorted(set(manifest["files"]) -
                         {"ownership.json", "bo_stategraph/runtime-version.json"})
model = read("bo_stategraph/project.json")["model"]
snapshots = {}
for part in ("machine", "policy"):
    data = json.dumps(model[part], ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    (OUT / ("before-" + part + ".json")).write_bytes(data)
    snapshots[part] = hashlib.sha256(data).hexdigest()
views = {path.relative_to(ROOT).as_posix(): digest(path)
         for path in (ROOT / "bo_stategraph/config/views").rglob("*.json")}
preserved = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "accepted_candidate": read("review/framework-upgrade-b78f03a/summary.json")["candidate_id"],
    "build_id": manifest["build_id"], "installed_files": version["files"],
    "protected_files": {name: digest(ROOT / name) for name in protected_names},
    "source_files": {name: digest(ROOT / name) for name in source_names},
    "evidence_files": {name: digest(ROOT / name) for name in sorted(evidence_names)},
    "declaration_hashes": snapshots, "views": views,
    "archives": {path.name: {"sha256": digest(path), "bytes": path.stat().st_size}
                 for path in (source_zip, evidence_zip)},
    "recording": "538215624de546279299d1c0a1cdf5b3",
    "database_sha256_before": digest(ROOT / "data/files.sqlite3"),
}
destination.write_text(json.dumps(preserved, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"source_files": len(source_names), "evidence_files": len(evidence_names),
                  "protected_files": len(protected_names), "build_id": manifest["build_id"]}))
