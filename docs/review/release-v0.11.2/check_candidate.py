"""Aggregate retained v0.11.2 receipts and verify the exact staged release inputs."""

from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile


SKILL_TREE = "82b7f501697334bb83a82b5863ac7c068785b6bf"
ARCHIVE_SHA256 = "4fc87cc1f9ab08fcaf69f64cdbf1e4bc2c73f882e0ab9c9ff85f2e501a402607"
FROZEN_CHANGE = "graph-quality-20261104-reserved-boundaries-0112"


def require(condition, message):
    """Fail closed rather than inventing a passing or pending receipt."""
    if not condition:
        raise ValueError(message)


def read_json(path):
    """Read the existing evidence without regenerating or replacing it."""
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main():
    """Publish one local aggregate only after every required input is available."""
    folder = Path(__file__).resolve().parent
    root = folder.parents[2]
    review = root / "docs/review/graph-quality-20261104"
    output = folder / "candidate-gate.json"
    require(not output.exists(), "Candidate gate already exists; retain it as evidence.")

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=root)

    def git_text(*args):
        return git(*args).decode("utf-8").strip()

    checks = []

    def receipt(name):
        path = review / name
        value = read_json(path)
        require(value.get("valid") is True, "Failed receipt: " + name)
        require(value.get("exit_code", 0) == 0, "Failed command: " + name)
        checks.append(
            {"receipt": name, "valid": True, "sha256": sha256(path.read_bytes()).hexdigest()}
        )
        return value

    full = receipt("full-verification-10-reserved-scope-host.json")
    require(
        "tools/verify.py" in full["command"] and "--database" in full["command"],
        "Full host gate must include the existing database checks.",
    )
    receipt("source-quality-0112.json")
    receipt("package-copies-0112.json")
    receipt("clean-staged-export-reserved-boundaries-0112.json")
    clean = receipt("clean-staged-export-reserved-boundaries-0112-report.json")
    parity = receipt("example-reserved-boundaries-0112-staged-parity-02.json")
    require(
        parity["compared_current_inputs"] == 682 and parity["mismatches"] == [],
        "Frozen example input parity is incomplete.",
    )
    require(
        parity["historical_review_index_equals_head"] is True,
        "Historical example review evidence changed in the index.",
    )

    focused_path = review / "trial-audit/scope-reserved-assessment/fix-regressions.json"
    focused = read_json(focused_path)
    focused_counts = {}
    for name, expected in {"scope": 25, "code": 31, "api": 20, "docs": 18}.items():
        result = focused[name]
        match = re.search(r"Ran\s+(\d+)\s+tests", result["output"])
        require(
            result["exit_code"] == 0 and match is not None and int(match[1]) >= expected,
            "Incomplete current focused regressions: " + name,
        )
        focused_counts[name] = int(match[1])
    checks.append(
        {
            "receipt": str(focused_path.relative_to(review)).replace("\\", "/"),
            "valid": True,
            "sha256": sha256(focused_path.read_bytes()).hexdigest(),
            "tests": focused_counts,
        }
    )

    manifest = read_json(folder / "manifest.json")
    require(
        manifest.get("passed") is True and manifest["tag"] == "v0.11.2",
        "Release manifest is not a passing v0.11.2 package.",
    )
    require(
        manifest["fresh_install_matches_archive"] is True,
        "Fresh archive installation was not verified.",
    )
    require(manifest["implicit_invocation"] is False, "Explicit Skill invocation is required.")
    require(
        manifest["skill_tree"] == SKILL_TREE and manifest["archive_sha256"] == ARCHIVE_SHA256,
        "Release package differs from the frozen candidate.",
    )

    staged_tree = git_text("write-tree")
    staged_skill = git_text("rev-parse", staged_tree + ":skills/vibelens")
    require(staged_skill == SKILL_TREE, "Staged Skill changed after packaging.")
    require(
        git_text("rev-parse", clean["revision"] + ":skills/vibelens") == SKILL_TREE,
        "Clean export checked a different Skill.",
    )
    archive = root / manifest["archive"]
    require(
        sha256(archive.read_bytes()).hexdigest() == ARCHIVE_SHA256,
        "Archive bytes changed after packaging.",
    )
    entries = {item["path"]: item["sha256"] for item in manifest["files"]}
    require(len(entries) == manifest["skill_files"] == 305, "Archive file inventory is incomplete.")
    with ZipFile(archive) as zipped:
        names = [name for name in zipped.namelist() if not name.endswith("/")]
        require(
            len(names) == len(set(names)) and set(names) == set(entries),
            "ZIP paths differ from the frozen manifest.",
        )
        for name, digest in entries.items():
            require(
                sha256(zipped.read(name)).hexdigest() == digest,
                "ZIP entry differs from the manifest: " + name,
            )
            require(
                sha256(git("show", staged_tree + ":skills/" + name)).hexdigest() == digest,
                "ZIP entry differs from staged Skill content: " + name,
            )

    native = {item["example"]: item for item in clean["examples"]}
    compared = {item["example"]: item for item in parity["examples"]}
    require(
        set(native) == set(compared) == {"delivery", "team-archive"},
        "Both frozen examples must be covered.",
    )
    example_trees = {}
    for name in ("delivery", "team-archive"):
        summary = receipt(
            "examples-" + name + "-reserved-boundaries-0112-final-acceptance-summary.json"
        )
        post_name = "delivery" if name == "delivery" else "archive"
        receipt("examples-" + post_name + "-reserved-boundaries-0112-post-freeze-check.json")
        require(summary["canonical_runtime_current"] is True, "Stale example runtime: " + name)
        require(summary["frozen_change"] == FROZEN_CHANGE, "Wrong frozen example change: " + name)
        require(
            all(item["valid"] is True for item in summary["checks"]),
            "A native example stage failed: " + name,
        )
        require(
            compared[name]["release"] == "0.11.2"
            and compared[name]["post_freeze_current_check"] is True,
            "Example was not checked after its current freeze: " + name,
        )
        require(native[name]["exit_code"] == 0, "Isolated native example failed: " + name)
        native_result, _ = json.JSONDecoder().raw_decode(native[name]["output"].lstrip())
        require(
            native_result["valid"] is True
            and native_result["status"] == "current"
            and native_result["errors"] == [],
            "Isolated native check is not current: " + name,
        )
        require(
            native_result["candidate_id"]
            == summary["candidate_id"]
            == compared[name]["candidate_id"],
            "Example candidate identity differs across receipts: " + name,
        )
        require(
            summary["baseline_sha256"] == compared[name]["baseline_sha256"],
            "Example baseline identity changed: " + name,
        )
        prefix = ":examples/" + name
        checked = git_text("rev-parse", clean["revision"] + prefix)
        staged = git_text("rev-parse", staged_tree + prefix)
        require(checked == staged, "Example changed after the clean export: " + name)
        example_trees[name] = checked

    protected = read_json(review / "protected-core.json")
    require(
        protected["valid"] is True and len(protected["files"]) == 6,
        "Protected core inventory is incomplete.",
    )
    for item in protected["files"]:
        require(item["unchanged"] is True, "Protected core was not confirmed: " + item["path"])
        require(
            sha256((root / item["path"]).read_bytes()).hexdigest() == item["sha256"],
            "Protected working-tree core changed: " + item["path"],
        )
        require(
            sha256(git("show", staged_tree + ":" + item["path"])).hexdigest() == item["sha256"],
            "Protected staged core changed: " + item["path"],
        )

    # Frontend assets are byte-identical to the official, independently checked
    # tag. Changed Python source boundaries have their own current gates above.
    prior_browser = read_json(review / "publication/ci-tag-7cc0bce9-final.json")
    require(
        prior_browser["all_green"] is True
        and prior_browser["passed"] == prior_browser["total"] == 8,
        "Retained official-tag browser proof did not pass.",
    )
    viewer_path = ":skills/vibelens/assets/stategraph-viewer"
    viewer = git_text("rev-parse", staged_tree + viewer_path)
    require(
        viewer == git_text("rev-parse", "v0.11.1" + viewer_path),
        "Changed viewer assets require fresh browser evidence.",
    )
    require(
        any(
            item["name"] == "timeline-browser" and item["conclusion"] == "success"
            for item in prior_browser["jobs"]
        ),
        "Retained browser job is missing.",
    )

    retained_failures = []
    for name in (
        "full-verification-09-reserved-scope.json",
        "trial-audit/scope-reserved-assessment/result-01.json",
        "trial-audit/scope-reserved-assessment/result-02.json",
        "publication/ci-main-7cc0bce9-browser-failure.json",
    ):
        path = review / name
        require(path.is_file(), "Missing retained failure evidence: " + name)
        retained_failures.append({"receipt": name, "sha256": sha256(path.read_bytes()).hexdigest()})

    result = {
        "valid": True,
        "release": "v0.11.2",
        "checks": checks,
        "skill_tree": staged_skill,
        "archive_sha256": ARCHIVE_SHA256,
        "archive_files": len(entries),
        "protected_core_files": len(protected["files"]),
        "clean_export_revision": clean["revision"],
        "clean_example_trees": example_trees,
        "compared_frozen_example_inputs": parity["compared_current_inputs"],
        "retained_frontend_proof": {
            "receipt": "publication/ci-tag-7cc0bce9-final.json",
            "viewer_assets_tree": viewer,
            "basis": "Exact staged viewer subtree equals the passing official v0.11.1 tag.",
            "boundary": "Frontend proof only; current Python and reserved-scope checks are listed above.",
        },
        "retained_failures": retained_failures,
        "scope": "Local frozen-candidate gates only. v0.11.2 remote CI, publication and installation are separate.",
    }
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
