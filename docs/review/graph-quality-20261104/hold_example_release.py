"""Retain the first candidate while deferring published receipts for final fixes."""

from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_upgrade import replace_copy
from bo_observer.workflow.sync_io import write

project = ROOT / "examples/delivery"
retained = project / ".release/stategraph/graph-quality-20261104-first-candidate"
assert retained.is_dir()
report = Path(__file__).with_name("example-release-hold.json")
assert not report.exists(), "Evidence is immutable"
for source, target in [("manifest.json", "manifest.json"), ("README.md", "release-note.md")]:
    assert not (retained / target).exists()
    shutil.copyfile(project / ".release" / source, retained / target)
restored = {}
for relative in (".release/stategraph/active.json", ".release/manifest.json", ".release/README.md"):
    original = subprocess.check_output(
        ["git", "show", "HEAD:examples/delivery/" + relative], cwd=ROOT
    )
    replace_copy(original, project / relative)
    restored[relative] = sha256(original).hexdigest()
write(
    report,
    {
        "status": "First candidate retained; final receipt publication waits for caption and adapter fixes.",
        "first_candidate": str(retained.relative_to(ROOT)),
        "restored_previous_published_records": restored,
        "reason": "The delivery candidate completed before the hold marker was created. Its native checks passed; subsequent real browser and full-gate findings require a newer candidate on the same baseline.",
    },
)
print(
    json.dumps({"valid": True, "first_candidate_retained": True, "final_publication_pending": True})
)
