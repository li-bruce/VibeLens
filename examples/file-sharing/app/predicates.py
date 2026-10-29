"""Pure, explicitly bound permission predicates."""


def same_identity(left: str, right: str) -> bool:
    return bool(left) and left == right


def flag_enabled(value: bool) -> bool:
    return value is True


def operation_allowed(context: dict, payload: dict) -> bool:
    return payload["allowed"] is True


def has_recipients(context: dict, payload: dict) -> bool:
    return context["grant_count"] > 0
