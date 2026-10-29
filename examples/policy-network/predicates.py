"""Native application predicates shared by the example's permissions."""


def same_identity(left: str, right: str) -> bool:
    """Compare the two current identities supplied by the application's reader."""
    return left == right


def flag_enabled(value: bool) -> bool:
    """Expose an application-owned Boolean fact without inventing missing data."""
    return value
