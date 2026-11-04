"""Bind conceptual facts and expected outcomes to independent observation fields.

These checks establish which actual observations must be tested. The existing
verification runner executes those tests and evaluates their observed values.
"""

from .common import encoded


def check_operation(ident, references, nodes, error, *, effect=False):
    """A business operation or effect needs a real source-backed implementation."""
    if not references or any(reference not in nodes for reference in references):
        error("unbound_logical_effect" if effect else "unbound_business_concept", ident)
        return
    for reference in references:
        node = nodes[reference]
        source = node.get("source")
        if (
            node.get("kind") not in {"action", "effect", "function", "decision", "operation"}
            or not isinstance(source, dict)
            or set(source) != {"path", "symbol"}
            or not all(isinstance(value, str) and value.strip() for value in source.values())
        ):
            error("business_binding_lacks_native_operation", ident + ":" + reference)


def has_assertion(checks, case, path, expected):
    """Retain JSON type distinctions such as false versus zero in test contracts."""
    return any(
        check.get("case") == case
        and encoded(check.get("path")) == encoded(path)
        and "equals" in check
        and encoded(check["equals"]) == encoded(expected)
        for check in checks
    )


def check_fact(ident, value, references, nodes, checks, error):
    """Bind a fact to both its typed capture and its precise read-basis assertion."""
    if not references:
        error("unbound_fact", ident)
        return
    for reference in references:
        node, direction, field = (reference[name] for name in ("node", "direction", "field"))
        specification = nodes.get(node, {}).get("capture", {}).get(direction, {}).get(field)
        if specification != value["type"]:
            error("fact_capture_type_differs", ident)
        # A field's type does not establish when or for whom it was read. The
        # assertion names this exact capture; sync_verify checks its real value.
        expected = {
            "node": node,
            "direction": direction,
            "field": field,
            "read_basis": value["read_basis"],
        }
        for witness in reference["basis_checks"]:
            if not has_assertion(checks, witness["case"], witness["path"], expected):
                error("fact_read_basis_assertion_differs", ident)


def check_expectation(ident, value, references, acceptance, error):
    """Require independent outcomes, not merely existing test names."""
    if not references:
        error("unbound_independent_expectation", ident)
        return
    if not isinstance(acceptance, dict) or not isinstance(acceptance.get("checks"), list):
        error("missing_independent_acceptance", ident)
        return
    for case in references:
        for assertion in value["then"]:
            if not has_assertion(
                acceptance["checks"], case, assertion["path"], assertion["equals"]
            ):
                error("independent_expected_assertion_differs", ident + ":" + case)


def check_record_bindings(active, nodes, binding, acceptance, error, business_ids):
    """Apply only the obligations selected by the confirmed semantic scope."""
    checks = acceptance.get("checks", []) if isinstance(acceptance, dict) else []
    for ident, value in active.items():
        kind = value["kind"]
        if ident in business_ids and kind not in {"action", "effect"}:
            references = binding.get("business", {}).get(ident)
            allowed = {
                "condition": {"condition", "decision"},
                "state": {"state"},
                "resource": {"resource"},
                "event": {"event", "action", "effect", "function"},
                "data": {"data", "parameter", "function"},
            }
            if not references or any(reference not in nodes for reference in references):
                error("unbound_business_concept", ident)
            elif any(nodes[reference].get("kind") not in allowed[kind] for reference in references):
                error("business_structure_binding_kind_differs", ident)
        elif ident in business_ids or kind == "logical_effect":
            effect = kind == "logical_effect"
            references = binding.get("effects" if effect else "business", {}).get(ident)
            check_operation(ident, references, nodes, error, effect=effect)
        elif kind == "fact":
            check_fact(
                ident, value, binding.get("facts", {}).get(value["id"]), nodes, checks, error
            )
        elif kind == "expectation":
            check_expectation(
                ident, value, binding.get("expectations", {}).get(value["id"]), acceptance, error
            )
