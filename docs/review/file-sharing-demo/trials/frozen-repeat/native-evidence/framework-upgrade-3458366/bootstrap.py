"""Prepare a new independent candidate round without editing the b78 evidence/tests."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PREVIOUS = ROOT / "review/framework-upgrade-b78f03a"
if (OUT / "before.json").exists():
    raise RuntimeError("Continue the existing immutable round; do not replace preservation.")

def adapt(name, replacements):
    text = (PREVIOUS / name).read_text(encoding="utf-8")
    for old, new in replacements:
        assert old in text, (name, old)
        text = text.replace(old, new)
    (OUT / name).write_text(text, encoding="utf-8")

adapt("preserve.py", [
    ('"review/evidence_checks.py"}', '"review/evidence_checks.py", "review/framework-upgrade-b78f03a/keyboard_source_acceptance.py"}'),
    ('"v2-source.zip"', '"b78-source.zip"'), ('"v2-evidence.zip"', '"b78-evidence.zip"'),
    ('".stategraph/initial-v1-browser-evidence", "dist"', '".stategraph/initial-v1-browser-evidence", ".stategraph/framework-upgrade-b78f03a", "dist"'),
    ('read("review/revocation-summary.json")', 'read("review/framework-upgrade-b78f03a/summary.json")'),
    ('"77ae11709c33488ca6b294097e7d86da"', '"538215624de546279299d1c0a1cdf5b3"'),
])
adapt("prepare.py", [
    ('["static/graph/analysis.js", "static/graph/recording.js"]', '["static/graph/semantic-view.js"]'),
    ('"vibelens-policy-graph"', '"vibelens-focus-fix"'),
    ('b78f03a89e1726f951ea76d4e0781efd2e869fe6', '3458366f72563b35749a9f7bcf799c2b7e22da00'),
    ('e69ce0921ac06fb455ec0aedc403e24d74babebc', 'b78f03a89e1726f951ea76d4e0781efd2e869fe6'),
    ('framework-upgrade-b78f03a', 'framework-upgrade-3458366'),
    ('v2-evidence.zip', 'b78-evidence.zip'),
])
(OUT / "browser-native").mkdir(exist_ok=True)
copies = {}
for name in ("keyboard_source_acceptance.py", "preferences-original.json", "capture_short.py", "viewer_acceptance.py"):
    shutil.copyfile(PREVIOUS / name, OUT / name)
    old = hashlib.sha256((PREVIOUS / name).read_bytes()).hexdigest()
    current = hashlib.sha256((OUT / name).read_bytes()).hexdigest()
    assert old == current
    copies[name] = {"original_sha256": old, "copied_sha256": current, "byte_identical": True}
(OUT / "unchanged-test-copies.json").write_text(json.dumps(copies, indent=2), encoding="utf-8")
session = json.loads((PREVIOUS / "resource-start.json").read_text())["session_file"]
markers, counters = [], []
for line in Path(session).open(encoding="utf-8"):
    try:
        item = json.loads(line)
    except ValueError:
        continue
    payload = item.get("payload", {})
    if "继续独立验收。新的冻结候选为 3458366" in str(payload):
        markers.append(item["timestamp"])
    if payload.get("type") == "token_count" and payload.get("info"):
        counters.append({"timestamp": item["timestamp"], "info": payload["info"]})
authorized = min(markers)
prior = [item for item in counters if item["timestamp"] < authorized]
(OUT / "resource-start.json").write_text(json.dumps({"session_file": session,
    "authorization_timestamp": authorized, "baseline": prior[-1] if prior else None}, indent=2), encoding="utf-8")
print(json.dumps({"byte_identical_test_copies": len(copies), "authorization_timestamp": authorized}))
