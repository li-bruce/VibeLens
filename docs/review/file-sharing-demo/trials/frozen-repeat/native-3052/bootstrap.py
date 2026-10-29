"""Preserve prior receipts without recursive ZIP growth and prepare native control acceptance."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PREVIOUS = ROOT / "review/framework-upgrade-3458366"
if (OUT / "before.json").exists():
    raise RuntimeError("Do not replace this round's preservation snapshot.")
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
read = lambda path: json.loads(path.read_text(encoding="utf-8-sig"))
history = {path.relative_to(ROOT).as_posix(): {"sha256": sha(path), "bytes": path.stat().st_size}
           for parent in (ROOT / "review", ROOT / "dist") for path in parent.rglob("*.zip")
           if not path.is_relative_to(OUT)}
source_package = PREVIOUS / "upgraded-source.zip"
with zipfile.ZipFile(source_package) as archive:
    source_names = archive.namelist()
    for name in source_names:
        assert archive.read(name) == (ROOT / name).read_bytes(), name
source_files = {name: sha(ROOT / name) for name in source_names}
version = read(ROOT / "bo_stategraph/runtime-version.json")
manifest = read(ROOT / "manifest.json")
protected = {name: sha(ROOT / name) for name in manifest["files"]
             if name not in {"ownership.json", "bo_stategraph/runtime-version.json"}}
test_files = {path.relative_to(ROOT).as_posix(): sha(path)
              for parent in (ROOT / "tests", ROOT / "review") for path in parent.rglob("*.py")
              if not path.is_relative_to(OUT) and "scratch" not in path.parts}
evidence_names = set()
for folder in (PREVIOUS, ROOT / ".stategraph/framework-upgrade-3458366"):
    evidence_names.update(path.relative_to(ROOT).as_posix() for path in folder.rglob("*")
                          if path.is_file() and path.suffix.lower() != ".zip" and "__pycache__" not in path.parts)
for path in (ROOT / "review").glob("gate-*.json"):
    evidence_names.add(path.relative_to(ROOT).as_posix())
evidence_names.update(("review/evidence-checks.json", "review/browser-latest.json", "review/implementation-version.json"))
evidence = {name: sha(ROOT / name) for name in sorted(evidence_names)}
receipt_zip = OUT / "prior-3458366-receipts.zip"
with zipfile.ZipFile(receipt_zip, "x", zipfile.ZIP_DEFLATED) as archive:
    for name in sorted(evidence):
        assert not name.lower().endswith(".zip")
        archive.write(ROOT / name, name)
model = read(ROOT / "bo_stategraph/project.json")["model"]
declarations = {}
for part in ("machine", "policy"):
    data = json.dumps(model[part], ensure_ascii=False, sort_keys=True, indent=2).encode()
    (OUT / ("before-" + part + ".json")).write_bytes(data)
    declarations[part] = hashlib.sha256(data).hexdigest()
recordings = {path.relative_to(ROOT).as_posix(): sha(path)
              for path in (ROOT / "bo_stategraph/data/recordings").glob("*.json")}
before = {"created_at": datetime.now(timezone.utc).isoformat(),
    "accepted_candidate": read(PREVIOUS / "summary.json")["candidate_id"],
    "build_id": manifest["build_id"], "source_files": source_files,
    "protected_files": protected, "protected_test_files": test_files,
    "installed_files": version["files"], "declaration_hashes": declarations,
    "history_archives": history, "prior_source_package": source_package.relative_to(ROOT).as_posix(),
    "evidence_files": evidence, "old_raw_recordings": recordings,
    "new_archive": {"path": receipt_zip.name, "sha256": sha(receipt_zip), "files": len(evidence), "contains_zip": False}}
(OUT / "before.json").write_text(json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8")
(OUT / "previous-evidence-index.json").write_text(json.dumps({
    "previous_review": "../framework-upgrade-3458366/index.md", "archives_referenced_only": history,
    "non_zip_receipts_preserved": before["new_archive"]}, ensure_ascii=False, indent=2), encoding="utf-8")
text = (PREVIOUS / "prepare.py").read_text(encoding="utf-8")
for old, new in [
    ('["static/graph/semantic-view.js"]', '["static/graph/conversation-controls.js", "static/graph/viewer.js"]'),
    ('"vibelens-focus-fix"', '"vibelens-control-fix"'),
    ('3458366f72563b35749a9f7bcf799c2b7e22da00', '3052e03c32e9bbfcdc19961cad36085415795433'),
    ('b78f03a89e1726f951ea76d4e0781efd2e869fe6', '3458366f72563b35749a9f7bcf799c2b7e22da00'),
    ('framework-upgrade-3458366', 'framework-upgrade-3052e03'),
    ('b78-evidence.zip:review/implementation-version.json', 'previous-evidence-index.json')]:
    assert old in text, old
    text = text.replace(old, new)
(OUT / "prepare.py").write_text(text, encoding="utf-8")
(OUT / "browser-native").mkdir(exist_ok=True)
copied = {}
for name in ("keyboard_source_acceptance.py", "preferences-original.json", "capture_short.py", "viewer_acceptance.py", "keyboard_details.py"):
    shutil.copyfile(PREVIOUS / name, OUT / name)
    assert sha(PREVIOUS / name) == sha(OUT / name)
    copied[name] = {"original_sha256": sha(PREVIOUS / name), "copied_sha256": sha(OUT / name), "byte_identical": True}
(OUT / "unchanged-test-copies.json").write_text(json.dumps(copied, indent=2), encoding="utf-8")
session = read(PREVIOUS / "resource-start.json")["session_file"]
markers, counts = [], []
for line in Path(session).open(encoding="utf-8"):
    try: item = json.loads(line)
    except ValueError: continue
    payload = item.get("payload", {})
    if "需要再做一轮框架原生集成验收" in str(payload): markers.append(item["timestamp"])
    if payload.get("type") == "token_count" and payload.get("info"):
        counts.append({"timestamp": item["timestamp"], "info": payload["info"]})
start = min(markers)
prior = [item for item in counts if item["timestamp"] < start]
(OUT / "resource-start.json").write_text(json.dumps({"session_file": session,
    "authorization_timestamp": start, "baseline": prior[-1] if prior else None}, indent=2), encoding="utf-8")
print(json.dumps({"prior_source_files_verified": len(source_files), "protected_test_files": len(test_files),
                  "new_non_zip_receipts": len(evidence), "history_archives_referenced": len(history)}))
