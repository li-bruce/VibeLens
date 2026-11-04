"""Replay the retained synthetic trial in a fresh directory using the selected Skill."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def main():
    """Verify source bytes before reproducing the actual complete project gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    skill, root = args.skill.resolve(), args.out.resolve()
    summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
    for name, expected in summary["source_hashes"].items():
        actual = hashlib.sha256((HERE / "project" / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("Retained source changed; review it independently: " + name)
    shutil.copytree(HERE / "project", root)
    log = root / "review" / "replay"
    log.mkdir(parents=True)
    environment = {
        **os.environ,
        "VIBELENS_SKILL": str(skill),
        "BO_TRIAL_DATABASE_URL": "sqlite:///var/files.sqlite3",
    }

    def run(name, arguments):
        result = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", *map(str, arguments)],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=240,
        )
        (log / (name + ".stdout")).write_text(result.stdout, encoding="utf-8")
        (log / (name + ".stderr")).write_text(result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"{name} failed; inspect {log / (name + '.stdout')}")
        return json.loads(result.stdout)

    run("build", [root / "bo_build.py", skill])
    sync = skill / "scripts" / "change_sync.py"
    run(
        "begin",
        [
            sync,
            "begin",
            "--root",
            root,
            "--change",
            "review/acceptance",
            "--request",
            "Replay the retained synthetic C2 trial without changing its meaning",
            "--requirements",
            "R1",
        ],
    )
    run("scan", [skill / "scripts" / "bo_sync.py", "scan", "--root", root])
    # Inspect may be nonzero solely because the review has not yet been written.
    inspected = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", str(sync), "inspect", "--root", str(root)],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    (log / "inspect.stdout").write_text(inspected.stdout, encoding="utf-8")
    candidate = json.loads(inspected.stdout)
    if candidate["errors"]:
        raise ValueError(candidate["errors"])
    review = {
        "candidate_id": candidate["candidate_id"],
        "decisions": {
            part: {
                "action": "unchanged",
                "reason": "Replayed byte-verified authored source and retained synthetic C2 confirmation",
            }
            for part in ("business", "state_machine", "abstraction", "probes")
        },
        "excluded_symbols": {},
        "requirement_changes": {},
    }
    (root / "review/acceptance/review.json").write_text(
        json.dumps(review, indent=2), encoding="utf-8"
    )
    for action in ("verify", "accept", "check"):
        result = run(action, [sync, action, "--root", root])
        print(
            json.dumps(
                {
                    "stage": action,
                    "valid": result["valid"],
                    "reports": {
                        key: value["status"] for key, value in result.get("reports", {}).items()
                    },
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
