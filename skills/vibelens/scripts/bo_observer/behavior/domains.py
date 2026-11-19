"""Resolve typed domains without applying analysis limits to an application.

Collections refer to named domains. Maps use key/value entries so typed keys
survive JSON interchange; container order is normalized only where meaningful.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math

from .diagnostics import index_records, require
from .domain_size import SAFE_COUNT, collection_size

SAFE_INTEGER = SAFE_COUNT
COLLECTIONS = {"set", "sequence", "map"}


def value_key(value):
    """A stable JSON identity that keeps booleans distinct from numeric values."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class Domain:
    """An immutable resolved domain; native values are never clamped or coerced."""

    id: str
    kind: str
    values: tuple = ()
    minimum: int | float | None = None
    maximum: int | float | None = None
    bound_origin: str | None = None
    element: Domain | None = None
    key: Domain | None = None
    max_items: int | None = None
    identity_policy: str | None = None

    def accepts(self, value):
        """Validate a representation for a definition, not as a runtime filter."""
        if self.kind == "enum":
            return value_key(value) in {value_key(item) for item in self.values}
        if self.kind == "identity":
            return (
                isinstance(value, str)
                and bool(value)
                and (self.identity_policy != "fixed_pool" or value in self.values)
            )
        if self.kind in COLLECTIONS:
            return self._accepts_collection(value)
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

    def _accepts_collection(self, value):
        if not isinstance(value, list) or (
            self.max_items is not None and len(value) > self.max_items
        ):
            return False
        if self.kind == "map":
            if any(
                not isinstance(entry, dict)
                or set(entry) != {"key", "value"}
                or not self.key.accepts(entry["key"])
                or not self.element.accepts(entry["value"])
                for entry in value
            ):
                return False
            identities = [self.key.value_key(entry["key"]) for entry in value]
            return len(set(identities)) == len(identities)
        if not all(self.element.accepts(item) for item in value):
            return False
        identities = [self.element.value_key(item) for item in value]
        return self.kind == "sequence" or len(set(identities)) == len(identities)

    def value_key(self, value):
        """Preserve sequence order; normalize set order and map entry order."""
        if self.kind in {"set", "sequence"}:
            parts = [self.element.value_key(item) for item in value]
            return value_key(sorted(parts) if self.kind == "set" else parts)
        if self.kind == "map":
            return value_key(
                sorted(
                    (self.key.value_key(item["key"]), self.element.value_key(item["value"]))
                    for item in value
                )
            )
        return value_key(value)

    def finite_capability(self):
        """Classify representation only; this is not a finite-system certificate."""
        if self.kind in COLLECTIONS:
            return collection_size(
                self.kind,
                self.max_items,
                self.element.finite_capability(),
                self.key.finite_capability() if self.key else None,
            )
        if self.kind in {"boolean", "enum"} or (
            self.kind == "identity" and self.identity_policy == "fixed_pool"
        ):
            return {
                "supported": True,
                "cardinality": 2 if self.kind == "boolean" else len(self.values),
            }
        if self.kind == "integer" and self.minimum is not None and self.maximum is not None:
            count = self.maximum - self.minimum + 1
            return {"supported": True, "cardinality": count if count <= SAFE_COUNT else None}
        return {
            "supported": False,
            "reason": (
                "unsupported_numeric_semantics"
                if self.kind == "number"
                else "unbounded_identity_history" if self.kind == "identity" else "unbounded_domain"
            ),
        }


def _validate_fields(record, path):
    """Reject type-specific fields on other kinds, even when structurally well typed."""
    kind = record["type"]
    extras = {
        "enum": {"values"},
        "integer": {"min", "max", "bound_origin"},
        "number": {"min", "max", "bound_origin"},
        "set": {"element_domain", "max_items", "bound_origin"},
        "sequence": {"element_domain", "max_items", "bound_origin"},
        "map": {"element_domain", "key_domain", "max_items", "bound_origin"},
        "identity": {"values", "object_ref", "identity_policy", "max_live", "bound_origin"},
    }.get(kind, set())
    require(
        not set(record) - {"id", "type", "source_refs"} - extras,
        "domain_fields",
        path,
        "Field does not apply to this domain kind",
    )
    bounded = any(field in record for field in ("min", "max", "max_items", "max_live"))
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
    values = record.get("values", [])
    if kind == "enum" or record.get("identity_policy") == "fixed_pool":
        require(bool(values), "empty_domain", path + "/values", "Finite values are required")
        require(
            not any(type(v) is float for v in values),
            "unsupported_enum_number",
            path + "/values",
            "Floating-point enum identity is not portable",
        )
        require(
            len({value_key(v) for v in values}) == len(values),
            "duplicate_value",
            path + "/values",
            "Values must be distinct",
        )
    if kind == "identity":
        require(
            "object_ref" in record and "identity_policy" in record,
            "identity_fields",
            path,
            "Identity needs an object reference and allocation policy",
        )
        require(
            all(isinstance(v, str) and v for v in values),
            "identity_fields",
            path + "/values",
            "Object identities use nonempty strings",
        )
        require(
            record["identity_policy"] == "fixed_pool" or "values" not in record,
            "identity_fields",
            path,
            "Growing identities cannot enumerate a fixed pool",
        )
    for field in ("min", "max"):
        if field in record and kind == "integer":
            require(
                type(record[field]) is int,
                "domain_type",
                path + "/" + field,
                "An integer bound must be an integer",
            )
    minimum, maximum = record.get("min"), record.get("max")
    require(
        minimum is None or maximum is None or minimum <= maximum,
        "empty_domain",
        path,
        "Minimum exceeds maximum",
    )


def load_domains(records):
    """Resolve domains in dependency order; recursive containers fail closed."""
    indexed = index_records(records, "/domains")
    positions = {record["id"]: n for n, record in enumerate(records)}
    domains, visiting = {}, set()

    def resolve(ident, ref_path):
        require(ident in indexed, "unknown_domain", ref_path, ident)
        require(ident not in visiting, "domain_cycle", ref_path, ident)
        if ident in domains:
            return domains[ident]
        require(len(visiting) < 64, "domain_depth", ref_path, "Domain nesting exceeds 64")
        visiting.add(ident)
        record, path = indexed[ident], f"/domains/{positions[ident]}"
        _validate_fields(record, path)
        kind = record["type"]
        dependencies = {}
        names = ("element", "key") if kind == "map" else ("element",) if kind in COLLECTIONS else ()
        for name in names:
            field = name + "_domain"
            require(field in record, "domain_fields", path, "Missing " + field)
            dependencies[name] = resolve(record[field], path + "/" + field)
        domains[ident] = Domain(
            id=ident,
            kind=kind,
            values=tuple(record.get("values", [])),
            minimum=record.get("min"),
            maximum=record.get("max"),
            bound_origin=record.get("bound_origin"),
            max_items=record.get("max_items"),
            identity_policy=record.get("identity_policy"),
            **dependencies,
        )
        visiting.remove(ident)
        return domains[ident]

    for ident in indexed:
        resolve(ident, f"/domains/{positions[ident]}")
    return domains


def compatible(left, right, domains):
    """Scalar primitive kinds compare; named enums/identities/containers stay distinct."""

    def kind(ident):
        return ident[1:] if ident.startswith("$") else domains[ident].kind

    return left == right or (
        kind(left) == kind(right) and kind(left) not in {"enum", "identity", *COLLECTIONS}
    )
