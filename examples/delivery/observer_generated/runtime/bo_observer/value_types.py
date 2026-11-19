"""Portable JSON carriers shared by conceptual facts and native capture bindings.

Carrier compatibility does not merge named domains or impose an analysis bound.
The domain validator still checks concrete values, uniqueness and finite limits.
"""

SCALARS = {"string", "number", "integer", "boolean"}


def fact_type_valid(spec, depth=0):
    """Accept explicit recursive carriers; arbitrary objects are not an untyped escape."""
    if depth > 16:
        return False
    if isinstance(spec, str):
        return spec in SCALARS
    if isinstance(spec, list):
        return len(spec) == 1 and fact_type_valid(spec[0], depth + 1)
    return (
        isinstance(spec, dict)
        and bool(spec)
        and all(
            isinstance(key, str) and key.strip() and fact_type_valid(value, depth + 1)
            for key, value in spec.items()
        )
    )


def represents(spec, domain):
    """Compare capture shape without applying finite-analysis limits at runtime."""
    if domain.kind in {"set", "sequence", "map"}:
        if not isinstance(spec, list) or len(spec) != 1:
            return False
        if domain.kind == "map":
            entry = spec[0]
            return (
                isinstance(entry, dict)
                and set(entry) == {"key", "value"}
                and represents(entry["key"], domain.key)
                and represents(entry["value"], domain.element)
            )
        return represents(spec[0], domain.element)
    if not isinstance(spec, str):
        return False
    if domain.kind == "enum":
        kinds = {
            "boolean" if type(v) is bool else "number" if type(v) is int else "string"
            for v in domain.values
            if v is not None
        }
        return spec == "scalar" or kinds <= {spec}
    primitive = {"integer": "number", "identity": "string"}.get(domain.kind, domain.kind)
    return spec in {primitive, "scalar"}
