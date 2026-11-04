"""Require the patch receipts and exact staged Skill before publication."""

from hashlib import sha256
import json
from pathlib import Path
import subprocess


def main():
    """Aggregate existing checks; never regenerate approvals or alter results."""
    root = Path(__file__).resolve().parents[3]
    review = root / "docs/review/graph-quality-20261104"
    names = (
        "full-verification-08-frozen.json",
        "source-quality-patch-scope.json",
        "source-scope-final-regressions.json",
        "source-scope-archive-profile-01.json",
        "source-scope-live-profile-02.json",
        "browser-patch-geometry.json",
        "browser-patch-scope-api.json",
        "clean-staged-export-patch-03.json",
        "clean-staged-export-patch-report-03.json",
        "examples-delivery-source-scope-portable-final-acceptance-summary.json",
        "examples-team-archive-source-scope-portable-final-acceptance-summary.json",
    )
    checks = []
    for name in names:
        receipt = json.loads((review / name).read_text(encoding="utf-8-sig"))
        assert receipt.get("valid") is True, name
        checks.append({"receipt": name, "valid": True})
    manifest = json.loads((Path(__file__).parent / "manifest.json").read_text())
    tree = subprocess.check_output(["git", "write-tree"], cwd=root, text=True).strip()
    skill = subprocess.check_output(
        ["git", "rev-parse", tree + ":skills/vibelens"], cwd=root, text=True
    ).strip()
    assert manifest["passed"] and skill == manifest["skill_tree"]
    clean = json.loads((review / "clean-staged-export-patch-report-03.json").read_text())
    example_trees = {}
    for name in ("delivery", "team-archive"):
        prefix = ":examples/" + name
        checked = subprocess.check_output(
            ["git", "rev-parse", clean["revision"] + prefix], cwd=root, text=True
        ).strip()
        staged = subprocess.check_output(
            ["git", "rev-parse", tree + prefix], cwd=root, text=True
        ).strip()
        assert checked == staged, "Example changed after its clean export: " + name
        example_trees[name] = checked
    archive = root / manifest["archive"]
    assert sha256(archive.read_bytes()).hexdigest() == manifest["archive_sha256"]
    protected = json.loads((review / "protected-core.json").read_text())
    for item in protected["files"]:
        assert sha256((root / item["path"]).read_bytes()).hexdigest() == item["sha256"]
    result = {
        "valid": True,
        "checks": checks,
        "skill_tree": skill,
        "archive_sha256": manifest["archive_sha256"],
        "protected_core_files": len(protected["files"]),
        "clean_example_trees": example_trees,
        "scope": "Local patch gates and frozen staged package; remote CI and dialogue reported separately",
    }
    (Path(__file__).parent / "candidate-gate.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
