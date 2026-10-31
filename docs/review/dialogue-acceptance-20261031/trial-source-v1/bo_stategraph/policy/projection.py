"""Project shared expressions and implementation links into the existing graph."""

from copy import deepcopy

from .definition import validate, dependencies

ORIGIN = "policy-definition"
PREFIX = "policy:"


def elements(policy, base_nodes, *, bound=True):
    """Retain one canonical node per expression, regardless of permission fan-out."""
    index = validate(policy, bound=bound)
    known = {node["id"]: node for node in base_nodes}
    group = {
        "id": PREFIX + "network",
        "kind": "decision",
        "layer": "predicate",
        "label": "Rules",
        "summary": "Rules",
        "origin": ORIGIN,
        "capture": {"in": {}, "out": {}},
    }
    nodes, edges = [group], []

    def edge(ident, source, target, kind, label):
        edges.append(
            {
                "id": PREFIX + ident,
                "from": source,
                "to": target,
                "type": kind,
                "label": label,
                "origin": ORIGIN,
                "evidence": "policy declaration",
                "evidence_kind": "conceptual",
                **({"code_relation": "maps"} if kind == "maps" else {}),
            }
        )

    for item in index["nodes"].values():
        ident, op = item["id"], item["op"]
        inputs = {"bo_check": "string", "bo_basis": "string"}
        node = {
            "id": PREFIX + ident,
            "kind": "data" if op in {"input", "constant"} else "decision",
            "layer": "predicate",
            "parent": group["id"],
            "label": (
                {"all": "AND · ", "any": "OR · ", "not": "NOT · "}.get(op, "")
                + item.get("label", ident)
            ),
            "summary": item.get("summary", item.get("label", ident)),
            "origin": ORIGIN,
            "policy_node": ident,
            "operator": op,
            "source_refs": item["source_refs"],
            "capture": {"in": inputs, "out": {"value": index["types"][ident], "status": "string"}},
            "capture_metadata": {"in": ["bo_check", "bo_basis"], "out": ["status"]},
        }
        if op == "predicate":
            pred = index["predicates"][item["predicate"]]
            inputs.update(pred["parameters"])
            if pred.get("source"):
                node["source"] = deepcopy(pred["source"])
                anchor = pred.get("implementation_node")
                # Reuse a physical function already mapped elsewhere in the graph.
                matches = [
                    n
                    for n in base_nodes
                    if n.get("kind") == "function" and n.get("source") == pred["source"]
                ]
                if anchor:
                    if anchor not in known or known[anchor].get("source") != pred["source"]:
                        raise ValueError("policy implementation node differs from source")
                elif len(matches) == 1:
                    anchor = matches[0]["id"]
                else:
                    anchor = PREFIX + "function:" + pred["id"]
                    if not any(n["id"] == anchor for n in nodes):
                        nodes.append(
                            {
                                "id": anchor,
                                "kind": "function",
                                "code_role": "function",
                                "layer": "program",
                                "label": pred["source"]["symbol"],
                                "summary": "Native rule predicate",
                                "source": deepcopy(pred["source"]),
                                "origin": ORIGIN,
                                "capture": {"in": {}, "out": {}},
                            }
                        )
                edge("mapping:" + ident, node["id"], anchor, "maps", "Implemented by")
        nodes.append(node)
        edge("contains:" + ident, group["id"], node["id"], "contains", "Rule expression")
        for offset, reference in enumerate(dependencies(item)):
            edge(
                "dependency:" + ident + ":" + str(offset),
                PREFIX + reference,
                node["id"],
                "data" if op == "predicate" else "guard",
                (
                    ", ".join(k for k, ref in item.get("arguments", {}).items() if ref == reference)
                    if op == "predicate"
                    else op
                ),
            )
    for operation in index["operations"].values():
        for target in operation.get("business_nodes", []):
            if target not in known:
                raise ValueError("policy operation has no business anchor: " + target)
            edge(
                "operation:" + operation["id"] + ":" + target,
                PREFIX + operation["root"],
                target,
                "guard",
                "Requires",
            )
    return nodes, edges


def project(model, *, bound=True):
    """Replace only generated policy elements; preserve all other identities/layout data."""
    result = deepcopy(model)
    if not model.get("policy"):
        return result
    base = [node for node in model["nodes"] if node.get("origin") != ORIGIN]
    nodes, edges = elements(model["policy"], base, bound=bound)
    previous = {n["id"]: n for n in model["nodes"] if n.get("origin") == ORIGIN}
    for node in nodes:
        old = previous.get(node["id"], {})
        if old.get("source") == node.get("source") and "code_evidence" in old:
            node["code_evidence"] = deepcopy(old["code_evidence"])
    base_ids = {node["id"] for node in base}
    if base_ids.intersection(node["id"] for node in nodes):
        raise ValueError("policy projection identity collides with project nodes")
    result["nodes"] = base + nodes
    result["edges"] = [
        edge for edge in model.get("edges", []) if edge.get("origin") != ORIGIN
    ] + edges
    # Other projectors retain their own elements. Preserve the existing order
    # so composing policy/data refreshes cannot alternate the model's hash.
    for name in ("nodes", "edges"):
        order = {item["id"]: position for position, item in enumerate(model.get(name, []))}
        result[name].sort(key=lambda item: order.get(item["id"], len(order)))
    ids = [node["id"] for node in result["nodes"]]
    edge_ids = [edge["id"] for edge in result["edges"]]
    if len(ids) != len(set(ids)) or len(edge_ids) != len(set(edge_ids)):
        raise ValueError("policy projection creates duplicate identities")
    return result


def projection_errors(model, *, bound=True):
    if not model.get("policy"):
        orphaned = any(node.get("origin") == ORIGIN for node in model.get("nodes", []))
        orphaned |= any(
            edge.get("origin") == ORIGIN or edge.get("type") == "maps"
            for edge in model.get("edges", [])
        )
        return ["policy elements require a valid policy declaration"] if orphaned else []
    try:
        expected = project(model, bound=bound)
        actual_nodes = {n["id"]: n for n in model["nodes"] if n.get("origin") == ORIGIN}
        actual_edges = {e["id"]: e for e in model["edges"] if e.get("origin") == ORIGIN}
        expected_nodes = {n["id"]: n for n in expected["nodes"] if n.get("origin") == ORIGIN}
        expected_edges = {e["id"]: e for e in expected["edges"] if e.get("origin") == ORIGIN}
        if any(
            edge.get("type") == "maps" and expected_edges.get(edge["id"]) != edge
            for edge in model.get("edges", [])
        ):
            return ["maps relation is outside the exact policy projection"]
        return (
            []
            if actual_nodes == expected_nodes and actual_edges == expected_edges
            else ["policy graph projection is missing, changed or stale"]
        )
    except (ValueError, KeyError, TypeError) as exc:
        return [str(exc)]
