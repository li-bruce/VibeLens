"""Portable model identity shared by native execution and the external observer.

Layers classify presentation. Machine IDs identify executable definitions; instance
IDs identify objects governed by those definitions. The legacy single machine is
read without rewriting its node IDs, snapshots, or historical exports.
"""

from copy import deepcopy
from urllib.parse import quote

LEGACY_MACHINE = "default"


def model_inventory(model):
    """Compact durable coding handoff; full declarations remain the source of truth."""
    machines = machine_registry(model) if "machine" in model or "machines" in model else {}
    return {
        "state_models": [
            {"id": key, "engine": chart.get("engine"), "states": len(chart.get("values", []))}
            for key, chart in machines.items()
        ],
        "networks": [
            {"id": item["id"], "layer": item["layer"], "nodes": len(item["nodes"])}
            for item in model.get("networks", [])
        ],
        "state_bindings": (model.get("concepts") or {}).get("state_models", {}),
    }


def machine_registry(model):
    """Return all declared machines, rejecting two competing declaration sources."""
    if "machines" in model:
        if "machine" in model:
            raise ValueError("declare machines or legacy machine, never both")
        machines = model["machines"]
        if not isinstance(machines, dict) or any(
            not isinstance(key, str) or not key.strip() or not isinstance(value, dict)
            for key, value in machines.items()
        ):
            raise ValueError("machines must map stable nonempty IDs to definitions")
        return machines
    chart = model.get("machine")
    if not isinstance(chart, dict):
        raise ValueError("missing machine registry")
    return {LEGACY_MACHINE: chart}


def select_machine(model, model_id=None):
    """Require explicit model identity for registries, including one-model registries."""
    machines = machine_registry(model)
    if model_id is None and "machines" not in model:
        model_id = LEGACY_MACHINE
    if model_id not in machines:
        raise ValueError("missing or unknown state_model_id: " + str(model_id))
    return model_id, machines[model_id]


def machine_view(model, model_id):
    """Provide an isolated validation view while preserving physical source IDs.

    An activity declaration owns its resource/join relations. Cross-model links stay
    in the complete graph and are not interpreted as local execution dependencies.
    """
    _, chart = select_machine(model, model_id)
    if "machines" not in model:
        return model
    result = {key: value for key, value in model.items() if key not in {"machines", "networks"}}
    result["machine"] = chart
    result["nodes"] = [
        (
            {**node, "layer": "state"}
            if node.get("state_model_id") == model_id and node.get("layer") == "state"
            else {**node, "layer": "foreign_state"} if node.get("layer") == "state" else node
        )
        for node in model.get("nodes", [])
    ]
    execution = chart.get("execution", {})
    owned = {item["id"] for item in execution.get("activities", [])}
    owned.update(item["id"] for item in execution.get("resources", []))
    if execution.get("join"):
        owned.add(execution["join"]["id"])
    result["edges"] = [
        edge
        for edge in model.get("edges", [])
        if edge.get("type") not in {"resource", "join"}
        or edge["from"] in owned
        and edge["to"] in owned
    ]
    return result


def instance_key(run_id, instance_id, model_id=None):
    """Keep old recording identities; namespace registry instances without collisions."""
    if model_id is None:
        return run_id + ":" + instance_id
    return "model-instance:" + ":".join(
        quote(value, safe="") for value in (model_id, run_id, instance_id)
    )


def binding_machines(binding, model):
    """Resolve conceptual model IDs to native IDs; no primary-model fallback in v2."""
    if binding.get("schema") == "bo-concept-bindings/v2":
        mapping = binding.get("state_models")
        if not isinstance(mapping, dict) or any(
            not isinstance(key, str) or not key or not isinstance(value, str) or not value
            for key, value in mapping.items()
        ):
            raise ValueError("state_models must map conceptual IDs to native machine IDs")
        if len(set(mapping.values())) != len(mapping):
            raise ValueError("independent state models cannot share one native machine binding")
        for value in mapping.values():
            select_machine(model, value)
        return dict(mapping)
    if "machines" in model:
        raise ValueError("machine registries require concept bindings v2")
    primary = binding.get("primary_state_model")
    return {primary: LEGACY_MACHINE} if primary is not None else {}


def network_registry(model):
    """Validate authored subnet membership in any layer without forcing connectivity.

    Membership is many-to-many. Shared functions and predicates retain one physical
    identity. Edges are existing graph relations, never inferred executable links.
    """
    networks = model.get("networks", [])
    if not isinstance(networks, list):
        raise ValueError("networks must be a list")
    nodes = {node["id"] for node in model.get("nodes", [])}
    edges = {edge["id"]: edge for edge in model.get("edges", [])}
    result = {}
    for network in networks:
        if not isinstance(network, dict) or set(network) - {
            "id",
            "layer",
            "label",
            "nodes",
            "edges",
            "state_model_id",
        }:
            raise ValueError("unsupported network declaration")
        key = network.get("id")
        if not isinstance(key, str) or not key.strip() or key in result:
            raise ValueError("missing or duplicate network ID")
        if network.get("layer") not in {
            "business",
            "state",
            "rules",
            "entry",
            "structure",
            "symbols",
            "implementation",
            "data",
            "unknown",
        }:
            raise ValueError("unknown network layer: " + key)
        if "label" in network and (
            not isinstance(network["label"], str) or not network["label"].strip()
        ):
            raise ValueError("network label must be nonempty text: " + key)
        members = network.get("nodes")
        links = network.get("edges", [])
        if (
            not isinstance(members, list)
            or not members
            or any(not isinstance(n, str) for n in members)
            or len(set(members)) != len(members)
            or set(members) - nodes
        ):
            raise ValueError("network has missing, duplicate or unknown members: " + key)
        if (
            not isinstance(links, list)
            or any(not isinstance(e, str) for e in links)
            or len(set(links)) != len(links)
            or set(links) - edges.keys()
        ):
            raise ValueError("network has duplicate or unknown relations: " + key)
        if any(edges[e]["from"] not in members or edges[e]["to"] not in members for e in links):
            raise ValueError("network relation endpoints must be members: " + key)
        if "state_model_id" in network:
            select_machine(model, network["state_model_id"])
            if network["layer"] != "state":
                raise ValueError("machine network must belong to state layer")
            if any(
                node.get("state_model_id") != network["state_model_id"]
                for node in model["nodes"]
                if node["id"] in members and node.get("layer") == "state"
            ):
                raise ValueError("machine network contains another model's states: " + key)
        result[key] = deepcopy(network)
    return result
