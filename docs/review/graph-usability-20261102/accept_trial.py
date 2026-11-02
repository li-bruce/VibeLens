"""Run the existing independent trial's full canonical gate after managed upgrade."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
ROOT = REPO.parent / "VibeLensTrials/otel-provenance-dialogue-20261101-04"
PYTHON = REPO / ".venv/Scripts/python.exe"
os.environ["BO_ADAPTER_HOME"] = str(REPO / "skills/vibelens/scripts/bo_observer/adapters/javascript")
os.environ["TEAM_FILES_DB_URL"] = "sqlite:///runtime/team-files.sqlite3"


def run(name, *args, inspecting=False):
    name += "-" + os.environ.get("BO_ACCEPT_ROUND", "01")
    result = subprocess.run([str(PYTHON), "-B", "-X", "utf8", *args], cwd=ROOT,
                            capture_output=True, text=True, encoding="utf-8")
    (OUT / ("trial-" + name + ".stdout.log")).write_text(result.stdout, encoding="utf-8")
    (OUT / ("trial-" + name + ".stderr.log")).write_text(result.stderr, encoding="utf-8")
    if result.returncode and not inspecting:
        raise RuntimeError(name + " failed; inspect preserved output")
    return json.loads(result.stdout) if result.stdout.strip().startswith("{") else result.stdout


def main():
    cli = "observer_runtime/change_sync.py"
    run("model", "tooling/build_model.py")
    run("scan", "observer_runtime/bo_sync.py", "scan", "--root", ".")
    impact = run("inspect", cli, "inspect", "--root", ".", inspecting=True)
    review = json.loads((ROOT / ".stategraph/instance-frame-identity/review.json").read_text(encoding="utf-8"))
    review["candidate_id"] = impact["candidate_id"]
    reason = "Managed observer/viewer upgrade: file projection, shared layer colors/order, semantic clusters, exact residence tracks, call hierarchy and queue-prefix settlement. Native behavior, state/policy declarations, capture fields and required checks remain unchanged."
    review["decisions"] = {part: {"action": "updated" if part == "probes" else "unchanged", "reason": reason}
                           for part in ("business", "state_machine", "abstraction", "probes")}
    review["requirement_changes"] = {"R_OBSERVE": reason}
    change = ROOT / ".stategraph" / os.environ.get("BO_CHANGE_NAME", "graph-usability-20261102")
    (change / "review.json").write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    receipts = {}
    for command in ("verify", "accept", "check", "recall"):
        receipts[command] = run(command, cli, command, "--root", ".")
        print("Trial " + command + " passed", flush=True)
    before = json.loads((OUT / "trial-preservation-before.json").read_text(encoding="utf-8"))
    modified = [name for name, expected in before["sha256"].items()
                if sha256((ROOT / name).read_bytes()).hexdigest() != expected]
    nodes = sorted(node["id"] for node in json.loads((ROOT / "bo_stategraph/project.json").read_text(encoding="utf-8"))["model"]["nodes"])
    value = {"passed": not modified and nodes == before["node_ids"], "modified_protected": modified,
             "stable_node_ids": nodes == before["node_ids"], "receipts": receipts}
    (OUT / ("trial-acceptance-" + os.environ.get("BO_ACCEPT_ROUND", "01") + ".json")).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    if not value["passed"]:
        raise AssertionError("Protected trial inputs changed")


if __name__ == "__main__":
    main()
