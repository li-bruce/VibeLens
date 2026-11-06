"""Report the actual structure of each conceptual network, without inventing links."""

from collections import Counter

from .presentation import ORDERING


def network_review(graph):
    """Distinguish behavioral edges from containment and cross-layer associations.

    Separate components can be legitimate independent user journeys. Report them
    for intent review, rather than connecting them by name or forcing one flow.
    A containment-only star does not count as an execution network.
    """
    nodes = {node["id"]: node for node in graph.get("nodes", [])}
    result = {}
    for layer, ordering in ORDERING.items():
        members = {key for key, node in nodes.items() if node.get("layer") == layer}
        internal = [
            edge
            for edge in graph.get("edges", [])
            if edge["from"] in members and edge["to"] in members
        ]
        behavior = [edge for edge in internal if edge["type"] in ordering]
        relevant = {
            key
            for key in members
            if nodes[key].get("concept_kind")
            in {
                (
                    "action"
                    if layer == "business"
                    else "state" if layer == "state" else "rule_expression"
                ),
                "rule_operation" if layer == "rules" else "condition",
            }
        }
        # Input/fact nodes can connect two decisions. Traverse all behavioral
        # endpoints, then report only the layer's actionable concepts.
        adjacency = {key: set() for key in members}
        for edge in behavior:
            for source, target in ((edge["from"], edge["to"]), (edge["to"], edge["from"])):
                adjacency[source].add(target)
        remaining, components = set(relevant), []
        while remaining:
            pending, component = [min(remaining)], set()
            while pending:
                key = pending.pop()
                if key in component:
                    continue
                component.add(key)
                pending.extend(adjacency[key] - component)
            remaining -= component
            components.append(sorted(component & relevant))
        result[layer] = {
            "nodes": len(members),
            "relations": len(internal),
            "behavior_relations": len(behavior),
            "relation_types": dict(sorted(Counter(edge["type"] for edge in internal).items())),
            "components": components,
            "unconnected": sorted(key for key in relevant if not adjacency[key]),
            "review_required": len(relevant) > 1 and len(components) > 1,
        }
    return result
