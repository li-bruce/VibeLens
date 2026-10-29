"""Check native upgrade parity and review the unchanged business candidate."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "observer_runtime"))
from behavior_model import capture
from sync_config import config, snapshot
from sync_io import write

def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8-sig"))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

before = json.loads((OUT / "before.json").read_text(encoding="utf-8"))
changed = [name for name, value in before["protected_files"].items()
           if digest(ROOT / name) != value]
for name in ("bo_stategraph/project.json", "review/evidence_checks.py"):
    if digest(ROOT / name) != before["source_files"][name]:
        changed.append(name)
assert not changed, changed
project = read("bo_stategraph/project.json")
for part, value in before["declaration_hashes"].items():
    actual = json.dumps(project["model"][part], ensure_ascii=False, sort_keys=True, indent=2).encode()
    assert hashlib.sha256(actual).hexdigest() == value, part
version = read("bo_stategraph/runtime-version.json")
mismatches = [name for name, value in version["files"].items() if digest(ROOT / name) != value]
assert not mismatches, mismatches
changes = [name for name, value in before["installed_files"].items()
           if version["files"].get(name) != value]
assert changes == ["static/graph/semantic-view.js"], changes
canonical = ROOT.parent / "vibelens-focus-fix"
head = subprocess.check_output(["git", "-C", str(canonical), "rev-parse", "HEAD"], text=True).strip()
dirty = subprocess.check_output(["git", "-C", str(canonical), "status", "--porcelain"], text=True)
assert head == "3458366f72563b35749a9f7bcf799c2b7e22da00" and not dirty
for name in changes:
    asset = canonical / "skills/vibelens/assets/stategraph-viewer" / Path(name).name
    assert (ROOT / name).read_bytes() == asset.read_bytes()
manifest = capture(ROOT, project["model"])
write(ROOT / "manifest.json", manifest)
result = {"canonical_revision": head, "canonical_worktree_clean": True,
          "managed_files": len(version["files"]), "managed_mismatches": mismatches,
          "managed_changes": changes, "protected_files_unchanged": len(before["protected_files"]),
          "project_declaration_byte_identical": True, "evidence_audit_byte_identical": True,
          "state_and_policy_unchanged": True, "before_build": before["build_id"],
          "after_build": manifest["build_id"],
          "build_changed": before["build_id"] != manifest["build_id"],
          "recording_reuse": "Refuse reuse if build changed; preserve the original and capture the necessary short chain.",
          "native_upgrade": True, "shims": False}
write(OUT / "parity.json", result)
write(ROOT / "review/implementation-version.json", {
    "canonical_revision": head,
    "previous_accepted_revision": "b78f03a89e1726f951ea76d4e0781efd2e869fe6",
    "confirmation_source": "Explicit framework-only upgrade request forwarded in this chat",
    "original_v2_provenance": "framework-upgrade-3458366/b78-evidence.zip:review/implementation-version.json",
    "independent_human_acceptance": False})
candidate = snapshot(ROOT, config(ROOT, "sync.json"))
write(ROOT / ".stategraph/framework-upgrade-3458366/review.json", {
    "candidate_id": candidate["id"], "author": "Coding agent; technical upgrade review",
    "source": "review/framework-upgrade-3458366/dialogue.zh-CN.md; explicit framework-only authorization",
    "decisions": {part: {"action": "unchanged", "reason": reason} for part, reason in {
        "business": "No business change; all application source, requirements, independent assertions and original tests are byte-identical.",
        "state_machine": "The entire project declaration, native machine and policy networks remain byte-identical.",
        "abstraction": "Stable nodes, source bindings, grouping and declarations are unchanged; native viewer assets only were upgraded.",
        "probes": "All capture wiring, selected fields, modes, cases and original evidence audit remain byte-identical. Build identity updates from managed metadata require fresh evidence."
    }.items()}, "requirement_changes": {}, "excluded_symbols": {}})
print(json.dumps(result))
