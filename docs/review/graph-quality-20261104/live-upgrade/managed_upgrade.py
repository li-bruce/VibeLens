"""Upgrade only verified managed observer/viewer files in the old live trial."""

import hashlib
import json
from pathlib import Path
import sys

REPOSITORY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY / "skills/vibelens/scripts"))
from bo_upgrade import plan, apply

TRIAL = REPOSITORY.parent / "VibeLensTrials/otel-provenance-dialogue-20261101-04"
EVIDENCE = Path(__file__).parent
OPTIONS = {"runtime": "observer_runtime", "viewers": ["static/graph"]}


def write(name, value):
    (EVIDENCE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def protected():
    """Hash project source, definitions, preferences, evidence and business data."""
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
        if name.startswith("runtime/") and relative.name not in {"session.key", "team-files.sqlite3"}:
            continue
        raw = path.read_bytes()
        result[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return result


proposed = plan(TRIAL, **OPTIONS)
summary = {key: proposed[key] for key in ("valid", "release", "protocols", "changes", "conflicts", "retired_files")}
write("plan.json", summary)
if not proposed["valid"] or proposed["retired_files"]:
    raise SystemExit("Conflicted or retiring upgrade needs separate review")
if any(not path.startswith(("observer_runtime/", "static/graph/")) for path in proposed["changes"]):
    raise SystemExit("Upgrade would change native state/execution core")
before = protected()
write("protected-before.json", before)
result = apply(TRIAL, **OPTIONS)
write("applied.json", result)
after = protected()
write("protected-after.json", after)
changed = sorted(path for path in before if before[path] != after.get(path))
added = sorted(set(after) - set(before))
verification = {"valid": not changed and not added, "protected_files": len(before), "changed": changed, "added": added, "managed_changes": len(result["changes"]), "native_core_unchanged": all(name in after and before[name] == after[name] for name in ("bo_stategraph/__init__.py", "bo_stategraph/bo_contracts.py", "bo_stategraph/execution_contract.py", "bo_stategraph/bo_runtime.py"))}
write("protected-verification.json", verification)
print(json.dumps(verification))
raise SystemExit(int(not verification["valid"]))
