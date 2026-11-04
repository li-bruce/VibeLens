"""Resolve display identities to registered observation owners without inventing facts.

The display inventory can contain concepts, files and API declarations. Capture
still addresses native observation IDs. A conceptual association, dependency or
rule path never grants capture scope: only a checked implementation binding and
exact source ownership can lead to an observed node.
"""

from ..concepts.common import canonical_id


def display_graph(view):
    """Merge the static inventories advertised by this exact server snapshot.

    Native declarations win shared identities, matching the viewer. Duplicate
    identities inside one inventory are malformed, rather than silently erased.
    This includes loaded source slices, never a new unbounded source scan.
    """
    model = view["model"]
    nodes, edges = {}, {}
    for graph in [
        view.get("concept_structure"),
        view.get("project_structure"),
        view.get("api_structure"),
        view.get("code_structure"),
        model,
    ]:
        if not graph:
            continue
        for field, result in (("nodes", nodes), ("edges", edges)):
            items = graph.get(field, [])
            if len({item["id"] for item in items}) != len(items):
                raise ValueError("Duplicate graph identities in " + field)
            result.update((item["id"], item) for item in items)
    if any(edge["from"] not in nodes or edge["to"] not in nodes for edge in edges.values()):
        raise ValueError("Graph contains an unknown relation endpoint")
    return {**model, "nodes": list(nodes.values()), "edges": list(edges.values())}


def concept_targets(view):
    """Return one-hop bindings produced by the validated concept projection.

    This function consumes trusted server context, not a user-supplied mapping.
    Protocol markers and canonical IDs prevent ordinary visual maps from being
    mistaken for implementation links. Native target membership is mandatory.
    """
    projection = view.get("concept_structure") or {}
    if projection.get("schema") != "bo-concept-projection/v1" or projection.get("stage") != "bound":
        return {}
    native = {node["id"] for node in view["model"]["nodes"]}
    concepts = {
        node["id"] for node in projection.get("nodes", []) if node.get("origin") == "concept-design"
    }
    targets = {}
    for edge in projection.get("edges", []):
        start, end = edge.get("from"), edge.get("to")
        if (
            start not in concepts
            or end not in native
            or start == end
            or edge.get("id") != canonical_id("concept-implements", start, end)
            or edge.get("type") != "maps"
            or edge.get("code_relation") != "maps"
            or edge.get("mapping_role") != "implements"
            or edge.get("origin") != "concept-binding"
            or edge.get("evidence_kind") != "binding"
            or edge.get("observed") is not False
        ):
            continue
        targets.setdefault(start, set()).add(end)
    return {key: sorted(value) for key, value in targets.items()}


def _source_index(graph, native):
    """Index exact source ownership once for a potentially large selection."""
    nodes = {node["id"]: node for node in graph["nodes"]}
    reverse = {}
    for edge in graph["edges"]:
        if edge.get("code_relation") != "maps":
            continue
        owner, source = nodes[edge["from"]], nodes[edge["to"]]
        if (
            owner.get("source")
            and owner.get("source") == source.get("source")
            and owner["id"] in native
        ):
            reverse.setdefault(source["id"], []).append(owner["id"])
    return nodes, reverse


def _source_owners(nodes, reverse, native, identity):
    """Locate exact declared source owners; never follow arbitrary graph paths."""
    pending, seen, result = [identity], set(), set()
    while pending:
        key = pending.pop()
        if key in seen or key not in nodes:
            continue
        seen.add(key)
        node = nodes[key]
        if not node.get("code_role"):
            if key in native:
                result.add(key)
            continue
        if node["code_role"] == "endpoint" and node.get("observation_projection") is True:
            for binding in node.get("observation_sources", []):
                owner = native.get(binding.get("node"))
                if (
                    owner
                    and binding.get("method")
                    and binding.get("route")
                    and binding.get("source")
                    and binding["source"] == owner.get("source")
                ):
                    result.add(owner["id"])
            continue
        pending.extend(reverse.get(key, []))
        if node["code_role"] == "reference":
            target = nodes.get(node.get("declaration_id"))
            if target and node.get("source") and target.get("source") == node["source"]:
                pending.append(target["id"])
        if node["code_role"] == "parameter":
            parent = node.get("parent")
            if parent in nodes and nodes[parent].get("code_role") in {"function", "class"}:
                pending.append(parent)
    return result


def capture_owners(view, identities, *, strict=True):
    """Resolve a selection to native IDs, preserving each raw event's identity.

    Several bound functions remain separate owners. This lookup establishes
    neither a combined conceptual lifetime nor business authorization. Static
    nodes without observations can be skipped for replay; focused capture rejects
    them so the user cannot mistake an empty scope for successful recording.
    """
    graph = display_graph(view)
    native = {node["id"]: node for node in view["model"]["nodes"]}
    targets = concept_targets(view)
    nodes, reverse = _source_index(graph, native)
    result = set()
    for identity in identities:
        owners = set()
        if identity in native or identity not in targets:
            owners.update(_source_owners(nodes, reverse, native, identity))
        for target in targets.get(identity, []):
            owners.update(_source_owners(nodes, reverse, native, target))
        if not owners and strict:
            raise ValueError("This node has no capture binding: " + identity)
        result.update(owners)
    return sorted(result)
