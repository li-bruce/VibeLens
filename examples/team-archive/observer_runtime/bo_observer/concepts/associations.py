"""Bind relationships between confirmed models, not just their individual nodes.

Native declarations remain the application's execution authority. These checks
make the observer reject a correct rule attached to the wrong operation and an
effect whose source exists but has no transition or completion evidence.
"""

from .assertions import has_assertion
from .common import canonical_id, encoded


def check_applicability(doc, model, binding, active, error):
    """Compare each selected rule's complete set of implemented business targets.

    An increment need not implement unrelated future actions. Once an action is
    bound, however, every rule that applies to it must retain that exact target.
    Undeclared extra targets are rejected as well as missing targets.
    """
    expected = {}
    for item in doc["applicability"]:
        targets = binding["business"].get(item["operation"], [])
        for operation in item["rules"].get("operations", []):
            expected.setdefault(operation, set()).update(targets)
    actual = {item["id"]: item for item in (model.get("policy") or {}).get("operations", [])}
    for record in active.values():
        if record["kind"] != "rule_operation":
            continue
        operation = record["id"]
        targets = set(actual.get(operation, {}).get("business_nodes", []))
        if targets != expected.get(operation, set()):
            error("rule_applicability_binding_differs", operation)


def _completion_contract(transition, effect, witness, data, binding, nodes, acceptance, error):
    """Require a typed observation and an independently confirmed expected value."""
    completion = witness["completion"]
    node = nodes.get(completion["node"], {})
    capture = node.get("capture", {}).get("out", {})
    if completion["node"] not in binding.get("effects", {}).get(effect, []):
        error("effect_completion_node_differs", effect)
    if completion["boundary"] != data["records"][effect]["completion"]:
        error("effect_completion_boundary_differs", effect)
    # Capture specifications use the probe's portable JSON shape rather than
    # state-context specifications. Reuse the existing protocol validator.
    from ..observation.semantic_probe import selected

    field = completion["field"]
    if field not in capture:
        error("effect_completion_capture_missing", effect)
    else:
        try:
            value = {field: completion["equals"]}
            if encoded(selected(value, {field: capture[field]})) != encoded(value):
                error("effect_completion_capture_type_differs", effect)
        except (TypeError, ValueError) as exc:
            error("effect_completion_capture_type_differs", str(exc))
    identity = completion.get("identity_field")
    if identity is not None and capture.get(identity) != "string":
        error("effect_completion_identity_capture_differs", effect)
    if node.get("data_role") == "transaction" and not (
        identity == "transaction_id"
        and field == "committed"
        and completion["equals"] is True
        and completion["phase"] in {"return", "commit"}
    ):
        error("transaction_completion_requires_commit_identity", effect)
    expectation = data["records"].get(canonical_id("expectation", completion["expectation"]), {})
    if (
        expectation.get("kind") != "expectation"
        or not {transition, effect}.intersection(expectation.get("scope", []))
        or not any(
            encoded(item["path"]) == encoded(completion["path"])
            and encoded(item["equals"]) == encoded(completion["equals"])
            for item in expectation.get("then", [])
        )
    ):
        error("effect_completion_expectation_differs", effect)
    cases = binding.get("expectations", {}).get(completion["expectation"], [])
    checks = acceptance.get("checks", []) if isinstance(acceptance, dict) else []
    if not cases or any(
        not has_assertion(checks, case, completion["path"], completion["equals"]) for case in cases
    ):
        error("effect_completion_acceptance_missing", effect)


def check_transition_effects(model, binding, data, active, anchors, acceptance, error):
    """Derive mandatory associations from transitions even without crosslinks.

    A display crosslink is optional. The state declaration itself creates the
    binding obligation, so omitting a crosslink cannot discard a real effect.
    """
    nodes = {node["id"]: node for node in model.get("nodes", [])}
    edges = {edge["id"]: edge for edge in model.get("edges", [])}
    declared = binding.get("transition_effects", {})
    for transition, record in active.items():
        if record["kind"] != "transition":
            continue
        effects = {
            key
            for key in data["dependencies"][transition]
            if data["records"][key]["kind"] == "logical_effect"
        }
        witnesses = declared.get(transition, [])
        found = [item["effect"] for item in witnesses]
        if set(found) != effects or len(found) != len(set(found)):
            error("transition_effect_bindings_differ", transition)
        for witness in witnesses:
            effect = witness["effect"]
            if effect not in effects:
                continue
            starts = set(anchors.get(transition, []))
            targets = set(binding.get("effects", {}).get(effect, []))
            represented = starts.intersection(targets)
            for reference in witness["edges"]:
                edge = edges.get(reference, {})
                if (
                    edge.get("from") not in starts
                    or edge.get("to") not in targets
                    or edge.get("type") not in {"flow", "event", "data"}
                ):
                    error(
                        "transition_effect_native_edge_differs",
                        transition + ":" + reference,
                    )
                else:
                    represented.add(edge["to"])
            if not starts or not targets or represented != targets:
                error(
                    "transition_effect_native_association_missing",
                    transition + ":" + effect,
                )
            _completion_contract(
                transition, effect, witness, data, binding, nodes, acceptance, error
            )
    # Unknown bindings cannot be used to attach observations to made-up effects.
    for transition in declared:
        if data["records"].get(transition, {}).get("kind") != "transition":
            error("undeclared_transition_effect_binding", transition)
