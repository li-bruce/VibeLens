"""Apply the frozen HTTP observation correction through managed upgrade only."""

import hashlib
import json
from pathlib import Path
import sys

REPOSITORY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY / "skills/vibelens/scripts"))
from bo_upgrade import apply, plan

TRIAL = REPOSITORY.parent / "VibeLensTrials/otel-provenance-dialogue-20261101-04"
EVIDENCE = Path(__file__).parent
OPTIONS = {"runtime": "observer_runtime", "viewers": ["static/graph"]}
PHASE = "api-observation"


def write(name, value):
    (EVIDENCE / f"{name}-{PHASE}.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def protected():
    """Hash project-owned source, definitions, data, preferences and old evidence."""
    skipped = {"__pycache__", "node_modules", ".venv", ".npm-cache"}
    result = {}
    for path in TRIAL.rglob("*"):
        relative = path.relative_to(TRIAL)
        name = relative.as_posix()
        if not path.is_file() or set(relative.parts) & skipped:
            continue
        if name.startswith(("observer_runtime/", "static/graph/", ".stategraph/upgrades/")):
            continue
        if name == "bo_stategraph/runtime-version.json":
            continue
        if name.startswith("runtime/") and relative.name not in {
            "session.key",
            "team-files.sqlite3",
        }:
            continue
        raw = path.read_bytes()
        result[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return result


def main():
    proposed = plan(TRIAL, **OPTIONS)
    write(
        "plan",
        {
            key: proposed[key]
            for key in ("valid", "release", "protocols", "changes", "conflicts", "retired_files")
        },
    )
    if not proposed["valid"] or proposed["retired_files"]:
        raise SystemExit("Conflicted or retiring upgrade needs separate review")
    if any(
        not path.startswith(("observer_runtime/", "static/graph/")) for path in proposed["changes"]
    ):
        raise SystemExit("Upgrade would change native state/execution core")
    before = protected()
    write("protected-before", before)
    launcher_before = (TRIAL / "runtime/launcher.json").read_bytes()
    result = apply(TRIAL, **OPTIONS)
    write("applied", result)
    after = protected()
    write("protected-after", after)
    changed = sorted(path for path in before if before[path] != after.get(path))
    added = sorted(set(after) - set(before))
    receipt = {
        "valid": not changed and not added,
        "protected_files": len(before),
        "changed": changed,
        "added": added,
        "managed_changes": len(result["changes"]),
        "launcher_unchanged_during_copy": launcher_before
        == (TRIAL / "runtime/launcher.json").read_bytes(),
        "native_core_unchanged": all(
            before[name] == after.get(name)
            for name in (
                "bo_stategraph/__init__.py",
                "bo_stategraph/bo_contracts.py",
                "bo_stategraph/execution_contract.py",
                "bo_stategraph/bo_runtime.py",
            )
        ),
    }
    write("protected-verification", receipt)
    print(json.dumps(receipt))
    return int(not receipt["valid"])


if __name__ == "__main__":
    raise SystemExit(main())
