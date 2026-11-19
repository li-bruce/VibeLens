"""Scoped evidence receipts and explicit reasons for reuse or invalidation.

Freshness is independent of correctness. A current failed/incomplete run stays
failed/incomplete. These fingerprints detect drift, not malicious forgery.
"""

from copy import deepcopy
import re

from ..concepts.common import digest
from .dependencies import dependency_index, closure

SCHEMA = "bo-behavior-evidence/v1"
SUBJECTS = {"design_model", "native_mapping", "native_runtime"}
OUTCOMES = {"pass", "fail", "incomplete", "unsupported", "error", "pending"}
FIELDS = {
    "schema",
    "subject",
    "roots",
    "dependencies",
    "outcome",
    "artifacts",
    "tool_identity",
    "fingerprint",
}
NATIVE = {"$native-source", "$native-model", "$native-tools", "$native-checks"}


def _dependencies(snapshot, subject, roots):
    if not isinstance(subject, str) or subject not in SUBJECTS or not isinstance(roots, list):
        raise ValueError("evidence needs a supported subject and a list of roots")
    if (
        not roots
        or not all(isinstance(root, str) for root in roots)
        or len(roots) != len(set(roots))
    ):
        raise ValueError("evidence needs a supported subject and distinct nonempty roots")
    if subject == "design_model" and any(root.startswith("$native-") for root in roots):
        raise ValueError("design evidence cannot stand for native execution")
    return closure(
        dependency_index(snapshot), set(roots) | (NATIVE if subject != "design_model" else set())
    )


def issue(snapshot, subject, roots, *, outcome, artifacts, tool_identity=None):
    """Record the caller's actual result and its complete current prerequisite set.

    The verifier/analysis runner supplies its executed outcome and artifact hashes.
    This function performs no test and cannot accept an iteration on its own.
    """
    if (
        not isinstance(outcome, str)
        or outcome not in OUTCOMES
        or not isinstance(artifacts, dict)
        or any(
            not isinstance(k, str) or not isinstance(v, str) or not re.fullmatch("[0-9a-f]{64}", v)
            for k, v in artifacts.items()
        )
        or (outcome == "pass" and not artifacts)
        or (tool_identity is not None and not isinstance(tool_identity, dict))
    ):
        raise ValueError("evidence needs an explicit outcome and artifact hashes")
    dependencies = _dependencies(snapshot, subject, roots)
    result = {
        "schema": SCHEMA,
        "subject": subject,
        "roots": sorted(roots),
        "dependencies": dependencies,
        "outcome": outcome,
        "artifacts": deepcopy(artifacts),
        "tool_identity": deepcopy(tool_identity or {}),
    }
    return {**result, "fingerprint": digest(result)}


def applicability(receipt, snapshot, *, tool_identity=None):
    """Recompute dependencies; a receipt cannot omit its changed prerequisites."""
    result = {"current": False, "passed": False, "changed": [], "reason": "invalid_receipt"}
    if not isinstance(receipt, dict) or set(receipt) != FIELDS:
        return result
    if (
        receipt["schema"] != SCHEMA
        or not isinstance(receipt["outcome"], str)
        or receipt["outcome"] not in OUTCOMES
        or not isinstance(receipt["artifacts"], dict)
        or not isinstance(receipt["tool_identity"], dict)
        or (receipt["outcome"] == "pass" and not receipt["artifacts"])
    ):
        return result
    try:
        if receipt["fingerprint"] != digest(
            {k: v for k, v in receipt.items() if k != "fingerprint"}
        ):
            return result
        if any(
            not isinstance(k, str) or not isinstance(v, str) or not re.fullmatch("[0-9a-f]{64}", v)
            for k, v in receipt["artifacts"].items()
        ):
            return result
        current = _dependencies(snapshot, receipt["subject"], receipt["roots"])
    except (ValueError, TypeError, KeyError) as error:
        return {**result, "reason": "definition_unavailable", "detail": str(error)}
    old = receipt["dependencies"]
    if not isinstance(old, dict):
        return result
    changed = sorted(k for k in set(old) | set(current) if old.get(k) != current.get(k))
    if set(old) != set(current):
        return {**result, "reason": "dependency_set_changed", "changed": changed}
    if changed:
        return {**result, "reason": "dependency_changed", "changed": changed}
    if receipt["tool_identity"] != (tool_identity or {}):
        return {**result, "reason": "analysis_tool_changed", "changed": ["tool_identity"]}
    return {
        "current": True,
        "passed": receipt["outcome"] == "pass",
        "outcome": receipt["outcome"],
        "changed": [],
        "reason": "same_dependencies",
        "dependencies": sorted(current),
    }
