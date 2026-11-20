"""Validate shared review fields before individual semantic guards consume them.

These checks establish shape only. Requirement authority, changed meaning and
retained observations remain the responsibility of their existing domain guards.
"""


def errors(review):
    """Return field diagnostics; never coerce malformed data into an approval."""
    if not isinstance(review, dict):
        return [{"code": "invalid_change_review", "path": "review.json", "expected": "object"}]
    result = []

    def invalid(path, expected):
        result.append({"code": "invalid_change_review", "path": path, "expected": expected})

    for name in ("requirement_changes", "excluded_symbols"):
        values = review.get(name, {})
        if not isinstance(values, dict):
            invalid(name, "object mapping identities to nonempty reasons")
            continue
        for identity, reason in values.items():
            if not isinstance(identity, str) or not identity.strip():
                invalid(name, "nonempty string identities")
            if not isinstance(reason, str) or not reason.strip():
                invalid(f"{name}.{identity}", "nonempty string reason")
    decisions = review.get("decisions", {})
    if not isinstance(decisions, dict):
        invalid("decisions", "object mapping review sections to decisions")
    else:
        for name, decision in decisions.items():
            if not isinstance(decision, dict):
                invalid(f"decisions.{name}", "object with action and reason")
            elif not isinstance(decision.get("reason"), str) or not decision["reason"].strip():
                invalid(f"decisions.{name}.reason", "nonempty string reason")
            elif not isinstance(decision.get("action"), str):
                invalid(f"decisions.{name}.action", "string action")
    return result
