"""Approve only the reviewed D3 packEnclose export in the two shipped examples."""

from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.workflow.sync_io import write

OLD = "9ddfbf1370eb9059dce154d9a3db95f28f04c47cf5024d7f94bace9ed7be8747"
NEW = "83f6ae11335138ad959c522255264f2076bc3c02c6a6f3194f4b093b5dd6f599"
REPORT = Path(__file__).with_name("example-vendor-approval.json")
assert not REPORT.exists(), "Review evidence must not be overwritten"
report = []
for name, targets in [
    (
        "delivery",
        [
            "integrations/bo_view/routing-tools.vendor.js",
            "observer_generated/static/routing-tools.vendor.js",
        ],
    ),
    ("team-archive", ["static/graph/routing-tools.vendor.js"]),
]:
    root = ROOT / "examples" / name
    baseline = root / ".stategraph/graph-quality-20261104/baseline.json"
    baseline_hash = sha256(baseline.read_bytes()).hexdigest()
    cfg_path = root / "ownership.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    prior = json.loads(json.dumps(cfg))
    protected = {}
    for path, expected in json.loads(baseline.read_text(encoding="utf-8"))["files"].items():
        if path.startswith(("app/", "archive_app/")) or path in {
            "intent.json",
            "acceptance.json",
            "whitebox.json",
            "mapping.json",
            "discovery.json",
            "implementation.json",
            "bo_stategraph/workflow.py",
            "bo_stategraph/machine.json",
        }:
            actual = sha256((root / path).read_bytes()).hexdigest()
            assert actual == expected, f"Protected business/state/expectation drift: {name}/{path}"
            protected[path] = actual
    for path in targets:
        assert cfg["vendor_files"][path] == OLD
        assert sha256((root / path).read_bytes()).hexdigest() == NEW
        cfg["vendor_files"][path] = NEW
    restored = json.loads(json.dumps(cfg))
    for path in targets:
        restored["vendor_files"][path] = OLD
    assert restored == prior, "Only approved exact vendor pins may change"
    write(cfg_path, cfg)
    assert sha256(baseline.read_bytes()).hexdigest() == baseline_hash
    report.append(
        {
            "example": name,
            "approved_paths": targets,
            "before": OLD,
            "after": NEW,
            "reason": "Export existing pinned D3 hierarchy packEnclose for shared visible-body fitting; no dependency version or license change.",
            "baseline_sha256": baseline_hash,
            "protected_files": protected,
        }
    )
write(REPORT, {"valid": True, "examples": report})
print(
    json.dumps(
        {
            "valid": True,
            "reviewed_vendor_paths": sum(len(item["approved_paths"]) for item in report),
        }
    )
)
