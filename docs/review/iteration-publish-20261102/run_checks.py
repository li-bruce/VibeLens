"""Retain the test snapshot's actual command outputs and exit statuses."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
os.environ["BO_ADAPTER_HOME"] = str(
    ROOT / "skills/vibelens/scripts/bo_observer/adapters/javascript"
)


def run(name, *args):
    started = datetime.now(timezone.utc).isoformat()
    with (
        (OUT / (name + ".stdout.log")).open("w", encoding="utf-8") as stdout,
        (OUT / (name + ".stderr.log")).open("w", encoding="utf-8") as stderr,
    ):
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", *args], cwd=ROOT, stdout=stdout, stderr=stderr
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


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "focused":
        run("iteration-dialogue", "tests/test_iteration_dialogue.py")
        run("requirements-dialogue", "tests/test_requirements_dialogue.py")
        run("document-links", "tests/test_document_links.py")
    elif action == "quality":
        run(
            "source-quality",
            "tools/check_source.py",
            "--format",
            "--out",
            str(OUT / "source-quality-report.json"),
        )
    elif action == "gate":
        run("full-gate", "tools/verify.py", "--database")
    elif action == "export":
        run(
            "clean-export",
            "tools/check_release_export.py",
            "--staged",
            "--out",
            str(OUT / "clean-export-report.json"),
        )
    else:
        raise ValueError("Unknown review action")
