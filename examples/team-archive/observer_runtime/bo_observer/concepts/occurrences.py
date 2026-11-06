"""Separate conceptual occurrences from physical declarations at the view boundary.

A reused native ID does not prove that an action, state and predicate mean the
same thing. Keep confirmed IDs in ``concept_id`` and native IDs in binding edges;
only the colliding display occurrence gets a deterministic, namespaced ID.
"""

from .common import canonical_id


def shares_meaning(concept, native):
    """Coalesce only an already conceptual native declaration of the same role."""
    kind = concept.get("concept_kind")
    if kind == "rule_expression":
        return native.get("policy_node") == concept["id"].removeprefix("policy:")
    if kind == "state":
        return native.get("kind") == "state" and native.get("value") == concept.get("value")
    return (
        concept.get("layer") == native.get("layer") == "business"
        and kind == "action"
        and native.get("kind") == "action"
    )


def separate_occurrences(graph, native_model):
    """Rewrite display endpoints together, retaining every original declaration ID.

    This function operates on a detached projection. It never rewrites discovery,
    confirmed semantic records, executable declarations or captured events.
    """
    native = {node["id"]: node for node in native_model["nodes"]}
    used = set(native) | {node["id"] for node in graph["nodes"]}
    aliases = {}
    for node in graph["nodes"]:
        original = node["id"]
        node["concept_id"] = original
        if original not in native or shares_meaning(node, native[original]):
            continue
        alias = canonical_id("concept-view", original)
        if alias in used:
            raise ValueError("reserved concept occurrence ID collision: " + alias)
        aliases[original] = alias
        used.add(alias)
        node["id"] = alias
    native_edges = {edge["id"] for edge in native_model["edges"]}
    edge_ids = {edge["id"] for edge in graph["edges"]} | native_edges
    graph["relation_occurrences"] = {}

    def rewrite_edge(edge):
        original = edge["id"]
        if original in native_edges:
            alias = canonical_id("concept-relation", original)
            if alias in edge_ids:
                raise ValueError("reserved concept relation ID collision: " + alias)
            edge["id"] = alias
            graph["relation_occurrences"][original] = alias
        for endpoint in ("from", "to"):
            edge[endpoint] = aliases.get(edge[endpoint], edge[endpoint])
        if edge.get("transition") in aliases:
            edge["transition"] = aliases[edge["transition"]]
        for equivalent in edge.get("equivalent_relations", []):
            rewrite_edge(equivalent)

    for node in graph["nodes"]:
        if node.get("parent") in aliases:
            node["parent"] = aliases[node["parent"]]
    for edge in graph["edges"]:
        rewrite_edge(edge)
    graph["graph_roots"] = [aliases.get(key, key) for key in graph["graph_roots"]]
    return aliases
