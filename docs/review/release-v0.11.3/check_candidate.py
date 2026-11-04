"""Aggregate retained v0.11.3 receipts and verify the exact staged release inputs."""

from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile


SKILL_TREE = "2df145bcd7839014c9382029723f43bc6e0dd3c6"
ARCHIVE_SHA256 = "cbf8c8ef647033cf74fbe372724084a5f49e8a67b14c8e7c881a966cd85df0ac"
FROZEN_CHANGE = "graph-quality-20261104-timeline-inspection-0113"
BROWSER_RECEIPTS = ("publication/timeline-inspection-0113/summary.json",)


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

    require(re.fullmatch(r"[0-9a-f]{40}", SKILL_TREE), "Frozen v0.11.3 Skill tree is pending.")
    require(re.fullmatch(r"[0-9a-f]{64}", ARCHIVE_SHA256), "Frozen v0.11.3 archive is pending.")
    full = receipt("full-verification-11-timeline-inspection-host.json")
    require(
        "tools/verify.py" in full["command"] and "--database" in full["command"],
        "Full host gate must include the existing database checks.",
    )
    receipt("source-quality-0113.json")
    receipt("source-quality-0113-harness-final-02.json")
    receipt("package-copies-0113.json")
    receipt("clean-staged-export-timeline-inspection-0113.json")
    clean = receipt("clean-staged-export-timeline-inspection-0113-report.json")
    parity = receipt("example-timeline-inspection-0113-staged-parity.json")
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
        manifest.get("passed") is True and manifest["tag"] == "v0.11.3",
        "Release manifest is not a passing v0.11.3 package.",
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
            "examples-" + name + "-timeline-inspection-0113-final-acceptance-summary.json"
        )
        post_name = "delivery" if name == "delivery" else "archive"
        receipt("examples-" + post_name + "-timeline-inspection-0113-post-freeze-check.json")
        require(summary["canonical_runtime_current"] is True, "Stale example runtime: " + name)
        require(summary["frozen_change"] == FROZEN_CHANGE, "Wrong frozen example change: " + name)
        require(
            all(item["valid"] is True for item in summary["checks"]),
            "A native example stage failed: " + name,
        )
        require(
            compared[name]["release"] == "0.11.3"
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

    # This patch changes the viewer. Previous tag equality cannot substitute for
    # actual current UI checks. Each receipt must retain its tested source hashes.
    require(BROWSER_RECEIPTS, "Fresh v0.11.3 browser receipts are pending.")
    current_browser = []
    for name in BROWSER_RECEIPTS:
        browser = receipt(name)
        sources = browser.get("source_hashes", {})
        product = "skills/vibelens/assets/stategraph-viewer/recording-timeline.js"
        require(
            product in sources, "Browser receipt does not identify the changed product: " + name
        )
        for source, digest in sources.items():
            require(
                sha256(git("show", staged_tree + ":" + source)).hexdigest() == digest,
                "Browser-tested source differs from staged source: " + source,
            )
        expected_variants = {
            "registered-01",
            "registered-02",
            "registered-03",
            "default",
            "midspan",
            "bands",
            "bands-midspan",
        }
        runs = browser["runs"]
        require(
            {item["variant"] for item in runs} == expected_variants,
            "Current browser variants are incomplete.",
        )
        for run in runs:
            require(
                run["passed"] is True and run["exit_code"] == 0,
                "A current browser command failed: " + run["variant"],
            )
            path = root / run["result"]
            require(
                sha256(path.read_bytes()).hexdigest() == run["result_sha256"]
                and read_json(path)["passed"] is True,
                "Current browser result changed or failed: " + run["variant"],
            )
            if not run["variant"].startswith("registered-"):
                continue
            motion = read_json(root / run["paused_motion"])
            before, after = motion["pausedWitness"], motion["nextWitness"]
            require(
                run["witness_min_ms"] > 1100
                and before["elapsedMilliseconds"] > 1100
                and before["frames"] > 0
                and after["frames"] > 0,
                "Paused inspection was not tested beyond the former settlement boundary.",
            )
            require(
                before["eventId"] == after["eventId"] == motion["fixedEvent"]
                and before["raw"] == after["raw"]
                and before["graphTransfers"] == after["graphTransfers"] == 0
                and run["graph_transfers"] == 0
                and run["raw_unchanged"] is True,
                "The isolated paused connector case changed its raw event or graph transfers.",
            )
            require(
                motion["moving"] is True
                and run["screens_differ"] is True
                and (path.parent / "connector-motion-a.png").read_bytes()
                != (path.parent / "connector-motion-b.png").read_bytes(),
                "The paused selected connector did not visibly continue moving.",
            )
        require(
            len(browser["units"]) >= 4
            and all(item["passed"] is True and item["exit_code"] == 0 for item in browser["units"]),
            "Current timeline unit regressions did not pass.",
        )
        current_browser.append({"receipt": name, "sources": sources})
    viewer_path = ":skills/vibelens/assets/stategraph-viewer"
    viewer = git_text("rev-parse", staged_tree + viewer_path)

    # The universal acknowledgment repair also changes maintained test tools.
    # Require their complete browser runs and the exact tested helper/tool bytes.
    harness_name = "publication/preference-ack-0113/summary.json"
    harness = receipt(harness_name)
    harness_folder = (review / harness_name).parent
    for name in ("names", "viewer", "helper"):
        case = harness["cases"][name]
        require(case["valid"] is True, "Preference acknowledgment case failed: " + name)
        result = read_json(harness_folder / case["result"])
        require(
            result.get("valid") is True or result.get("passed") is True,
            "Preference acknowledgment browser/helper result failed: " + name,
        )
        if name != "helper":
            command = read_json(harness_folder / case["command"])
            require(
                command["exit_code"] == 0 and command["valid"] is True,
                "Preference acknowledgment Chrome command failed: " + name,
            )
    code_harness_name = "publication/code-browser-ack/summary.json"
    code_harness = receipt(code_harness_name)
    code_result = root / code_harness["result"]
    require(
        sha256(code_result.read_bytes()).hexdigest() == code_harness["result_sha256"]
        and read_json(code_result)["passed"] is True,
        "Complete code-browser acknowledgment regression did not pass.",
    )
    current_harness = []
    for name, summary in ((harness_name, harness), (code_harness_name, code_harness)):
        sources = summary["source_hashes"]
        require(sources, "Acknowledgment receipt has no tested sources: " + name)
        for source, digest in sources.items():
            require(
                sha256(git("show", staged_tree + ":" + source)).hexdigest() == digest,
                "Acknowledgment-tested source differs from staged source: " + source,
            )
        current_harness.append({"receipt": name, "sources": sources})

    retained_failures = []
    for name in (
        "full-verification-09-reserved-scope.json",
        "publication/ci-main-41807986096-timeline-failed.log",
        "publication/ci-tag-41807986087-timeline-failed.log",
        "publication/main-ad50-timeline/original-ci/result.json",
        "publication/lifecycle-registered-motion-diagnostic-01/diagnosis.json",
        "trial-audit/scope-reserved-assessment/result-01.json",
        "trial-audit/scope-reserved-assessment/result-02.json",
        "publication/ci-main-7cc0bce9-browser-failure.json",
    ):
        path = review / name
        require(path.is_file(), "Missing retained failure evidence: " + name)
        retained_failures.append({"receipt": name, "sha256": sha256(path.read_bytes()).hexdigest()})

    result = {
        "valid": True,
        "release": "v0.11.3",
        "checks": checks,
        "skill_tree": staged_skill,
        "archive_sha256": ARCHIVE_SHA256,
        "archive_files": len(entries),
        "protected_core_files": len(protected["files"]),
        "clean_export_revision": clean["revision"],
        "clean_example_trees": example_trees,
        "compared_frozen_example_inputs": parity["compared_current_inputs"],
        "current_frontend_proof": {
            "receipts": current_browser,
            "viewer_assets_tree": viewer,
            "basis": "Fresh real-browser receipts identify the exact staged changed product sources.",
        },
        "current_harness_proof": current_harness,
        "retained_failures": retained_failures,
        "scope": "Local frozen-candidate gates only. v0.11.3 remote CI, publication and installation are separate.",
    }
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
