"""Attach insertion decisions to authored graphs without changing their engines."""

from copy import deepcopy

from .contract import encoded
from .index import RelationIndex


def node_ids(model):
    """Read exact graph identities; a display label never establishes identity."""
    return [node["id"] for node in model["nodes"]]


def validate(model):
    """Recompute registered decisions and reject bypassed edits to their edges.

    Other projectors may append physical source/state/data nodes and edges. They
    remain intact, outside this registry, and subject to their existing checks.
    A registered claim cannot silently reappear as an unregistered display edge.
    """
    if "relation_registry" not in model:
        return None
    index = RelationIndex.restore(model["relation_registry"])
    saved = index.export()
    current_nodes = RelationIndex._node_ids(node_ids(model))
    if set(saved["nodes"]) - current_nodes:
        raise ValueError("Relation registry references missing graph nodes")
    registered = {item["edge"]["id"] for item in saved["entries"]}
    actual = [edge for edge in model["edges"] if edge["id"] in registered]
    if encoded(actual) != encoded(index.edges):
        raise ValueError("Graph edges differ from registered insertion decisions")
    return index


def attach(model, index):
    """Publish the canonical registered edges and preserve unrelated physical facts."""
    value = deepcopy(model)
    saved = index.export()
    registered = {item["edge"]["id"] for item in saved["entries"]}
    previous = value.get("relation_registry", {})
    registered.update(item["edge"]["id"] for item in previous.get("entries", []))
    value["edges"] = index.edges + [edge for edge in value["edges"] if edge["id"] not in registered]
    value["relation_registry"] = saved
    validate(value)
    return value


def construct(model, rules=None, *, registrations=None, limits=None):
    """Register authored edges in one transaction while constructing a graph.

    Registration metadata is separate from the physical edge payload. No types,
    conditions or duplicate identity are inferred from labels or endpoint layers.
    """
    if "relation_registry" in model:
        raise ValueError("Graph already has a registry; update through its index")
    metadata = {} if registrations is None else registrations
    if not isinstance(metadata, dict):
        raise ValueError("Expected relation registrations object")
    edge_ids = {edge["id"] for edge in model["edges"]}
    if set(metadata) - edge_ids:
        raise ValueError("Registration metadata references an unknown edge")
    entries = []
    for edge in model["edges"]:
        details = metadata.get(edge["id"], {})
        if not isinstance(details, dict) or "edge" in details:
            raise ValueError("Registration metadata cannot replace an edge payload")
        entries.append({"edge": edge, **details})
    index = RelationIndex(node_ids(model), rules, limits=limits)
    index.apply([{"op": "insert", "entry": item} for item in entries])
    return attach(model, index)


def discovery(doc, identities=None):
    """Validate and construct only explicitly configured discovery relations."""
    raw_nodes = [node for network in doc["networks"] for node in network["nodes"]]
    identities = identities or {node["id"]: node["id"] for node in raw_nodes}
    edges, metadata = [], {}
    if "relation_rules" not in doc:
        if any(
            "relation_registration" in edge
            for network in doc["networks"]
            for edge in network["edges"]
        ):
            raise ValueError("Discovery relation registrations require relation_rules")
        return None
    rules = doc["relation_rules"]
    if not isinstance(rules, dict):
        raise ValueError("Expected discovery relation_rules object")
    # Validate the contract before reading selectors or using any declaration.
    from .contract import Rules

    contract = Rules(rules)
    for network in doc["networks"]:
        for raw in network["edges"]:
            details = raw.get("relation_registration", {})
            if not isinstance(details, dict):
                raise ValueError("Expected discovery relation registration metadata")
            edge = {
                "id": raw["id"],
                "from": identities[raw["from"]],
                "to": identities[raw["to"]],
                "type": {"event": "flow", "retry": "flow", "cancel": "flow"}.get(
                    raw["relation"], raw["relation"]
                ),
                "label": raw["label"],
                "origin": "design",
                "evidence": "discovery:" + ",".join(raw["source_refs"]),
                "source_refs": deepcopy(raw["source_refs"]),
            }
            definition = contract.definitions.get(details.get("relation"))
            if definition:
                if definition["mode"] == "summary":
                    if raw["relation"] != "maps":
                        raise ValueError("Discovery summaries must be conceptual maps")
                    edge.update(origin="relation-summary", semantic_relation=definition["id"])
                elif "semantic_relation" in definition["match"]:
                    edge["semantic_relation"] = definition["id"]
            edges.append(edge)
            metadata[raw["id"]] = details
    return construct(
        {"nodes": [{"id": ident} for ident in identities.values()], "edges": edges},
        rules,
        registrations=metadata,
    )
