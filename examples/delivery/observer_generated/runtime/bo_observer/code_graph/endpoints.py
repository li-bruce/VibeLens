"""Extract literal HTTP registrations already identified by the source adapters."""

import ast
from collections import defaultdict
from ..observation.observation_scope import observer_route


def endpoints(symbol):
    """Preserve unknown/dynamic routes in source evidence instead of guessing URLs."""
    if "http_endpoints" in symbol:
        # Fresh adapters prove receiver identity. The legacy declaration parser
        # below remains available only for older stored source inventories.
        return [route for route in symbol["http_endpoints"] if not observer_route(route["path"])]
    result = []
    for declaration in symbol.get("entrypoints", []):
        try:
            call = ast.parse(declaration, mode="eval").body
            if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
                continue
            verb = call.func.attr.lower()
            if verb not in {"get", "post", "put", "patch", "delete", "route", "websocket"}:
                continue
            path = (
                call.args[0]
                if call.args
                else next(k.value for k in call.keywords if k.arg == "path")
            )
            if not isinstance(path, ast.Constant) or not isinstance(path.value, str):
                continue
            if observer_route(path.value):
                continue
            methods = [verb.upper()] if verb != "route" else []
            if verb == "route":
                for keyword in call.keywords:
                    if keyword.arg == "methods":
                        value = ast.literal_eval(keyword.value)
                        if isinstance(value, (list, tuple)) and all(
                            isinstance(v, str) for v in value
                        ):
                            methods = [v.upper() for v in value]
            # A route decorator can use framework-specific defaults; do not assume GET.
            result.append({"path": path.value, "methods": methods, "declaration": declaration})
        except (SyntaxError, ValueError, TypeError, StopIteration, IndexError):
            continue
    return result


def registration_identity(api):
    """Identify a literal registration independently of its handler declarations."""
    import json

    source = api.get("source", {})
    return json.dumps(
        [
            api["path"],
            api["methods"],
            api.get("receiver"),
            api["declaration"],
            {key: source.get(key) for key in ("path", "line", "column", "end_line", "end_column")},
        ],
        sort_keys=True,
    )


def combine_handler_registrations(nodes, edges, bindings):
    """One literal middleware registration has one endpoint and several handlers.

    Preserve the first existing endpoint identity. Retired duplicate identities
    and their exact bindings remain explicit migration evidence; preferences on
    those IDs stay dormant and are never merged or overwritten automatically.
    Independent declarations are distinguished by their full registration range.
    """
    groups = defaultdict(list)
    for node in nodes.values():
        api = node.get("api", {})
        source = api.get("source")
        if node.get("code_role") != "endpoint" or not source:
            continue
        key = registration_identity(api)
        groups[key].append(node["id"])
    aliases = {}
    for ids in groups.values():
        if len(ids) < 2:
            continue
        primary = nodes[ids[0]]
        # The first middleware's comment does not describe the whole route.
        # Keep its HTTP identity and expose every handler explanation separately.
        primary["summary"] = ""
        primary["api"]["registration_ids"] = ids
        primary["api"]["registration_bindings"] = {
            key: {**nodes[key]["source"], "documentation": nodes[key].get("documentation")}
            for key in ids
        }
        for retired in ids[1:]:
            aliases[retired] = primary["id"]
            del nodes[retired]
            bindings.pop(retired, None)
    for edge in edges:
        edge["from"] = aliases.get(edge["from"], edge["from"])
        edge["to"] = aliases.get(edge["to"], edge["to"])
    return aliases
