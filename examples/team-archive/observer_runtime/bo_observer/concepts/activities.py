"""Source-free validation and projection of the existing integrated activity model.

This module uses the same capacity, waiting and ALL-join contract as the native
engine. It introduces no scheduler and does not infer activity outcomes.
"""

from copy import deepcopy

try:
    from ...execution_contract import validate_execution_graph
except ImportError:
    from execution_contract import validate_execution_graph

from .common import canonical_id as cid, fields, records, text, without_display


def activity_semantics(spec):
    """Strip only declared activity-record metadata and native source bindings.

    Resource identifiers inside ``requires`` may themselves be named ``label``;
    those are map keys, not metadata, and remain part of the capacity contract.
    """

    def envelope(item):
        value = without_display(item)
        source = value.get("source")
        if isinstance(source, dict) and set(source) == {"path", "symbol"}:
            value.pop("source")
        return value

    result = envelope(spec)
    for field in ("activities", "resources"):
        result[field] = [envelope(item) for item in spec[field]]
    result["join"] = envelope(spec["join"])
    return result


def validate_activities(state, states, business_ids):
    """Validate a source-free activity declaration against native engine semantics."""
    spec = state["execution"]
    fields(
        spec,
        {
            "schema",
            "within",
            "parent",
            "activity_state_type",
            "activity_states",
            "activities",
            "resources",
            "join",
            "source_refs",
        },
        {"schema", "within", "parent", "activity_states", "activities", "resources", "join"},
        "activity design",
    )
    if spec["schema"] != "activity-graph/v1":
        raise ValueError("unsupported activity configuration schema")
    owners = {
        *business_ids,
        cid("state-model", state["id"]),
        *[cid("state", state["id"], name) for name in states],
    }
    if spec["within"] not in states or spec["parent"] not in owners:
        raise ValueError("activity design scope is not declared")
    activity_states = spec["activity_states"]
    if (
        not isinstance(activity_states, list)
        or any(not text(item) for item in activity_states)
        or len(set(activity_states)) != len(activity_states)
    ):
        raise ValueError("activity states must have distinct names")
    activities = records(spec["activities"], "activities", empty=False)
    resources = records(spec["resources"], "resources")
    for name, item in activities.items():
        fields(
            item,
            {"id", "requires", "label", "summary", "source_refs"},
            {"id", "requires"},
            "activity " + name,
        )
        if not isinstance(item["requires"], dict):
            raise ValueError("activity resource requirements must be an object")
    for name, item in resources.items():
        fields(
            item,
            {"id", "scope", "capacity_field", "min", "max", "label", "summary", "source_refs"},
            {"id", "scope", "capacity_field", "min", "max"},
            "resource " + name,
        )
        if not text(item["capacity_field"]):
            raise ValueError("resource capacity needs a field identity")
    join = spec["join"]
    fields(
        join,
        {
            "id",
            "policy",
            "requires",
            "success_event",
            "success_states",
            "guard",
            "label",
            "summary",
            "source_refs",
        },
        {"id", "policy", "requires", "success_event", "success_states", "guard"},
        "activity join",
    )
    if not text(join["id"]) or not isinstance(join["requires"], list):
        raise ValueError("join needs identity and activity members")
    success_states = join["success_states"]
    if (
        not isinstance(success_states, list)
        or not success_states
        or len(set(success_states)) != len(success_states)
        or set(success_states) - set(states)
    ):
        raise ValueError("join completion states must be declared")
    if join["success_event"] not in state["events"] or join["guard"] not in state["guards"]:
        raise ValueError("join completion event and guard must be declared")
    if not any(
        item["trigger"] == join["success_event"] and item["dest"] in success_states
        for item in state["transitions"]
    ):
        raise ValueError("join completion event has no matching state transition")

    # Supply only a validation skeleton to the native structural validator.
    # None denotes an intentionally unbound source; no path/symbol is invented,
    # exported, or used as source evidence. Runtime binding still requires real
    # sources and passes the existing full native graph/source checks.
    native = deepcopy(spec)
    for activity in native["activities"]:
        activity["source"] = None
    nodes = [{"id": spec["parent"]}]
    nodes += [
        {"id": name, "parent": spec["parent"], "execution_role": "activity"} for name in activities
    ]
    nodes += [
        {"id": name, "parent": spec["parent"], "execution_role": "resource"} for name in resources
    ]
    nodes.append({"id": join["id"], "parent": spec["parent"], "execution_role": "join"})
    edges = [
        {"from": resource, "to": name, "type": "resource", "units": units}
        for name, activity in activities.items()
        for resource, units in activity["requires"].items()
    ]
    edges += [{"from": name, "to": join["id"], "type": "join"} for name in activities]
    machine = {"values": list(states), "transitions": state["transitions"], "execution": native}
    validate_execution_graph({"machine": machine, "nodes": nodes, "edges": edges})


def add_activities(graph, model_id, state):
    """Expose resources, activities and joins on the existing state concern plane."""
    spec = state.get("execution")
    if not spec:
        return
    root, within = cid("state-model", model_id), cid("state", model_id, spec["within"])
    activity_ids = {
        item["id"]: cid("activity", model_id, item["id"]) for item in spec["activities"]
    }
    resource_ids = {item["id"]: cid("resource", model_id, item["id"]) for item in spec["resources"]}
    for role, items in [
        ("resource", spec["resources"]),
        ("activity", spec["activities"]),
        ("join", [spec["join"]]),
    ]:
        for item in items:
            ident = cid(role, model_id, item["id"])
            dependencies = [root, within]
            if role == "activity":
                dependencies += [resource_ids[name] for name in item["requires"]]
            elif role == "join":
                dependencies += [activity_ids[name] for name in item["requires"]]
                dependencies.append(cid("guard", model_id, item["guard"]))
            graph.add(
                ident,
                role,
                item,
                label=item.get("label", item["id"]),
                layer="state",
                aliases=[item["id"]],
                deps=dependencies,
                execution_role=role,
                parent=within,
            )
            graph.relation(
                cid("activity-scope", model_id, role, item["id"]), within, ident, "contains"
            )
    for activity in spec["activities"]:
        for resource, units in activity["requires"].items():
            graph.relation(
                cid("activity-resource", model_id, resource, activity["id"]),
                resource_ids[resource],
                activity_ids[activity["id"]],
                "resource",
                value={"units": units},
            )
        graph.relation(
            cid("activity-join", model_id, activity["id"]),
            activity_ids[activity["id"]],
            cid("join", model_id, spec["join"]["id"]),
            "join",
        )
    graph.relation(
        cid("join-completion", model_id),
        cid("join", model_id, spec["join"]["id"]),
        cid("event", model_id, spec["join"]["success_event"]),
        "enables_event",
    )
