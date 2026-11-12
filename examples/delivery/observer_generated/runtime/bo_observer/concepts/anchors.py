"""Resolve conceptual references to explicit native event, guard and capture anchors."""

from .common import canonical_id

try:
    from ...bo_models import binding_machines, machine_view
except ImportError:
    from bo_models import binding_machines, machine_view


def native_anchors(doc, model, bindings, data, error):
    """Check declared anchor meaning; labels and source proximity are never evidence."""
    nodes = {item["id"]: item for item in model.get("nodes", [])}
    anchors = {}
    for ident, values in bindings.get("business", {}).items():
        anchors[ident] = list(values) if isinstance(values, list) else []
    for ident, values in bindings.get("facts", {}).items():
        anchors[canonical_id("fact", ident)] = (
            [value if isinstance(value, str) else value.get("node") for value in values]
            if isinstance(values, list)
            else []
        )
    for ident, values in bindings.get("effects", {}).items():
        anchors[ident] = list(values) if isinstance(values, list) else []
    policy = model.get("policy", {})
    for item in policy.get("nodes", []):
        key = "policy:" + item["id"]
        anchors[key] = [key] if key in nodes else []
    for item in policy.get("operations", []):
        key = "policy:" + item["root"]
        anchors[canonical_id("policy-operation", item["id"])] = [key] if key in nodes else []
    try:
        machines = binding_machines(bindings, model)
    except ValueError as exc:
        error("invalid_state_model_bindings", exc)
        machines = {}
    for primary, native_id in machines.items():
        design = next((item for item in doc["state_models"] if item["id"] == primary), None)
        if design is None:
            continue
        native = machine_view(model, native_id)
        for name in design["events"]:
            key = canonical_id("event", primary, name)
            item = bindings.get("events", {}).get(key)
            if (
                not isinstance(item, dict)
                or set(item) != {"node", "event"}
                or item["event"] != name
                or item["node"] not in nodes
                or not nodes[item["node"]].get("source")
            ):
                error("unbound_native_event", key)
                continue
            anchors[key] = [item["node"]]
        for transition in design["transitions"]:
            key = canonical_id("transition", primary, transition["id"])
            anchors[key] = anchors.get(canonical_id("event", primary, transition["trigger"]), [])
        for name, logical in design["guards"].items():
            key = canonical_id("guard", primary, name)
            source = native.get("machine", {}).get("guards", {}).get(name, {}).get("source")
            decision = data["records"][key].get("decision")
            item = bindings.get("guards", {}).get(key)
            if item is None and decision:
                candidates = anchors.get(decision, [])
                if len(candidates) == 1 and nodes[candidates[0]].get("source") == source:
                    item = {"node": candidates[0], "decision": decision, "field": "value"}
            if not isinstance(item, dict) or set(item) != {"node", "decision", "field"}:
                error("unbound_native_guard", key)
                continue
            target = nodes.get(item["node"], {})
            if (
                not source
                or target.get("source") != source
                or target.get("capture", {}).get("out", {}).get(item["field"]) != "boolean"
            ):
                error("native_guard_source_or_result_differs", key)
            if item["decision"] != decision:
                error("native_guard_decision_differs", key)
            if decision:
                value = data["records"][decision]
                operation = value.get("id") if value["kind"] == "rule_operation" else None
                root = value["root"] if operation else decision.removeprefix("policy:")
                if (
                    target.get("policy_node") != root
                    and target.get("policy_operation") != operation
                ):
                    error("native_guard_has_no_matching_rule_identity", key)
            elif not logical.get("meaning"):
                error("native_guard_lacks_meaning", key)
            anchors[key] = [item["node"]]
        for state in data["index"]:
            if data["index"][state]["kind"] == "state" and state.startswith(
                canonical_id("state", primary) + ":"
            ):
                value = data["records"][state].get("name")
                # Hierarchical state names are encoded in the canonical suffix.
                from urllib.parse import unquote

                value = unquote(state.split(":", 2)[-1])
                anchors[state] = [
                    key
                    for key, node in nodes.items()
                    if node.get("kind") == "state"
                    and node.get("value") == value
                    and ("machines" not in model or node.get("state_model_id") == native_id)
                ]
        execution = design.get("execution")
        if execution:
            for role, items in [
                ("activity", execution["activities"]),
                ("resource", execution["resources"]),
                ("join", [execution["join"]]),
            ]:
                for item in items:
                    key = canonical_id(role, primary, item["id"])
                    node = nodes.get(item["id"], {})
                    if (
                        node.get("execution_role") != role
                        or role == "activity"
                        and not node.get("source")
                    ):
                        error("unbound_native_activity_structure", key)
                    else:
                        anchors[key] = [item["id"]]
    return anchors


def check_links(doc, model, bindings, anchors, data, active, error):
    """Check physical edge endpoints and meanings, including inverse guard direction."""
    edges = {item["id"]: item for item in model.get("edges", [])}
    from .semantics import resolve_index

    for link in doc["crosslinks"]:
        if link["id"] not in active:
            continue
        a, b = resolve_index(data["index"], link["from"]), resolve_index(data["index"], link["to"])
        left, right = set(anchors.get(a, [])), set(anchors.get(b, []))
        raw = bindings.get("crosslinks", {}).get(link["id"])
        refs = raw.get("edges") if isinstance(raw, dict) else raw
        if isinstance(raw, dict):
            if (
                set(raw) != {"relation", "from", "to", "native_event", "edges"}
                or raw.get("relation") != link["relation"]
                or set(raw.get("from", [])) != left
                or set(raw.get("to", [])) != right
            ):
                error("crosslink_binding_endpoints_differ", link["id"])
                continue
        if not left or not right or not isinstance(refs, list):
            error("unbound_cross_model_relation", link["id"])
            continue
        if not refs:
            native = bindings.get("events", {}).get(b, {})
            if not (
                link["relation"] == "action_requests_event"
                and isinstance(raw, dict)
                and left == right
                and raw["native_event"] == native.get("event")
                and len(left) == 1
            ):
                error("crosslink_has_no_native_witness_binding", link["id"])
            continue
        relation = link["relation"]
        if relation in {"transition_guarded_by", "decision_reads_fact"}:
            left, right = right, left
        allowed = (
            {"guard"}
            if relation == "transition_guarded_by"
            else {"data"} if relation == "decision_reads_fact" else {"flow", "event", "data"}
        )
        for ref in refs:
            actual = edges.get(ref)
            if (
                not actual
                or actual.get("from") not in left
                or actual.get("to") not in right
                or actual.get("type") not in allowed
            ):
                error("crosslink_native_edge_meaning_differs", link["id"])
