"""Revalidate already-opened managed example updates without changing business rules."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
os.environ["BO_ADAPTER_HOME"] = str(ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript")
CHANGE = os.environ.get("BO_EXAMPLE_CHANGE", ".stategraph/execution-lanes-20261031")
OUT = Path(__file__).resolve().parent
REASON = os.environ.get("BO_EXAMPLE_REASON") or (
    "Managed observer update: causal execution bands with one row per graph layer, "
    "shared centre/rim edge anchors, Python/JavaScript span recognition, source-derived "
    "iteration recall and independent invocation-closure checks. Native business code, "
    "definitions, required scenarios, capture fields and verification modes are unchanged."
)


def run(root, *argv, inspecting=False):
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", *map(str, argv)], cwd=root,
                            capture_output=True, text=True, encoding="utf-8")
    value = json.loads(result.stdout) if result.stdout.strip().startswith("{") else {"output": result.stdout}
    if result.returncode and not inspecting:
        raise RuntimeError(json.dumps({"argv": argv, "output": value, "stderr": result.stderr}, default=str))
    return value


def main():
    receipts = []
    for name, runtime in (("delivery", "observer_generated/runtime"), ("team-archive", "observer_runtime")):
        if os.environ.get("BO_EXAMPLE_TARGET") not in (None, name):
            continue
        root = ROOT / "examples" / name
        cfg = json.loads((root / "sync.json").read_text(encoding="utf-8"))
        diff = subprocess.check_output(["git", "diff", "HEAD", "--", *[str(root / item) for item in cfg["code_files"]]], cwd=ROOT, text=True)
        if diff.strip():
            raise ValueError("Unreviewed native application change: " + name)
        cli = root / runtime / "change_sync.py"
        if sys.argv[1:] == ["begin"]:
            checked = run(root, cli, "check", "--root", ".")
            begun = run(root, cli, "begin", "--root", ".", "--change", CHANGE, "--request", REASON)
            receipts.append({"project": name, "check": checked, "begin": begun})
            print(name + " change opened", flush=True)
            continue
        previous = Path(json.loads((root / ".release/stategraph/active.json").read_text())["change"]).name
        review = json.loads((root / ".release/stategraph" / previous / "review.json").read_text(encoding="utf-8"))
        if name == "delivery":
            run(root, "tooling/dev.py", "graph", "--reason", REASON)
        else:
            run(root, "tooling/build_model.py")
            run(root, runtime + "/architecture_guard.py", "seal", "--root", ".", "--reason", REASON)
        impact = run(root, cli, "inspect", "--root", ".", inspecting=True)
        review["candidate_id"] = impact["candidate_id"]
        review["decisions"] = {part: {"action": "updated" if part == "probes" else "unchanged", "reason": REASON}
                               for part in ("business", "state_machine", "abstraction", "probes")}
        (root / CHANGE / "review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
        receipt = {"project": name, "candidate_id": impact["candidate_id"]}
        for command in ("verify", "accept", "check", "recall"):
            receipt[command] = run(root, cli, command, "--root", ".")
        destination = root / ".release/stategraph" / Path(CHANGE).name
        if destination.exists():
            raise ValueError("Frozen checkpoint already exists: " + str(destination))
        shutil.copytree(root / CHANGE, destination)
        shutil.copyfile(root / ".stategraph/active.json", root / ".release/stategraph/active.json")
        shutil.copyfile(root / cfg["manifest"], root / ".release/manifest.json")
        receipts.append(receipt)
        print(name + " verified, accepted and frozen", flush=True)
    suffix = "begin" if sys.argv[1:] == ["begin"] else "verification"
    (OUT / (Path(CHANGE).name + "-" + suffix + ".json")).write_text(json.dumps(receipts, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
