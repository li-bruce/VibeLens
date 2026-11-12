"""Expose peer model subnetworks without merging independent user capabilities."""

from .common import canonical_id


def model_networks(graph, dependencies):
    """Build inspectable membership from declared ownership and rule dependencies.

    State charts and business flows retain their roots. Each rule operation exposes
    its dependency network; common predicates appear in several memberships with the
    same identity. Connectivity is reported, never manufactured.
    """
    nodes = {node["id"]: node for node in graph["nodes"]}
    roots = [
        node
        for node in nodes.values()
        if node.get("concept_kind") in {"business_network", "state_model", "rule_operation"}
    ]
    result = []
    for root in roots:
        layer = root["layer"]
        members = {root["id"]}
        if layer == "rules":
            pending = [root["id"]]
            while pending:
                for key in dependencies.get(pending.pop(), []):
                    if key in nodes and nodes[key]["layer"] == layer and key not in members:
                        members.add(key)
                        pending.append(key)
        else:
            changed = True
            while changed:
                prior = len(members)
                for key, node in nodes.items():
                    if node["layer"] == layer and (
                        node.get("parent") in members or root["id"] in dependencies.get(key, [])
                    ):
                        members.add(key)
                changed = len(members) != prior
        result.append(
            {
                "id": canonical_id("network", root["id"]),
                "layer": layer,
                "label": root["label"],
                "nodes": sorted(members),
                "edges": [
                    edge["id"]
                    for edge in graph["edges"]
                    if edge["from"] in members and edge["to"] in members
                ],
            }
        )
    return result
