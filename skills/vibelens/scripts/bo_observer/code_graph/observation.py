"""Qualify real HTTP observation sources against exact static registrations.

An endpoint may observe several registered methods. Shared function names and
generic source-map edges are insufficient evidence: method, literal route and
resolved handler must all agree, and the captured node must identify one route.
Original producer events and their invocation/trace identities are never copied.
"""

from collections import defaultdict
from copy import deepcopy
import re

from ..graph.behavior_model import digest
from .endpoints import registration_identity

METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"}


def http_selector(match):
    """Read literal HTTP method/route selectors; conflicting spellings stay unknown."""
    named = re.fullmatch(r"([A-Z]+) (/\S*)", str(match.get("name", "")))
    methods, routes = set(), set()
    if named and named[1] in METHODS:
        methods.add(named[1])
        routes.add(named[2])
    attributes = match.get("attributes", {})
    for key in ("http.method", "http.request.method"):
        if key in attributes:
            methods.add(attributes[key])
    if "http.route" in attributes:
        routes.add(attributes["http.route"])
    if len(methods) != 1 or len(routes) != 1:
        return None
    method, route = next(iter(methods)), next(iter(routes))
    if method not in METHODS or not isinstance(route, str) or not route.startswith("/"):
        return None
    return method, route


def qualify(graph, model, configuration):
    """Attach read-only projection metadata only to uniquely qualified endpoints."""
    result = deepcopy(graph)
    nodes = {node["id"]: node for node in result["nodes"]}
    authored = {node["id"]: node for node in model.get("nodes", [])}
    endpoints = {key: node for key, node in nodes.items() if node.get("code_role") == "endpoint"}
    for node in endpoints.values():
        node["observation_sources"] = []
        node.pop("observation_projection", None)
    registrations = result.get("endpoint_registrations", [])
    candidates, issues, other_selectors = [], [], set()
    for item in (configuration or {}).get("registrations", []):
        owner = authored[item["node"]]
        selector = http_selector(item["match"])
        if owner.get("layer") != "api" and selector is None:
            other_selectors.add(item["node"])
            continue
        if selector is None:
            issues.append({"node": item["node"], "reason": "http_selector_not_route_qualified"})
            continue
        method, route = selector
        source = item["source"]
        symbol = source["path"] + "::" + source["symbol"]
        matching = {}
        for fact in registrations:
            declaration = fact["route"]
            if (
                fact["handler"] != symbol
                or declaration["path"] != route
                or method not in declaration["methods"]
            ):
                continue
            # Middleware entries share this exact source registration; separate
            # routers/calls remain distinct even if an older static ID collided.
            key = registration_identity(declaration)
            matching[key] = fact["endpoint"]
        if len(matching) != 1:
            issues.append(
                {
                    "node": item["node"],
                    "method": method,
                    "route": route,
                    "reason": "http_endpoint_ambiguous" if matching else "http_endpoint_unresolved",
                    "candidates": sorted(set(matching.values())),
                    "registrations": len(matching),
                }
            )
            continue
        target = next(iter(matching.values()))
        if target not in endpoints:
            issues.append({"node": item["node"], "reason": "http_endpoint_missing"})
            continue
        candidates.append(
            (
                target,
                {
                    "node": item["node"],
                    "method": method,
                    "route": route,
                    "source": deepcopy(source),
                    "selector": deepcopy(item["match"]),
                    "capture": deepcopy(owner.get("capture", {})),
                },
            )
        )
    targets = defaultdict(set)
    for target, source in candidates:
        targets[source["node"]].add(target)
    reused = {node for node, selected in targets.items() if len(selected) > 1}
    rejected = {issue["node"] for issue in issues}
    for node in sorted(other_selectors & targets.keys()):
        issues.append({"node": node, "reason": "http_capture_reused_by_unqualified_selector"})
        rejected.add(node)
    for node in sorted(reused):
        issues.append(
            {
                "node": node,
                "reason": "http_capture_reused_across_endpoints",
                "candidates": sorted(targets[node]),
            }
        )
    for target, source in candidates:
        if source["node"] in reused or source["node"] in rejected:
            continue
        endpoint = endpoints[target]
        if source not in endpoint["observation_sources"]:
            endpoint["observation_sources"].append(source)
            endpoint["observation_projection"] = True
    result["observation_issues"] = issues
    result["revision"] = digest(
        [
            graph["revision"],
            [(key, node["observation_sources"]) for key, node in endpoints.items()],
            issues,
        ]
    )
    return result
