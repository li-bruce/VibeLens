"""Prove the accepted project's delivery gate rejects unsynchronized source edits.

All changes happen in an owned disposable copy. The original conversation,
its acceptance baseline, application data and running services remain untouched.
"""

import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

REPOSITORY = Path(__file__).resolve().parents[1]
TRIAL = REPOSITORY.parent / "VibeLensTrials/lifecycle-dialogue-20261031"


def main():
    phase = sys.argv[1]
    output = REPOSITORY / "docs/review/dialogue-acceptance-20261031/iteration" / phase
    output.mkdir(parents=True, exist_ok=True)
    target = output / "source-only-controls.json"
    if target.exists():
        raise ValueError("Retain old failures; choose a new phase for a rerun")
    active = json.loads((TRIAL / ".stategraph/active.json").read_text(encoding="utf-8"))
    if not (TRIAL / active["change"] / "accepted.json").is_file():
        raise ValueError("The original project is not yet accepted")
    copy = Path(
        tempfile.mkdtemp(
            prefix="dialogue-source-control-", dir=REPOSITORY / ".validation"
        )
    )

    def ignore(directory, names):
        ignored = {
            name
            for name in names
            if name in {"__pycache__", "node_modules", ".git", ".venv"}
        }
        if Path(directory) == TRIAL:
            ignored |= {".agents", "review", "data"}
        if Path(directory) == TRIAL / ".trial":
            ignored.add("skill-backups")
        return ignored

    shutil.copytree(TRIAL, copy, dirs_exist_ok=True, ignore=ignore)
    (copy / "review").mkdir(exist_ok=True)
    for source in (TRIAL / "review").glob("*.json"):
        if source.stat().st_size < 2_000_000:
            shutil.copyfile(source, copy / "review" / source.name)
    (copy / "data").mkdir(exist_ok=True)
    with sqlite3.connect(
        (TRIAL / "data/application.sqlite3").as_uri() + "?mode=ro", uri=True
    ) as source:
        with sqlite3.connect(copy / "data/application.sqlite3") as destination:
            source.backup(destination)

    command = [
        sys.executable,
        "-B",
        "-X",
        "utf8",
        str(REPOSITORY / "skills/vibelens/scripts/change_sync.py"),
        "check",
        "--root",
        str(copy),
    ]
    results = []

    def check(name, should_pass):
        response = subprocess.run(
            command,
            cwd=copy,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
        (output / f"source-{name}.stdout.log").write_text(
            response.stdout, encoding="utf-8"
        )
        (output / f"source-{name}.stderr.log").write_text(
            response.stderr, encoding="utf-8"
        )
        row = {
            "name": name,
            "expected": "accept" if should_pass else "reject",
            "exit_code": response.returncode,
            "passed": (response.returncode == 0) == should_pass,
        }
        results.append(row)
        print(json.dumps(row), flush=True)
        if not row["passed"]:
            raise AssertionError(name)

    summary = {"phase": phase, "copy": str(copy), "command": command, "checks": results}
    try:
        check("accepted-copy", True)
        source = copy / "app/service.py"
        original = source.read_bytes()
        source.write_bytes(
            original
            + b"\n# Independent source-only drift; intentionally omit graph maintenance.\n"
        )
        try:
            check("edited-service", False)
        finally:
            source.write_bytes(original)
        addition = copy / "app/unmapped_feature.py"
        addition.write_text(
            'def untracked_feature(value):\n    """A new unmapped application entrypoint."""\n    return value\n',
            encoding="utf-8",
        )
        try:
            check("new-feature", False)
        finally:
            addition.unlink()
        check("restored-source", True)
        summary["passed"] = True
    except Exception as error:
        summary.update(passed=False, error=repr(error))
    target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if summary["passed"] else 1)


if __name__ == "__main__":
    main()
