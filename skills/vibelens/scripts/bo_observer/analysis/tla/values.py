"""Encode finite JSON domains without interpolating user text into TLA syntax."""

from itertools import combinations, product
from ...behavior.domains import value_key

MAX_ENUMERATED_VALUES = 8192


class ExportLimit(ValueError):
    """A finite representation exceeds this export budget; it was not checked."""


def literal(value, domain=None):
    """String bytes use an injective ASCII carrier; booleans and integers stay typed."""
    if type(value) is bool:
        return "TRUE" if value else "FALSE"
    if type(value) is int:
        return str(value) if value >= 0 else "(" + str(value) + ")"
    if isinstance(value, str):
        return '"s' + value.encode("utf-8").hex() + '"'
    if value is None:
        return '"n"'
    if isinstance(value, list) and domain and domain.kind in {"sequence", "set"}:
        parts = [literal(item, domain.element) for item in value]
        return (
            ("{" + ", ".join(parts) + "}")
            if domain.kind == "set"
            else ("<<" + ", ".join(parts) + ">>")
        )
    raise ValueError("Unsupported TLA value carrier: " + value_key(value))


def finite_values(domain):
    """Enumerate only bounded parameter domains; reject excessive Cartesian products."""
    capability = domain.finite_capability()
    if not capability["supported"]:
        raise ValueError("Unbounded domain: " + domain.id)
    count = capability.get("cardinality")
    if count is None or count > MAX_ENUMERATED_VALUES:
        raise ExportLimit("Parameter domain exceeds export budget: " + domain.id)
    if domain.kind == "boolean":
        return [False, True]
    if domain.kind in {"enum", "identity"}:
        return list(domain.values)
    if domain.kind == "integer":
        return list(range(domain.minimum, domain.maximum + 1))
    if domain.kind in {"sequence", "set"}:
        values = finite_values(domain.element)
        limit = domain.max_items if domain.max_items is not None else len(values)
        expand = product if domain.kind == "sequence" else combinations
        return [
            list(items)
            for size in range(limit + 1)
            for items in (
                expand(values, repeat=size) if domain.kind == "sequence" else expand(values, size)
            )
        ]
    raise ValueError("Unsupported finite domain: " + domain.kind)


def domain_expression(domain):
    """Finite membership sets initialize values; they never filter Next or properties."""
    if domain.kind == "integer":
        return f"({domain.minimum}..{domain.maximum})"
    if domain.kind in {"boolean", "enum", "identity"}:
        return "{" + ", ".join(literal(value, domain) for value in finite_values(domain)) + "}"
    if domain.kind == "sequence":
        return (
            "UNION {[1..n -> "
            + domain_expression(domain.element)
            + "] : n \\in 0.."
            + str(domain.max_items)
            + "}"
        )
    if domain.kind == "set":
        base = "SUBSET " + domain_expression(domain.element)
        return (
            ("{s \\in " + base + " : Cardinality(s) <= " + str(domain.max_items) + "}")
            if domain.max_items is not None
            else base
        )
    raise ValueError("Unsupported domain expression: " + domain.kind)
