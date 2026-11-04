"""Run the existing example workflow and freeze its reviewed acceptance receipts."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
CHANGE = "graph-quality-20261104"
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.workflow.sync_io import write
from bo_upgrade import plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("example", choices=["delivery", "team-archive"])
    parser.add_argument("--pass-label", default="final")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--frozen-label", default=CHANGE)
    parser.add_argument(
        "--review-note", default="", help="Describe the reviewed follow-up without replacing guards"
    )
    args = parser.parse_args()
    assert args.pass_label.replace("-", "").isalnum(), "Use a simple evidence pass label"
    assert args.frozen_label.replace("-", "").isalnum(), "Use a simple frozen record label"
    root = ROOT / "examples" / args.example
    delivery = args.example == "delivery"
    runtime = "observer_generated/runtime" if delivery else "observer_runtime"
    change = root / ".stategraph" / CHANGE
    baseline = json.loads((change / "baseline.json").read_text(encoding="utf-8"))
    baseline_hash = sha256((change / "baseline.json").read_bytes()).hexdigest()
    prior = json.loads((EVIDENCE / "example-vendor-approval.json").read_text(encoding="utf-8"))
    approved = next(item for item in prior["examples"] if item["example"] == args.example)
    assert (
        baseline_hash == approved["baseline_sha256"]
    ), "Original change baseline must remain intact"
    for path, expected in approved["protected_files"].items():
        assert sha256((root / path).read_bytes()).hexdigest() == expected, path
    environment = {
        **os.environ,
        "BO_ADAPTER_HOME": str(ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript"),
    }
    results = []

    def run(stage, *argv, expected=0):
        name = f"examples-{args.example}-{args.pass_label}-{stage}"
        status = EVIDENCE / f"{name}.json"
        log = EVIDENCE / f"{name}.log"
        assert not status.exists() and not log.exists(), "Evidence is immutable: " + name
        with log.open("w", encoding="utf-8", newline="\n") as stream:
            process = subprocess.run(
                argv,
                cwd=root,
                env=environment,
                stdout=stream,
                stderr=subprocess.STDOUT,
                timeout=1200,
                check=False,
            )
        expected_codes = (expected,) if isinstance(expected, int) else expected
        result = {
            "stage": stage,
            "command": list(argv),
            "exit_code": process.returncode,
            "expected_exit_code": expected,
            "valid": process.returncode in expected_codes,
            "log": log.name,
        }
        write(status, result)
        results.append(result)
        print(json.dumps({"example": args.example, **result}), flush=True)
        assert process.returncode in expected_codes, log.read_text(encoding="utf-8")[-6000:]

    python = (sys.executable, "-B", "-X", "utf8")
    review_note = args.review_note.strip()
    run("generate", *python, "tooling/build_graph.py" if delivery else "tooling/build_model.py")
    run(
        "seal",
        *python,
        f"{runtime}/architecture_guard.py",
        "seal",
        "--root",
        ".",
        "--reason",
        "Reviewed graph-quality viewer/API/source-mapping update, complete planar labels, explicit D3 packEnclose export and exact vendor hash; business/state definitions and expectations retained."
        + (" " + review_note if review_note else ""),
    )
    run("scan", *python, f"{runtime}/bo_sync.py", "scan", "--root", ".")
    run(
        "inspect-before-review",
        *python,
        f"{runtime}/change_sync.py",
        "inspect",
        "--root",
        ".",
        expected=(0, 1),
    )
    impact = json.loads((change / "impact.json").read_text(encoding="utf-8"))
    assert not impact["errors"]
    assert set(impact["review_errors"]) <= {
        "missing review.json for this candidate",
        "review belongs to an older candidate",
    }
    assert not impact["changed_requirements"]
    structure = json.loads((change / "structure.json").read_text(encoding="utf-8"))
    excluded = {}
    for symbol in impact.get("required_classification", []):
        path = symbol.split("::", 1)[0]
        assert baseline["files"].get(path) == sha256((root / path).read_bytes()).hexdigest(), (
            "Review needs an implementation decision for changed business source: " + symbol
        )
        if structure["symbols"][symbol].get("kind") == "class":
            excluded[symbol] = (
                "Unchanged class or enumeration container. Executable methods, declared states, parameter mappings and independent runtime expectations retain their existing coverage."
            )
        else:
            assert path.endswith("ports.py") or path in {
                "integrations/bo_observer.py",
                "integrations/bo_server.py",
                "run.py",
                "static/app.js",
            }, (
                "Review an unrecognized support symbol explicitly: " + symbol
            )
            excluded[symbol] = (
                "Existing optional observation transport, request dispatch or application startup support; source bytes are unchanged from the preserved baseline. Delegated business actions retain source nodes, probes, parameters and independent scenarios. This review changes no implementation classification."
            )
    review = {
        "candidate_id": impact["candidate_id"],
        "excluded_symbols": excluded,
        "requirement_changes": {},
        "decisions": {
            "business": {
                "action": "unchanged",
                "reason": "Business source, user-confirmed behavior and independent business expectations match the preserved baseline byte for byte.",
            },
            "state_machine": {
                "action": "unchanged",
                "reason": "Native workflow, state definitions, transitions, resources and join behavior match the preserved baseline; drive mode and its decision remain unchanged.",
            },
            "abstraction": {
                "action": "updated",
                "reason": "Regenerated source metadata and graph mapping with the maintained parser. Viewer enclosures fit visible content and full planar labels; filtering retains owner identity and source proximity only changes layout. HTTP runtime aliases require exact source identity, method and route. Legacy source traversal is used only for focus selection and supplies no HTTP activation or duration. Approved D3 packEnclose export is pinned by exact SHA-256; original semantic IDs and native declarations remain stable.",
            },
            "probes": {
                "action": "unchanged",
                "reason": "No capture field, required runtime case, probe assertion or independent whitebox expectation was removed. Observer operations remain outside business recordings.",
            },
        },
    }
    if review_note:
        review["decisions"]["abstraction"]["reason"] += " " + review_note
    write(change / "review.json", review)
    for stage in ("inspect", "verify", "accept", "check"):
        run(stage, *python, f"{runtime}/change_sync.py", stage, "--root", ".")
    assert sha256((change / "baseline.json").read_bytes()).hexdigest() == baseline_hash
    if not args.freeze:
        write(
            EVIDENCE / f"examples-{args.example}-{args.pass_label}-acceptance-summary.json",
            {
                "valid": True,
                "baseline_sha256": baseline_hash,
                "candidate_id": review["candidate_id"],
                "frozen": False,
                "checks": results,
            },
        )
        return
    viewers = (
        ["integrations/bo_view", "observer_generated/static"] if delivery else ["static/graph"]
    )
    for directory in viewers:
        for canonical in (ROOT / "skills/vibelens/assets/stategraph-viewer").iterdir():
            if canonical.is_file():
                assert (root / directory / canonical.name).read_bytes() == canonical.read_bytes(), (
                    "Viewer changed again before freeze: " + canonical.name
                )
    pending = plan(root, runtime=runtime, viewers=viewers)
    assert pending["valid"] and not pending["changes"] and not pending["retired_files"], (
        "Runtime or adapter changed again before freeze",
        pending["conflicts"],
        pending["changes"],
    )
    release = root / ".release"
    target = release / "stategraph" / args.frozen_label
    assert not target.exists(), "Never replace a previous frozen acceptance record"
    shutil.copytree(change, target)
    for name in ("source-baseline.json", "maintenance.json"):
        shutil.copyfile(root / ".stategraph" / name, release / "stategraph" / name)
    write(release / "stategraph/active.json", {"change": ".stategraph/" + args.frozen_label})
    manifest = "observer_generated/manifest.json" if delivery else "manifest.json"
    shutil.copyfile(root / manifest, release / "manifest.json")
    old_readme = (release / "README.md").read_text(encoding="utf-8")
    header = f"# Reviewed release records\n\nThe current record is `{args.frozen_label}`. The reviewed viewer fits visible\ncontents and full planar labels, preserves filtered owner identities, and uses the\nexisting pinned D3 enclosing-circle implementation. Source mapping and API metadata\nwere regenerated; native business/state code, probes and expectations are unchanged.\nNormal generate, seal, scan, inspect, verify, accept and check passed before these\nreceipts were frozen. Earlier records remain below.\n\n## Previous records\n\n"
    (release / "README.md").write_text(header + old_readme, encoding="utf-8", newline="\n")
    write(
        EVIDENCE / f"examples-{args.example}-{args.pass_label}-acceptance-summary.json",
        {
            "valid": True,
            "baseline_sha256": baseline_hash,
            "candidate_id": review["candidate_id"],
            "frozen_change": args.frozen_label,
            "source_change": CHANGE,
            "canonical_runtime_current": True,
            "checks": results,
        },
    )


if __name__ == "__main__":
    main()
