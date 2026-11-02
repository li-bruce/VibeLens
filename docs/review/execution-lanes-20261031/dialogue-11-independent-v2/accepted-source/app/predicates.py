"""Native policy and transition predicates."""
def same_identity(left: str, right: str) -> bool:
    return bool(left) and left == right

def operation_allowed(context: dict, payload: dict) -> bool:
    return payload["allowed"] is True
