"""Bounded code neighborhoods with exact endpoints and explicit omitted content."""

from collections import deque
from copy import deepcopy
from .index import identity


def anchors(model, graph, focus):
    """Find source anchors below the chosen authored node, without guessing names."""
    authored = {n["id"]: n for n in model.get("nodes", [])}
    code = {n["id"]: n for n in graph["nodes"]}
    if focus in code:
        return {focus}, []
    if focus not in authored:
        raise ValueError("Select an existing graph node for a code neighborhood")
    children = {}
    for n in authored.values():
        children.setdefault(n.get("parent"), []).append(n["id"])
    pending, selected, links = deque([focus]), set(), []
    seen = set()
    while pending:
        key = pending.popleft()
        if key in seen:
            continue
        seen.add(key)
        pending.extend(children.get(key, []))
        source = authored[key].get("source", {})
        sid = graph["symbols"].get(source.get("path", "") + "::" + source.get("symbol", ""))
        if sid:
            selected.add(sid)
            links.append(
                {
                    "id": identity("binding", [key, sid]),
                    "from": key,
                    "to": sid,
                    "type": "data",
                    "code_relation": "maps",
                    "label": "Source binding",
                    "origin": "code-index",
                }
            )
    return selected, links


def query(graph, model, *, focus=None, depth=1, limit=400, projection="all"):
    """Return a stable slice, preserving truncated relations as named boundaries."""
    if type(depth) is not int or not 0 <= depth <= 3:
        raise ValueError("Code depth must be an integer from 0 to 3")
    if type(limit) is not int or not 1 <= limit <= 5000:
        raise ValueError("Code limit must be an integer from 1 to 5000")
    if projection not in {"all", "project"}:
        raise ValueError("Code projection must be all or project")
    if projection == "project":
        keep = {
            n["id"]
            for n in graph["nodes"]
            if n.get("code_role") in {"directory", "file"} or n.get("reference_scope") == "project"
        }
        graph = {
            **graph,
            "nodes": [n for n in graph["nodes"] if n["id"] in keep],
            "symbols": {
                symbol: identity("file", symbol.split("::", 1)[0])
                for symbol in graph["symbols"]
                if identity("file", symbol.split("::", 1)[0]) in keep
            },
            "edges": [e for e in graph["edges"] if e["from"] in keep and e["to"] in keep],
        }
    nodes = {n["id"]: n for n in graph["nodes"]}
    links = []
    if focus:
        wanted, links = anchors(model, graph, focus)
        # Descend within the selected declaration (a file/class can be a focus).
        queue = deque(sorted(wanted))
        children = {}
        for n in nodes.values():
            children.setdefault(n.get("parent"), []).append(n["id"])
        while queue:
            for key in children.get(queue.popleft(), []):
                if key not in wanted:
                    wanted.add(key)
                    queue.append(key)
        for _ in range(depth):
            current = set(wanted)
            for edge in graph["edges"]:
                if edge["code_relation"] in {
                    "calls",
                    "inherits",
                    "handles",
                    "imports",
                    "exports",
                    "dependency",
                    "links",
                }:
                    if edge["from"] in current or edge["to"] in current:
                        wanted.update((edge["from"], edge["to"]))
        # Context is an ancestor, never a fabricated direct call.
        for key in list(wanted):
            parent = nodes[key].get("parent")
            while parent and parent not in wanted:
                wanted.add(parent)
                parent = nodes[parent].get("parent")
    else:
        wanted = set(nodes)
        # Full code view retains each explicit authored-to-source mapping too.
        for item in model.get("nodes", []):
            source = item.get("source", {})
            sid = graph["symbols"].get(source.get("path", "") + "::" + source.get("symbol", ""))
            if sid:
                links.append(
                    {
                        "id": identity("binding", [item["id"], sid]),
                        "from": item["id"],
                        "to": sid,
                        "type": "data",
                        "code_relation": "maps",
                        "label": "Source binding",
                        "origin": "code-index",
                    }
                )
    ordered = sorted(
        wanted,
        key=lambda k: (
            nodes[k].get("project_path", nodes[k].get("source", {}).get("path", "")),
            nodes[k].get("source", {}).get("line", 0),
            k,
        ),
    )
    selected = set(ordered[:limit])
    result = {key: deepcopy(nodes[key]) for key in ordered[:limit]}
    relations, boundary_count, omitted_edges = [], 0, 0
    for edge in graph["edges"]:
        ends = {edge["from"], edge["to"]}
        if not ends & selected:
            continue
        if len(relations) >= 10000:
            omitted_edges += 1
            continue
        missing = ends - selected
        # Ancestor context must not pull unrelated siblings into a focused tree.
        if focus and edge["code_relation"] == "contains" and edge["to"] not in wanted:
            continue
        # Bound payload size even when one function has thousands of callers.
        if missing and boundary_count + len(missing - result.keys()) > 80:
            omitted_edges += 1
            continue
        for key in missing:
            if key not in result:
                result[key] = {**deepcopy(nodes[key]), "code_boundary": True}
                result[key].pop("parent", None)
                boundary_count += 1
        relations.append(deepcopy(edge))
    for n in result.values():
        if n.get("parent") not in result:
            n.pop("parent", None)
    relations += [e for e in links if e["to"] in result]
    project = graph.get("project", {})
    paths = {n.get("project_path") for n in result.values()}
    entries = {p: fact for p, fact in project.get("entries", {}).items() if p in paths}
    cycles = [cycle for cycle in project.get("file_cycles", []) if set(cycle) <= result.keys()]
    project_summary = {
        "entries": entries,
        "total_entries": len(project.get("entries", {})),
        "omitted_entries": len(project.get("entries", {})) - len(entries),
        "file_dependencies": project.get("file_dependencies", 0),
        "file_cycles": cycles,
        "omitted_file_cycles": len(project.get("file_cycles", [])) - len(cycles),
    }
    return {
        "schema": graph["schema"],
        "revision": graph["revision"],
        "nodes": list(result.values()),
        "edges": relations,
        "bindings": {k: v for k, v in graph["bindings"].items() if k in result},
        "focus": focus,
        "projection": projection,
        "project": project_summary,
        "depth": depth,
        "total_nodes": len(wanted),
        "loaded_nodes": len(selected),
        "boundary_nodes": boundary_count,
        "omitted_nodes": len(wanted) - len(selected),
        "total_edges": len(graph["edges"]),
        "loaded_edges": len(relations),
        "omitted_edges": omitted_edges,
        "errors": graph["errors"],
        "limits": graph["limits"],
        "incremental": graph["incremental"],
        "status": "incomplete" if graph["errors"] else "current",
    }
