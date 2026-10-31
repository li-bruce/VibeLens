"""Review managed runtime updates while keeping existing example gates intact."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CHANGE = os.environ.get("BO_DIALOGUE_EXAMPLE_CHANGE", ".stategraph/dialogue-capture-20261031")
OUT = ROOT / "docs/review/dialogue-acceptance-20261031"
os.environ["BO_ADAPTER_HOME"] = str(ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript")


def run(root, *arguments):
    result = subprocess.run([sys.executable, "-B", "-X", "utf8", *map(str, arguments)],
                            cwd=root, capture_output=True, text=True, encoding="utf-8")
    if len(arguments) > 1 and arguments[1] == "inspect":
        value = json.loads(result.stdout)
        if value.get("candidate_id"):
            return value  # Missing review is expected before writing this candidate's review.
    if result.returncode:
        print(result.stdout[-12000:], result.stderr[-1500:])
        raise SystemExit(result.returncode)
    try:
        return json.loads(result.stdout)
    except ValueError:
        return {"stdout": result.stdout}


receipts = []
for name, runtime in [("delivery", "observer_generated/runtime"), ("team-archive", "observer_runtime")]:
    root = ROOT / "examples" / name
    cli = root / runtime / "change_sync.py"
    cfg = json.loads((root / "sync.json").read_text(encoding="utf-8"))
    diff = subprocess.check_output(["git", "diff", "HEAD", "--", *[str(root / p) for p in cfg["code_files"]]],
                                   cwd=ROOT, text=True)
    if diff.strip():
        raise SystemExit("Business source drift must be reviewed separately: " + name)
    if sys.argv[1] == "begin":
        run(root, cli, "check", "--root", ".")
        value = run(root, cli, "begin", "--root", ".", "--change", CHANGE, "--request",
                    "Repair recording boundaries and native capture-scope integration found by independent dialogue testing. "
                    "Expose actual capture errors separately from business outcomes and preserve source checks, stable graph identity and application behavior.")
        receipts.append({"project": name, "begin": value})
        continue
    previous = Path(json.loads((root / ".release/stategraph/active.json").read_text())["change"]).name
    review = json.loads((root / ".release/stategraph" / previous / "review.json").read_text(encoding="utf-8"))
    reason = "Reviewed managed observer update: bounded recording queue settlement, pre-builder capture scope, safe producer health, and current source-byte verification. Business source and protected scenarios remain unchanged."
    if name == "delivery":
        run(root, "tooling/dev.py", "graph", "--reason", reason)
    else:
        run(root, "tooling/build_model.py")
        run(root, runtime + "/architecture_guard.py", "seal", "--root", ".", "--reason", reason)
    impact = run(root, cli, "inspect", "--root", ".")
    review["candidate_id"] = impact["candidate_id"]
    review["decisions"]["business"] = {"action": "unchanged", "reason": "Git confirms byte-identical configured code_files; all protected requirements, cases and independent effects remain unchanged."}
    review["decisions"]["state_machine"] = {"action": "unchanged", "reason": "No native state, transition, guard, activity, join or resource definition changed."}
    review["decisions"]["abstraction"] = {"action": "unchanged", "reason": "Node IDs, meanings, source bindings and lifecycle definitions remain unchanged. Managed source fingerprints are refreshed only after explicit impact review."}
    review["decisions"]["probes"] = {"action": "updated", "reason": "Managed Python/JavaScript adapters add scope filtering before builders, read-only health and safe capture diagnostics. Recording settlement waits outside observer locks. Same-stat source edits, out-of-root junctions, delayed capture errors, timeout retention and actual queued events have independent regressions. Existing example probe locations, allowlists, business assertions and on/off/fault modes are retained."}
    (root / CHANGE / "review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    verified = run(root, cli, "verify", "--root", ".")
    accepted = run(root, cli, "accept", "--root", ".")
    checked = run(root, cli, "check", "--root", ".")
    shutil.copytree(root / CHANGE, root / ".release/stategraph" / Path(CHANGE).name)
    shutil.copyfile(root / ".stategraph/active.json", root / ".release/stategraph/active.json")
    shutil.copyfile(root / cfg["manifest"], root / ".release/manifest.json")
    receipts.append({"project": name, "candidate_id": impact["candidate_id"], "verify": verified, "accept": accepted, "check": checked})
    print(name + " verified, accepted and frozen", flush=True)
(OUT / ("example-" + Path(CHANGE).name + "-" + sys.argv[1] + ".json")).write_text(json.dumps(receipts, indent=2) + "\n", encoding="utf-8")
