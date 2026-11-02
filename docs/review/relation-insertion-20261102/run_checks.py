"""Keep reproducible outputs for relation insertion and the unchanged release gate."""

from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CHANGE = "relation-insertion-20261102"
REASON = (
    "Construction-time relation registration: strict portable rules, exact duplicate "
    "identity, typed conceptual proof paths and automatic witness restoration. "
    "Preserve native business/state definitions, capture requirements and all existing gates."
)
os.environ["BO_ADAPTER_HOME"] = str(
    ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript"
)
os.environ["BO_EXAMPLE_CHANGE"] = ".stategraph/" + CHANGE
os.environ["BO_EXAMPLE_REASON"] = REASON
os.environ["BO_CHANGE_NAME"] = CHANGE
os.environ["BO_UPGRADE_ROUND"] = "relations-01"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = OUT
    return module


def run(name, *args):
    started = datetime.now(timezone.utc).isoformat()
    with (
        (OUT / (name + ".stdout.log")).open("w", encoding="utf-8") as stdout,
        (OUT / (name + ".stderr.log")).open("w", encoding="utf-8") as stderr,
    ):
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", *args],
            cwd=ROOT,
            stdout=stdout,
            stderr=stderr,
        )
    receipt = {
        "valid": result.returncode == 0,
        "command": list(args),
        "exit_code": result.returncode,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    }
    (OUT / (name + ".json")).write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt), flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)


def main():
    action = sys.argv[1]
    if action in {"begin", "accept"}:
        module = load(
            "relation_examples", "docs/review/execution-lanes-20261031/review_examples.py"
        )
        sys.argv = [str(__file__)] + (["begin"] if action == "begin" else [])
        module.main()
    elif action == "upgrade":
        module = load("relation_upgrades", "docs/review/graph-usability-20261102/upgrade_copies.py")
        sys.argv = [str(__file__)]
        module.main()
    elif action == "focused":
        run("unit", "tests/test_relation_insertion.py")
        run("integration", "tests/test_relation_integration.py")
        run("exercise", str(OUT / "exercise.py"))
    elif action == "quality":
        run(
            "source-quality",
            "tools/check_source.py",
            "--format",
            "--out",
            str(OUT / "source-quality-report.json"),
        )
        run("document-links", "tests/test_document_links.py")
    elif action == "gate":
        run("full-gate", "tools/verify.py", "--database")
    elif action == "audit":
        before = json.loads((OUT / "baseline.json").read_text(encoding="utf-8"))
        after = {
            name: sha256((ROOT / name).read_bytes()).hexdigest() for name in before["protected"]
        }
        valid = before["protected"] == after
        result = {"valid": valid, "unchanged_core_modules": len(after), "sha256": after}
        (OUT / "core-preservation.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result))
        if not valid:
            raise SystemExit(1)
    else:
        raise ValueError("Unknown review action")


if __name__ == "__main__":
    main()
