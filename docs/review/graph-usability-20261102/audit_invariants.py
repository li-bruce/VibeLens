"""Verify protected native semantics, personal files, IDs and managed-copy parity."""

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "skills/vibelens/scripts"))
from bo_upgrade import plan


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    baseline = json.loads((OUT / "baseline.json").read_text(encoding="utf-8"))
    trial = json.loads((OUT / "trial-preservation-before.json").read_text(encoding="utf-8"))
    trial_root = Path(trial["root"])
    changed_core = [
        name for name, value in baseline["protected"].items() if digest(REPO / name) != value
    ]
    changed_trial = [
        name for name, value in trial["sha256"].items() if digest(trial_root / name) != value
    ]
    native_js = "skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs"
    old_js = subprocess.check_output(
        ["git", "show", baseline["head"] + ":" + native_js], cwd=REPO
    ).decode("utf-8")
    current_js = (REPO / native_js).read_text(encoding="utf-8")
    marker = "export function bo_selected"
    if marker not in old_js or marker not in current_js:
        raise ValueError("Native JavaScript executor boundary was not found")
    js_equal = old_js.split(marker, 1)[0] == current_js.split(marker, 1)[0]
    project = json.loads((trial_root / "bo_stategraph/project.json").read_text(encoding="utf-8"))
    ids_equal = sorted(node["id"] for node in project["model"]["nodes"]) == trial["node_ids"]
    copies = []
    for name, root, runtime, viewers in (
        ("delivery", REPO / "examples/delivery", "observer_generated/runtime",
         ["observer_generated/static", "integrations/bo_view"]),
        ("team-archive", REPO / "examples/team-archive", "observer_runtime", ["static/graph"]),
        ("independent-trial", trial_root, "observer_runtime", ["static/graph"]),
    ):
        value = plan(root, runtime=runtime, viewers=viewers)
        copies.append({
            "project": name, "managed_files": len(value["files"]),
            "changes": value["changes"], "conflicts": value["conflicts"],
            "retired_files": value["retired_files"],
            "current": value["valid"] and not value["changes"] and not value["retired_files"],
        })
    report = {
        "passed": not changed_core and not changed_trial and js_equal and ids_equal
                  and all(item["current"] for item in copies),
        "protected_core_files": len(baseline["protected"]), "changed_core": changed_core,
        "javascript_native_executor_unchanged": js_equal,
        "protected_trial_files": len(trial["sha256"]), "changed_trial": changed_trial,
        "stable_trial_ids": len(trial["node_ids"]), "ids_unchanged": ids_equal,
        "managed_copies": copies,
    }
    (OUT / "invariants-final.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
