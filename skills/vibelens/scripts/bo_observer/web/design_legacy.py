"""Compatibility projection for existing business-discovery/v1 documents.

Version 2 assembly lives in concepts. Keeping this adapter isolated preserves
existing primary model-node identities without pretending legacy drafts contain
confirmed state-machine semantics.
"""


def legacy_model(doc, identities, project):
    """Project the original business/policy draft without adding runtime facts."""
    raw = [n for net in doc["networks"] for n in net["nodes"]]
    if len(set(identities.values())) != len(identities):
        raise ValueError(
            "Design nodes require unique primary IDs; represent shared relations with edges"
        )
    nodes = []
    for n in raw:
        kind = {"action": "action", "condition": "decision", "event": "data"}.get(
            n["kind"], n["kind"]
        )
        parent = identities.get(n.get("parent"))
        if n.get("parent") and parent is None:
            raise ValueError("Design node parent not found: " + n["id"])
        nodes.append(
            {
                "id": identities[n["id"]],
                "label": n["label"],
                "kind": kind,
                "layer": (
                    "business" if kind == "action" else "state" if kind == "state" else "design"
                ),
                "summary": n.get("summary", ""),
                "origin": "design",
                "capture": {},
                **({"parent": parent} if parent else {}),
            }
        )
    # Reject containment cycles rather than hiding them as an empty graph.
    parents = {n["id"]: n.get("parent") for n in nodes}
    for ident in parents:
        seen = set()
        while ident is not None:
            if ident in seen:
                raise ValueError("Cycle in design node hierarchy")
            seen.add(ident)
            ident = parents.get(ident)
    edges = [
        {
            "id": e["id"],
            "from": identities[e["from"]],
            "to": identities[e["to"]],
            "type": {"event": "flow", "retry": "flow", "cancel": "flow"}.get(
                e["relation"], e["relation"]
            ),
            "label": e["label"],
            "origin": "design",
        }
        for net in doc["networks"]
        for e in net["edges"]
    ]
    machine = {"values": [], "labels": {}, "transitions": []}
    model = {
        "project_id": project,
        "nodes": nodes,
        "edges": edges,
        "machine": machine,
        "graph_roots": [n["id"] for n in nodes if not n.get("parent")],
        "presentation": {"subject": doc.get("title", "Project design")},
    }
    from ..graph.relations.model import discovery as construct_relations

    registered = construct_relations(doc, identities)
    if registered is not None:
        model["edges"] = registered["edges"]
        model["relation_registry"] = registered["relation_registry"]
    if doc.get("policy"):
        from ..policy.projection import project as project_policy

        model["policy"] = doc["policy"]
        model = project_policy(model, bound=False)
    return model
