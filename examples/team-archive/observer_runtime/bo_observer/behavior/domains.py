"""Typed value domains and finite-analysis capability, with no application limits.

An analysis bound is metadata for later analysis, not permission to clamp native
values. JSON type equality keeps booleans, integers and strings distinct.
"""

from dataclasses import dataclass
import json
import math

from .diagnostics import require

SAFE_INTEGER = 9007199254740991


def value_key(value):
    """A stable JSON identity that keeps booleans distinct from numeric values."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class Domain:
    """Normalized scalar domain; bound origin is retained for every consumer."""

    id: str
    kind: str
    values: tuple
    minimum: int | float | None
    maximum: int | float | None
    bound_origin: str | None

    def accepts(self, value):
        """Check actual values without coercing, trimming or substituting defaults."""
        if self.kind == "enum":
            return value_key(value) in {value_key(item) for item in self.values}
        if self.kind == "boolean":
            return type(value) is bool
        if self.kind == "string":
            return isinstance(value, str)
        if self.kind == "integer":
            if type(value) is not int or abs(value) > SAFE_INTEGER:
                return False
        elif self.kind == "number":
            if type(value) not in (int, float) or not math.isfinite(value):
                return False
        else:
            return False
        return (self.minimum is None or value >= self.minimum) and (
            self.maximum is None or value <= self.maximum
        )

    def finite_capability(self):
        """Classify representation only; this is not a finite-system certificate."""
        if self.kind in {"boolean", "enum"}:
            return {
                "supported": True,
                "cardinality": 2 if self.kind == "boolean" else len(self.values),
            }
        if self.kind == "integer" and self.minimum is not None and self.maximum is not None:
            return {"supported": True, "cardinality": self.maximum - self.minimum + 1}
        return {
            "supported": False,
            "reason": (
                "unsupported_numeric_semantics" if self.kind == "number" else "unbounded_domain"
            ),
        }


def load_domains(records):
    """Validate per-kind fields and bounds after the strict JSON envelope check."""
    domains = {}
    for position, record in enumerate(records):
        path = f"/domains/{position}"
        ident, kind = record["id"], record["type"]
        require(ident not in domains, "duplicate_id", path + "/id", ident)
        values = record.get("values", [])
        require(
            kind == "enum" or "values" not in record,
            "domain_fields",
            path,
            "Only enums enumerate values",
        )
        if kind == "enum":
            require(bool(values), "empty_domain", path + "/values", "An enum needs values")
            require(
                not any(type(value) is float for value in values),
                "unsupported_enum_number",
                path + "/values",
                "Floating-point enum identities are not portable across JSON producers",
            )
            require(
                len({value_key(v) for v in values}) == len(values),
                "duplicate_value",
                path + "/values",
                "Enum values must be distinct",
            )
        bounded = "min" in record or "max" in record
        require(
            not bounded or kind in {"integer", "number"},
            "domain_fields",
            path,
            "Bounds require a numeric domain",
        )
        require(
            not bounded or "bound_origin" in record,
            "bound_origin_required",
            path,
            "Identify application_limit, analysis_bound or abstraction",
        )
        require(
            "bound_origin" not in record or bounded,
            "domain_fields",
            path,
            "Bound origin needs an actual bound",
        )
        minimum, maximum = record.get("min"), record.get("max")
        for field in ("min", "max"):
            if field in record and kind == "integer":
                require(
                    type(record[field]) is int,
                    "domain_type",
                    path + "/" + field,
                    "An integer bound must be an integer",
                )
        require(
            minimum is None or maximum is None or minimum <= maximum,
            "empty_domain",
            path,
            "Minimum exceeds maximum",
        )
        domains[ident] = Domain(
            ident, kind, tuple(values), minimum, maximum, record.get("bound_origin")
        )
    return domains


def compatible(left, right, domains):
    """Primitive kinds can be compared; enums retain their named domain identity."""

    def kind(ident):
        return ident[1:] if ident.startswith("$") else domains[ident].kind

    return left == right or (kind(left) == kind(right) and kind(left) != "enum")
