"""Join the physical containment tree to source declarations and dependencies."""

from pathlib import PurePosixPath


def attach_tree(project, nodes, edge, identity):
    """Retain existing file IDs and add one parent per physical directory/file."""
    for path, fact in project["entries"].items():
        role = "directory" if fact["kind"] == "directory" else "file"
        key = identity(role, path)
        value = nodes.setdefault(
            key,
            {
                "id": key,
                "label": PurePosixPath(path).name if path != "." else "Project",
                "kind": "data",
                "code_role": role,
                "origin": "code-index",
            },
        )
        value.update(layer="project", project_path=path, project_kind=fact["kind"])
        value["label"] = PurePosixPath(path).name if path != "." else "Project"
        value["summary"] = path if path != "." else ""
        if "bytes" in fact:
            value["file_bytes"] = fact["bytes"]
        if path != ".":
            value["parent"] = identity("directory", PurePosixPath(path).parent.as_posix())
            edge(value["parent"], key, "contains", "Contains")
        target = fact.get("target")
        if target and target in project["entries"]:
            target_role = (
                "directory" if project["entries"][target]["kind"] == "directory" else "file"
            )
            edge(key, identity(target_role, target), "links", "File link")


def analyze(nodes, edges):
    """Count distinct file dependencies and find cycles without recursion limits.

    Counts are static structure metrics, not runtime activity or an architecture
    quality verdict. Directory totals roll up descendant files only once.
    """
    files = {key for key, value in nodes.items() if value.get("code_role") == "file"}
    outgoing = {key: set() for key in files}
    incoming = {key: set() for key in files}
    for relation in edges:
        a, b = relation["from"], relation["to"]
        if relation["code_relation"] not in {"imports", "exports", "references"}:
            continue
        if a in files and b in files and a != b:
            outgoing[a].add(b)
            incoming[b].add(a)
    # Kosaraju's two iterative passes avoid Python's recursion limit on large repos.
    visited, order = set(), []
    for start in sorted(files):
        if start in visited:
            continue
        visited.add(start)
        stack = [(start, iter(sorted(outgoing[start])))]
        while stack:
            current, children = stack[-1]
            child = next(children, None)
            if child is None:
                order.append(current)
                stack.pop()
            elif child not in visited:
                visited.add(child)
                stack.append((child, iter(sorted(outgoing[child]))))
    visited, cycles = set(), []
    for start in reversed(order):
        if start in visited:
            continue
        stack, component = [start], []
        visited.add(start)
        while stack:
            current = stack.pop()
            component.append(current)
            for child in sorted(incoming[current]):
                if child not in visited:
                    visited.add(child)
                    stack.append(child)
        if len(component) > 1:
            cycles.append(sorted(component))
    for key in files:
        nodes[key]["project_metrics"] = {
            "imports": len(outgoing[key]),
            "imported_by": len(incoming[key]),
        }
    for component in cycles:
        for key in component:
            nodes[key]["project_cycle"] = component[0]
    totals = {}
    for key in files:
        parent = nodes[key].get("parent")
        while parent:
            totals[parent] = totals.get(parent, 0) + 1
            parent = nodes[parent].get("parent")
    for key, total in totals.items():
        nodes[key]["project_metrics"] = {"files": total}
    return {"file_cycles": sorted(cycles), "file_dependencies": sum(map(len, outgoing.values()))}
