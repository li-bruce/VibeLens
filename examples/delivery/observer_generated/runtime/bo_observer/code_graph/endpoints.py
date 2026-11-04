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

    if api.get("registration_id"):
        return api["registration_id"]

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


def assign_endpoint_identities(specifications, identity):
    """Qualify colliding legacy endpoint IDs by their actual source registration.

    Existing handler/method/path IDs survive when unambiguous. Receiver and
    lexical owner distinguish independent registrations; line offsets only order
    otherwise identical repeated statements and never enter the identity hash.
    One old ID splitting into several registrations is explicit migration
    metadata, never an arbitrary alias to the first endpoint or preference edit.
    """
    import json

    physical = {}
    for item in specifications:
        api = item["route"]
        source = api.get("source", {})
        exact = registration_identity(api)
        stable = [
            source.get("path", item["source"]["path"]),
            source.get("symbol", item["source"]["symbol"]),
            api.get("receiver"),
            api.get("framework"),
            api["path"],
            api["methods"],
            api["declaration"],
        ]
        physical.setdefault(
            exact,
            {"stable": stable, "source": source, "sort": json.dumps(stable, sort_keys=True)},
        )
    counts = defaultdict(int)
    registration_ids = {}
    for exact, item in sorted(
        physical.items(),
        key=lambda row: (
            row[1]["sort"],
            row[1]["source"].get("line", 0),
            row[1]["source"].get("column", 0),
        ),
    ):
        occurrence = counts[item["sort"]]
        counts[item["sort"]] += 1
        registration_ids[exact] = identity("registration", [item["stable"], occurrence])
    registrations = defaultdict(set)
    for item in specifications:
        legacy = identity("endpoint", item["legacy_key"])
        item["legacy_id"] = legacy
        item["registration_id"] = registration_ids[registration_identity(item["route"])]
        registrations[legacy].add(item["registration_id"])
    replacements = defaultdict(set)
    for item in specifications:
        legacy = item["legacy_id"]
        item["id"] = (
            legacy
            if len(registrations[legacy]) == 1
            else identity("endpoint", [item["legacy_key"], item["registration_id"]])
        )
        item["route"] = {**item["route"], "registration_id": item["registration_id"]}
        if item["id"] != legacy:
            replacements[legacy].add(item["id"])
    migrations = [
        {
            "legacy_id": legacy,
            "targets": sorted(targets),
            "reason": "independent_source_registrations",
            "resolution": "requires_selection",
        }
        for legacy, targets in sorted(replacements.items())
    ]
    return specifications, migrations


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
