"""Behavior-specific iteration obligations used by the existing coordinator.

Meaning changes need the recorded requirement basis. Source refactors and tool
updates require new evidence without asking a human to certify implementation.
"""

from copy import deepcopy

from ..concepts.common import without_display
from .dependencies import dependency_index, impact

SECTIONS = (
    "domains",
    "variables",
    "actions",
    "properties",
    "assumptions",
    "interactions",
    "refinements",
    "initial_alternatives",
)


def definition_records(contract):
    """Separate semantic record envelopes from citations and revision metadata."""
    if not contract:
        return {}
    result = {
        name: deepcopy(contract[name]) for name in ("schema", "project_id", "scope", "initial")
    }
    for section in SECTIONS:
        for item in contract.get(section, []):
            result[section + "/" + item["id"]] = without_display(item)
    return result


def _analysis_bound_only(key, before, after):
    if not key.startswith("domains/") or not before or not after:
        return False
    if (
        before.get("bound_origin") != "analysis_bound"
        or after.get("bound_origin") != "analysis_bound"
    ):
        return False
    bounds = {"min", "max", "max_items", "max_live"}
    return {k: v for k, v in before.items() if k not in bounds} == {
        k: v for k, v in after.items() if k not in bounds
    }


def meaning_changes(before, after):
    """Return business-definition changes, separately from finite-analysis limits."""
    old, new = definition_records(before.get("behavior")), definition_records(after.get("behavior"))
    # Initial adoption is reviewed by the existing discovery and binding gates.
    if not old:
        return {"meaning": [], "analysis": [], "adoption": bool(new)}
    meaning, analysis = [], []
    for key in sorted(set(old) | set(new)):
        if old.get(key) == new.get(key):
            continue
        if _analysis_bound_only(key, old.get(key), new.get(key)):
            analysis.append(key)
        elif key.startswith("properties/") and key not in old:
            analysis.append(key)  # Adding an independent expectation is allowed.
        else:
            meaning.append(key)
    return {"meaning": meaning, "analysis": analysis, "adoption": False}


def protected_errors(before, after, review):
    """Preserve protected scope and mandatory analysis without a new approval store."""
    errors = []
    if before.get("behavior") is not None and after.get("behavior") is None:
        return [{"code": "behavior_contract_removed"}]
    changes = meaning_changes(before, after)
    allowed = set(before.get("requested_requirements", []))
    reasons = review.get("requirement_changes", {})
    basis = {key for key in allowed if isinstance(reasons.get(key), str) and reasons[key].strip()}
    current_requirements = {r["id"] for r in after.get("intent", {}).get("requirements", [])}
    # Every changed record has its own request basis; one generic reason must not
    # silently cover changes to an unrelated model or property.
    decisions = review.get("behavior_changes", {})
    if not isinstance(decisions, dict):
        return [{"code": "invalid_behavior_change_review"}]

    def reviewed(key):
        refs = decisions.get(key)
        return (
            isinstance(refs, list)
            and bool(refs)
            and all(isinstance(r, str) for r in refs)
            and len(set(refs)) == len(refs)
            and set(refs) <= basis & current_requirements
        )

    missing = [key for key in changes["meaning"] if not reviewed(key)]
    if missing:
        errors.append(
            {
                "code": "behavior_meaning_change_unreviewed",
                "changed": missing,
                "required": "Per-record requirement basis and current scoped discovery confirmation",
            }
        )
    required = set(changes["meaning"])
    current = {p["id"]: p for p in after.get("analysis_profiles", [])}
    for profile in before.get("analysis_profiles", []):
        if profile.get("required_for_acceptance") and (
            profile["id"] not in current or current[profile["id"]] != profile
        ):
            required.add("profile/" + profile["id"])
            if not reviewed("profile/" + profile["id"]):
                errors.append({"code": "required_analysis_changed", "profile": profile["id"]})
    if set(decisions) - required:
        errors.append(
            {"code": "unrelated_behavior_change_review", "keys": sorted(set(decisions) - required)}
        )
    return errors


def recall(before, after, *, limit=20):
    """Keep prompt output compact while retaining full dependencies in the snapshot."""
    if after.get("behavior") is None:
        return {"configured": False, "removed": before.get("behavior") is not None}
    try:
        difference = impact(before, after)
        index = dependency_index(after)
        meaning = meaning_changes(before, after)
    except (ValueError, KeyError, TypeError) as error:
        return {"configured": True, "status": "invalid", "errors": [str(error)]}
    bindings = after.get("model", {}).get("behavior_bindings") or {}
    missing = {
        section: sorted(
            {item["id"] for item in after["behavior"].get(section, [])}
            - set(bindings.get(section, {}))
        )
        for section in ("variables", "actions", "interactions")
    }
    counts = {key: len(difference[key]) for key in ("changed", "affected", "added", "removed")}
    difference = {
        **difference,
        **{key: difference[key][:limit] for key in counts},
        "counts": counts,
        "omitted": {key: max(0, count - limit) for key, count in counts.items()},
    }
    return {
        "configured": True,
        "status": "pending_checks",
        "scope": after["behavior"]["scope"],
        "models": after["behavior"]["scope"]["model_refs"],
        "meaning_changes": meaning,
        "impact": difference,
        "missing_bindings": missing,
        "assumptions": [
            {k: v for k, v in item.items() if k in {"id", "kind", "status", "model_refs"}}
            for item in after["behavior"].get("assumptions", [])
        ],
        "dependency_count": len(index),
        "integration": {"mode": "explicit_workflow", "automatic_host_hook": False},
        "next": "Rebind source facts automatically; resolve only changed meaning through scoped dialogue; run original verify/accept/check gates.",
    }
