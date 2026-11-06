"""Resolve viewer-only fields and states from existing declarations, never request data."""

from urllib.parse import quote


def resolve_derived(graph, identity):
    """Materialize only the requested field/state and its declared ownership path."""
    nodes, edges = {}, []

    def field(owner, direction, key, spec, path=(), parent=None):
        parent = parent or owner["id"]
        ident = f"field:{owner['id']}:{direction}:{key}" + "".join(
            ":" + quote(part, safe="~()*!.'-") for part in path
        )
        if identity != ident and not identity.startswith(ident + ":"):
            return
        nodes[ident] = {
            "id": ident,
            "label": path[-1] if path else key,
            "kind": "data",
            "layer": "rules" if owner.get("policy_node") else "implementation",
            "origin": "capture-field",
            "field": key,
            "field_path": list(path),
            "direction": direction,
            "value_type": spec,
            "event_node": owner["id"],
            "summary": "Registered event field, not necessarily a lexical source variable",
        }
        edges.append(
            {
                "id": "capture:" + ident,
                "from": ident if direction == "in" else parent,
                "to": parent if direction == "in" else ident,
                "type": "data",
                "label": "Recorded input" if direction == "in" else "Recorded output",
            }
        )
        if isinstance(spec, dict):
            for name, child in spec.items():
                field(owner, direction, key, child, (*path, name), ident)

    for node in graph["nodes"]:
        if identity.startswith("field:" + node["id"] + ":"):
            for direction, fields in node.get("capture", {}).items():
                for key, spec in fields.items():
                    field(node, direction, key, spec)
    machine = graph.get("machine", {})
    for value in machine.get("values", []):
        if identity == "state." + value:
            nodes[identity] = {
                "id": identity,
                "kind": "state",
                "layer": "state",
                "value": value,
                "label": machine.get("labels", {}).get(value, value),
            }
    return list(nodes.values()), edges
