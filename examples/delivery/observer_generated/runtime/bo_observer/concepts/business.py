"""Project user-facing actions and typed object facts before source code exists."""

from .common import canonical_id as cid, records, references, text


def add_business(graph, doc, sources):
    """Validate business operation scope and preserve explicit business routes."""
    add, relation = graph.add, graph.relation
    networks = records(doc["networks"], "networks", empty=False)
    business = {}
    for netid, net in networks.items():
        root = cid("business-network", netid)
        if (
            not all(text(net.get(k)) for k in ["title", "trigger", "outcome"])
            or not isinstance(net.get("actors"), list)
            or not net["actors"]
            or any(not text(x) for x in net["actors"])
        ):
            raise ValueError("business network needs actors, trigger and outcome")
        add(
            root,
            "business_network",
            {
                "actors": sorted(set(net["actors"])),
                "trigger": net["trigger"],
                "outcome": net["outcome"],
            },
            label=net["title"],
            layer="business",
        )
        local = records(net.get("nodes"), "business nodes", empty=False)
        for start in local:
            seen, current = set(), start
            while current in local:
                if current in seen:
                    raise ValueError("business containment cycle: " + start)
                seen.add(current)
                current = local[current].get("parent", root)
        for ident, item in local.items():
            references(item, sources, "business node " + ident)
            if (
                item.get("kind")
                not in {"action", "condition", "state", "effect", "resource", "event", "data"}
                or not text(item.get("label"))
                or not isinstance(item.get("meaning"), (str, dict))
                or not item["meaning"]
            ):
                raise ValueError("v2 business node needs kind, label and stable meaning: " + ident)
            if ident in business:
                raise ValueError("business identities must be globally unique")
            business[ident] = item
            parent = item.get("parent", root)
            if parent != root and parent not in local:
                raise ValueError("business parent is not in the same network")
            meaning = {
                k: v
                for k, v in item.items()
                if k
                not in {
                    "id",
                    "label",
                    "summary",
                    "source",
                    "source_refs",
                    "model_nodes",
                    "outside_reason",
                    "parent",
                    "x",
                    "y",
                }
            }
            add(
                ident,
                item["kind"],
                meaning,
                label=item["label"],
                layer="business",
                deps=[root],
                parent=parent,
            )
            relation(cid("business-contains", netid, ident), parent, ident, "contains")
        for ident, edge in records(net.get("edges"), "business edges").items():
            references(edge, sources, "business edge " + ident)
            if (
                edge.get("from") not in local
                or edge.get("to") not in local
                or edge.get("relation")
                not in {
                    "flow",
                    "guard",
                    "data",
                    "event",
                    "resource",
                    "join",
                    "retry",
                    "cancel",
                    "maps",
                }
            ):
                raise ValueError("business edge needs declared endpoints/relation: " + ident)
            relation(
                ident,
                edge["from"],
                edge["to"],
                edge["relation"],
                value={
                    k: v
                    for k, v in edge.items()
                    if k
                    not in {
                        "id",
                        "from",
                        "to",
                        "relation",
                        "label",
                        "source_refs",
                        "decision_refs",
                        "relation_registration",
                    }
                },
                label=edge.get("label"),
            )
    return business


def add_objects(graph, objects, facts):
    """Keep shared facts unique, with explicit links to the objects they describe."""
    add, relation = graph.add, graph.relation
    for ident, obj in objects.items():
        add(
            cid("object", ident),
            "object",
            obj,
            label=obj.get("label", ident),
            aliases=[ident],
            layer="business",
        )
    for ident, fact in facts.items():
        add(
            cid("fact", ident),
            "fact",
            fact,
            label=fact.get("label", ident),
            aliases=[ident],
            layer="rules",
            deps=[cid("object", fact["object"])],
        )
        relation(
            cid("object-fact", ident),
            cid("object", fact["object"]),
            cid("fact", ident),
            "describes_fact",
        )
