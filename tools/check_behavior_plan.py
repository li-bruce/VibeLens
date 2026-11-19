"""Check the ordered behavior-contract work ledger against its frozen Git baseline.

This is an engineering check, not a product acceptance command. A mapped case is
still pending until its phase has a candidate-bound result. Baseline blobs remain
in Git so fixtures and checks can evolve without overwriting the original evidence.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs/development/behavior-contracts/progress.json"


def baseline_blob(revision, path):
    """Read one tracked baseline file without checking out or changing the tree."""
    return subprocess.run(
        ["git", "show", f"{revision}:{path}"], cwd=ROOT, check=True, capture_output=True
    ).stdout


def check_inventory(plan, read_blob=baseline_blob):
    """Find lost obligations, false completion and a changed baseline reference.

    Receipt files attest only to their stated scope. This check deliberately does
    not turn their existence into evidence that business behavior is correct.
    """
    errors = []
    requirements = plan.get("requirements", [])
    cases = plan.get("cases", [])
    phases = plan.get("phases", [])
    for name, entries, expected in (
        ("requirements", requirements, {f"BC-{i:02}" for i in range(1, 13)}),
        ("cases", cases, {f"A{i:02}" for i in range(1, 35)}),
        ("phases", phases, {f"P{i}" for i in range(8)}),
    ):
        identifiers = [item.get("id") for item in entries]
        if set(identifiers) != expected or len(identifiers) != len(expected):
            errors.append(f"{name}: missing, duplicate or unexpected IDs")
    case_ids = {item.get("id") for item in cases}
    phase_ids = {item.get("id") for item in phases}
    covered = set()
    for requirement in requirements:
        links = set(requirement.get("cases", []))
        if not links or not links <= case_ids:
            errors.append(f"{requirement['id']}: invalid case coverage")
        covered.update(links)
        if not requirement.get("phases") or not set(requirement["phases"]) <= phase_ids:
            errors.append(f"{requirement['id']}: invalid phase coverage")
    if covered != case_ids:
        errors.append("cases: some acceptance obligations have no requirement")
    phase_status = {item["id"]: item.get("status") for item in phases}
    for phase in phases:
        status = phase.get("status")
        if status not in {"pending", "in_progress", "complete"}:
            errors.append(f"{phase['id']}: invalid status")
        if status == "pending":
            continue
        if any(phase_status.get(dep) != "complete" for dep in phase.get("depends_on", [])):
            errors.append(f"{phase['id']}: prerequisite not complete")
        if status == "complete" and not phase.get("evidence"):
            errors.append(f"{phase['id']}: completion needs scoped evidence")
    for case in cases:
        if case.get("status") not in {"pending", "partial", "passed"}:
            errors.append(f"{case['id']}: invalid status")
        if case.get("status") == "passed" and not case.get("evidence"):
            errors.append(f"{case['id']}: no executed acceptance evidence")
    baseline = plan["baseline"]
    for item in baseline["files"]:
        try:
            actual = hashlib.sha256(read_blob(baseline["commit"], item["path"])).hexdigest()
        except (OSError, subprocess.CalledProcessError):
            errors.append(f"baseline: unreadable {item['path']}")
            continue
        if actual != item["sha256"]:
            errors.append(f"baseline: changed reference {item['path']}")
    # Keep the original product entrypoints in the main acceptance runner. New
    # feature tests are additional gates, even while their own ledger is pending.
    original_runner = read_blob(baseline["commit"], "tools/verify.py")
    current_runner = (ROOT / "tools/verify.py").read_bytes()
    missing = test_entrypoints(original_runner) - test_entrypoints(current_runner)
    errors.extend("runner: removed baseline check " + name for name in sorted(missing))
    return errors


def test_entrypoints(source):
    """Extract literal test paths without executing a runner or its subprocesses."""
    return {
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.endswith((".py", ".mjs"))
        and ("test_" in node.value or "check_" in node.value or "verify_" in node.value)
    }


def main():
    """Print an engineering ledger result; never change phase status automatically."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=PLAN)
    args = parser.parse_args()
    errors = check_inventory(json.loads(args.plan.read_text(encoding="utf-8")))
    print(json.dumps({"valid": not errors, "errors": errors, "scope": "development ledger"}))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
