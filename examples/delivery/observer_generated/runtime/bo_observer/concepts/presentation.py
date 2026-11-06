"""Validate optional route labels against existing conceptual relationships.

Routes affect reading order only. The agent selects existing concept/edge IDs;
it cannot create transitions, infer causality or merge shared policy predicates
by adding a layout annotation. Confirmation hashes exclude this display layer.
"""

from .common import fields, records, references

ORDERING = {
    "business": {"flow", "event", "join", "retry", "cancel"},
    "state": {"transition", "declares_target"},
    "rules": {"data", "guard", "decision_result"},
}


def apply_routes(result, presentation, sources):
    """Attach checked route memberships to graph copies with stable identities."""
    if presentation is None:
        return
    fields(presentation, {"routes"}, {"routes"}, "concept presentation")
    nodes = {node["id"]: node for node in result["graph"]["nodes"]}
    edges = {edge["id"]: edge for edge in result["graph"]["edges"]}
    for ident, route in records(presentation["routes"], "presentation routes").items():
        fields(
            route,
            {"id", "label", "nodes", "edges", "source_refs"},
            {"id", "nodes", "edges", "source_refs"},
            "presentation route",
        )
        references(route, sources, "presentation route " + ident)
        for key, inventory in (("nodes", nodes), ("edges", edges)):
            values = route[key]
            if (
                not isinstance(values, list)
                or not values
                or any(not isinstance(value, str) or value not in inventory for value in values)
                or len(set(values)) != len(values)
            ):
                raise ValueError("presentation route has unknown or repeated " + key)
        members = set(route["nodes"])
        layers = {nodes[node]["layer"] for node in members}
        if len(layers) != 1 or next(iter(layers)) not in ORDERING:
            raise ValueError("a presentation route must stay in one conceptual plane")
        layer = next(iter(layers))
        adjacent = {node: set() for node in members}
        for eid in route["edges"]:
            edge = edges[eid]
            if (
                edge["from"] not in members
                or edge["to"] not in members
                or edge["type"] not in ORDERING[layer]
            ):
                raise ValueError("presentation route needs existing typed ordering edges")
            adjacent[edge["from"]].add(edge["to"])
            adjacent[edge["to"]].add(edge["from"])
        visited, pending = set(), [route["nodes"][0]]
        while pending:
            node = pending.pop()
            if node not in visited:
                visited.add(node)
                pending.extend(adjacent[node] - visited)
        if visited != members:
            raise ValueError("presentation route contains disconnected nodes")
        for node in members:
            nodes[node].setdefault("layout_routes", []).append(ident)
        for eid in route["edges"]:
            edges[eid].setdefault("layout_routes", []).append(ident)
