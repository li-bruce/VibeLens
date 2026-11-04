"""Compare a confirmed design with native declarations, never execute business work."""

from copy import deepcopy

try:
    from ...bo_contracts import validate_runtime_definition
    from ...execution_contract import validate_execution_graph
except ImportError:
    from bo_contracts import validate_runtime_definition
    from execution_contract import validate_execution_graph
from ..policy.definition import validate as validate_policy
from .common import canonical_id, without_display
from .common import encoded
from .model import build, policy_semantics
from ..protocol import schema_check
from .semantics import snapshot_records, check_confirmations
from .anchors import native_anchors, check_links
from .assertions import check_record_bindings
from .activities import activity_semantics


def machine_semantics(value):
    """Normalize supported engine syntax without erasing priority or conditions."""
    result = {key: deepcopy(value.get(key, {})) for key in ["states", "initial", "context"]}
    # Event names and payload keys are domain identifiers, even when they are
    # spelled "label" or "summary". Only each event's envelope has metadata.
    result["events"] = {
        name: without_display(event) for name, event in value.get("events", {}).items()
    }
    result["guards"] = sorted(value.get("guards", {}))
    result["transitions"] = []
    for original in value["transitions"]:
        item = {key: deepcopy(original[key]) for key in ["source", "dest", "trigger"]}
        item["source"] = item["source"] if isinstance(item["source"], list) else [item["source"]]
        for name in ["conditions", "unless"]:
            ref = original.get(name, [])
            item[name] = ref if isinstance(ref, list) else [ref]
        result["transitions"].append(item)
    if "execution" in value:
        result["execution"] = activity_semantics(value["execution"])
    return result


def scoped_policy_semantics(policy, operation_ids):
    """Compare the expressions needed by this increment, including shared inputs.

    Operation IDs are selected from confirmed conceptual records. Dependency
    traversal is deterministic and preserves operator argument order; unrelated
    future operations need not be implemented just to bind the current feature.
    """
    canonical = policy_semantics(policy)
    nodes = {item["id"]: item for item in canonical["nodes"]}
    operations = [item for item in canonical["operations"] if item["id"] in operation_ids]
    selected = set()
    pending = [item["root"] for item in operations]
    while pending:
        ident = pending.pop()
        if ident in selected:
            continue
        selected.add(ident)
        item = nodes[ident]
        pending.extend(item.get("arguments", {}).values())
        pending.extend(item.get("inputs", []))
    expressions = [item for item in canonical["nodes"] if item["id"] in selected]
    predicates = {item["predicate"] for item in expressions if item["op"] == "predicate"}
    inputs = {item["name"] for item in expressions if item["op"] == "input"}
    return {
        "operations": operations,
        "nodes": expressions,
        "predicates": [item for item in canonical["predicates"] if item["id"] in predicates],
        "inputs": {key: value for key, value in canonical["inputs"].items() if key in inputs},
    }


def check_binding(doc, model, bindings=None, *, scope=None, acceptance=None):
    """Require exact primary state semantics, policy meaning and concrete anchors.

    This is an additional gate; source scanners, actual case IDs and runtime
    witnesses remain the responsibility of the existing independent checks.
    """
    errors = []

    def error(code, item):
        errors.append({"code": code, "item": str(item)})

    data = build(doc)
    confirmation = check_confirmations(doc, scope=scope)
    if not confirmation["ready"]:
        error("concepts_not_confirmed", ",".join(confirmation["blocked"]))
        errors.extend(confirmation["errors"])
    expected = snapshot_records(
        {key: data["records"][key] for key in confirmation["coverage_scope"]}
    )
    binding = bindings if bindings is not None else model.get("concepts")
    if not isinstance(binding, dict) or binding.get("schema") != "bo-concept-bindings/v1":
        return {
            "valid": False,
            "errors": errors + [{"code": "missing_concept_bindings", "item": "model.concepts"}],
        }
    try:
        schema_check(binding, "concept-bindings")
    except ValueError as exc:
        return {
            "valid": False,
            "errors": errors + [{"code": "invalid_concept_bindings", "item": str(exc)}],
        }
    if binding.get("semantic_revision") != expected["semantic_revision"]:
        error("stale_concept_binding", "semantic_revision")
    active = expected["records"]
    models = {
        item["id"]: item
        for item in doc["state_models"]
        if canonical_id("state-model", item["id"]) in active
    }
    primary = binding.get("primary_state_model")
    if len(models) > 1:
        error("unsupported_multiple_bound_state_models", ",".join(sorted(models)))
    if models:
        if primary not in models:
            error("missing_primary_state_model", primary)
        else:
            designed = models[primary]
            try:
                validate_runtime_definition(model.get("machine"))
                designed_semantics = machine_semantics(designed)
                if "execution" in designed_semantics:
                    owner = designed_semantics["execution"]["parent"]
                    targets = binding.get("business", {}).get(owner, [])
                    if len(targets) != 1:
                        error("ambiguous_activity_owner_binding", owner)
                    else:
                        designed_semantics["execution"]["parent"] = targets[0]
                    validate_execution_graph(model)
                if encoded(designed_semantics) != encoded(machine_semantics(model["machine"])):
                    error("state_semantics_changed_during_binding", primary)
            except (KeyError, TypeError, ValueError) as exc:
                error("invalid_native_machine", exc)
            expected_owner = designed["subject"]
            if binding.get("objects", {}).get(primary) != expected_owner:
                error("state_object_identity_binding_differs", primary)
    elif primary is not None:
        error("unexpected_bound_state_model", primary)
    if doc.get("policy"):
        try:
            required_operations = {
                value["id"] for value in active.values() if value["kind"] == "rule_operation"
            }
            if not required_operations and not model.get("policy"):
                bound_operations = set()
            else:
                validated_policy = validate_policy(model.get("policy"))
                bound_operations = set(validated_policy["operations"])
            declared_operations = {item["id"] for item in doc["policy"]["operations"]}
            if bound_operations - declared_operations:
                error(
                    "undeclared_bound_rule_operations",
                    ",".join(sorted(bound_operations - declared_operations)),
                )
            if required_operations and encoded(
                scoped_policy_semantics(doc["policy"], required_operations)
            ) != encoded(scoped_policy_semantics(model["policy"], required_operations)):
                error("rule_semantics_changed_during_binding", "policy")
        except (ValueError, KeyError, TypeError) as exc:
            error("invalid_bound_policy", exc)
    elif model.get("policy"):
        error("undeclared_bound_policy", "policy")
    nodes = {node["id"]: node for node in model.get("nodes", [])}
    business_ids = {node["id"] for network in doc["networks"] for node in network["nodes"]}
    check_record_bindings(active, nodes, binding, acceptance, error, business_ids)
    anchors = native_anchors(doc, model, binding, data, error)
    check_links(doc, model, binding, anchors, data, active, error)
    return {
        "valid": not errors,
        "errors": errors,
        "semantic_revision": expected["semantic_revision"],
        "bound_state_models": [primary] if primary in models else [],
        "scope": expected["scope"],
        "limits": ["Source/case/runtime evidence must also pass the existing independent gates."],
    }
