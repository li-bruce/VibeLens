"""Layer-specific observation requirements derived from the project's existing contracts.

The implementation inventory remains authoritative. This module audits invocation
boundaries and publishes a readable plan; it does not maintain a second graph.
"""

from __future__ import annotations

import ast
from collections import defaultdict

from ..graph.classification import classify, layer_of

LAYER_CHECKS = {
    "business": ("feature entrypoints and effects", "actual invocation and selected result"),
    "state": (
        "state declarations, identities, resources and waits",
        "actual transitions, residence and activity evidence",
    ),
    "rules": (
        "predicate sources, arguments and shared dependencies",
        "evaluated/skipped conditions and actual enclosing invocation",
    ),
    "implementation": (
        "routes, source hierarchy, declarations, parameters and data-access bindings",
        "actual calls, responses, selected values and native transaction boundaries; unobserved declarations remain static",
    ),
    "data": ("ORM/ODM/schema metadata and relationships", "operation-linked structural projection"),
    "unknown": ("unclassified declarations requiring a mapping review", "no inferred evidence"),
}


def observation_plan(model, index):
    """List exact sources, fields and cases per layer for each coding iteration."""
    features = (model.get("implementation") or {}).get("features", [])
    by_node = defaultdict(list)
    for feature in features:
        for node in feature.get("nodes", []):
            by_node[node].append(feature)
    grouped = {layer: [] for layer in LAYER_CHECKS}
    for node in model.get("nodes", []):
        obligations = by_node[node["id"]]
        grouped[layer_of(node)].append(
            {
                "node": node["id"],
                "facet": classify(node)["facet"],
                "source": node.get("source"),
                "fields": node.get("capture", {}),
                "lifecycle": node.get("lifecycle"),
                "observation_root": node.get("observation_root", False),
                "features": [feature["id"] for feature in obligations],
                "cases": [
                    case
                    for feature in obligations
                    for case in feature.get("cases", [])
                    if case.get("node") == node["id"]
                ],
            }
        )
    return {
        "schema": "bo-observation-plan/v1",
        "layers": {
            layer: {"scan": checks[0], "observe": checks[1], "nodes": grouped[layer]}
            for layer, checks in LAYER_CHECKS.items()
        },
        "unresolved_calls": index.get("unresolved", []),
    }


def probe_sites(index, cfg):
    """Recognize configured record and span APIs without executing application code.

    A span declares entry, normal return and exception exit sites. Runtime cases
    must still establish which boundary and selected values actually occurred.
    """
    sites = []
    callees = cfg.get("probe_callees", ["trace.record"])
    for symbol in index.get("symbols", {}).values():
        for call in symbol.get("calls", []):
            if call["expression"] not in callees:
                continue
            if call.get("span_node"):
                nodes_phases = [
                    (call["span_node"], phase) for phase in ("enter", "return", "error")
                ]
            elif call.get("literal_pair"):
                nodes_phases = [call["literal_pair"]]
            else:
                continue
            sites.extend(
                {"symbol": symbol["id"], "node": node, "phase": phase}
                for node, phase in nodes_phases
            )
    return sites


def layer_evidence(model, payload):
    """Report direct evidence by layer without calling static projections unobserved bugs."""
    grouped = observation_plan(model, {})["layers"]
    events = [
        event
        for run in payload.get("runs", [])
        if run.get("mode") == "on"
        for event in run.get("events", [])
    ]
    observed = {event.get("node") for event in events if not event.get("context_only")}
    boundaries = {event.get("node") for event in events if event.get("context_only")}
    return {
        layer: {
            "declared_nodes": len(group["nodes"]),
            "direct_observations": sorted(
                node["node"] for node in group["nodes"] if node["node"] in observed
            ),
            "required_cases": sum(len(node["cases"]) for node in group["nodes"]),
            "boundary_observations": sorted(
                node["node"] for node in group["nodes"] if node["node"] in boundaries
            ),
            "basis": group["observe"],
        }
        for layer, group in grouped.items()
    }


def deferred_builder_errors(root, model):
    """Find deferred probe results that reference a cleared Python exception target.

    Limit inspection to mapped application sources and the probe result API. A
    normal immediate lambda or a default-bound scalar is not this failure mode.
    """
    errors = []
    node_ids = {node["id"] for node in model.get("nodes", [])}
    paths = {
        node["source"]["path"]
        for node in model.get("nodes", [])
        if node.get("source", {}).get("path", "").endswith(".py")
    }
    from ..graph.behavior_model import contained

    for path in sorted(paths):
        try:
            tree = ast.parse(contained(root, path).read_text(encoding="utf-8-sig"), filename=path)
        except (OSError, SyntaxError, ValueError) as error:
            errors.append({"observation_source_unreadable": path, "error": str(error)})
            continue
        seen = set()
        for handler, call in span_results(tree, node_ids):
            if handler.name and call.lineno not in seen:
                for builder in call.args:
                    if not isinstance(builder, ast.Lambda):
                        continue
                    bound = {arg.arg for arg in [*builder.args.args, *builder.args.kwonlyargs]}
                    if handler.name not in bound and any(
                        isinstance(item, ast.Name) and item.id == handler.name
                        for item in ast.walk(builder.body)
                    ):
                        errors.append(
                            {
                                "unsafe_deferred_probe_result": path,
                                "line": builder.lineno,
                                "exception_target": handler.name,
                                "action": "bind the selected scalar before leaving the exception handler",
                            }
                        )
                        seen.add(call.lineno)
    return errors


def span_results(tree, node_ids):
    """Restrict deferred-result inspection to a known node's span activation."""
    for scope in ast.walk(tree):
        if not isinstance(scope, (ast.With, ast.AsyncWith)):
            continue
        names = set()
        for item in scope.items:
            expr = item.context_expr
            if (
                isinstance(item.optional_vars, ast.Name)
                and isinstance(expr, ast.Call)
                and isinstance(expr.func, ast.Attribute)
                and expr.func.attr == "span"
                and expr.args
                and isinstance(expr.args[0], ast.Constant)
                and expr.args[0].value in node_ids
            ):
                names.add(item.optional_vars.id)
        if not names:
            continue
        for handler in (item for item in ast.walk(scope) if isinstance(item, ast.ExceptHandler)):
            for call in (item for item in ast.walk(handler) if isinstance(item, ast.Call)):
                if (
                    isinstance(call.func, ast.Attribute)
                    and call.func.attr == "result"
                    and isinstance(call.func.value, ast.Name)
                    and call.func.value.id in names
                ):
                    yield handler, call


def invocation_closure(payload, *, required=False, model=None):
    """Audit actual call pairs; a correct HTTP result does not close a missing span.

    Registered state lifetimes may remain open. Calls use neutral enter/return/
    error boundaries. Cross-producer arrival order cannot establish ownership.
    """
    from ..observation.lifecycle import lifecycle_transition
    from ..observation.ownership import observation_ownership, parent_references
    from ..observation.provenance import trace_references

    errors, checked, legacy = [], 0, 0
    nodes = {node["id"]: node for node in (model or {}).get("nodes", [])}
    for run in payload.get("runs", []):
        if run.get("mode") != "on":
            continue
        lineage = parent_references(run.get("events", []), complete=True)
        errors.extend({**error, "case": run.get("case")} for error in lineage["errors"])
        tracing = trace_references(run.get("events", []))
        errors.extend({**error, "case": run.get("case")} for error in tracing["errors"])
        if required:
            errors.extend(
                {
                    "case": run.get("case"),
                    "event": event.get("id"),
                    "partial_boundary_in_complete_run": True,
                }
                for event in run.get("events", [])
                if event.get("context_only") is True
            )
            ownership = observation_ownership(run.get("events", []), model or {})
            errors.extend({**error, "case": run.get("case")} for error in ownership["errors"])
        opened = {}
        for event in run.get("events", []):
            phase = event.get("phase")
            explicit = event.get("lifecycle") == "span"
            if not required and not explicit:
                legacy += int(phase in {"enter", "return", "error"})
                continue
            node = nodes.get(event.get("node"), {})
            # A physical span closes at its actual return/exception. A commit
            # inside that span may precede later work and is not a return.
            boundary = (
                {"enter": "start", "return": "end", "error": "end"}.get(phase)
                if explicit
                else (lifecycle_transition(node, event) or {}).get("boundary")
            )
            if boundary not in {"start", "end"}:
                continue
            if boundary == "start" and phase != "enter":
                continue
            # Value/state residence can start at change/decision and remain open.
            # This audit covers invocation intervals, not those semantic periods.
            if phase not in {"enter", "return", "error"} and node.get("lifecycle"):
                if not any(
                    binding["phase"] == "enter" and binding["boundary"] == "start"
                    for binding in node["lifecycle"]["bindings"]
                ):
                    continue
            identity = tuple(
                event.get(key)
                for key in (
                    "build_id",
                    "run_id",
                    "producer_id",
                    "stream_id",
                    "entity",
                    "attempt",
                    "node",
                    "call_id",
                )
            )
            if not event.get("call_id"):
                errors.append(
                    {"invocation_without_call_id": event.get("id"), "case": run.get("case")}
                )
                continue
            if boundary == "start":
                if identity in opened:
                    errors.append(
                        {"overlapping_invocation": event.get("id"), "case": run.get("case")}
                    )
                opened[identity] = event
            elif identity not in opened:
                errors.append(
                    {"invocation_without_entry": event.get("id"), "case": run.get("case")}
                )
            else:
                checked += 1
                del opened[identity]
        for entry in opened.values():
            errors.append(
                {
                    "invocation_without_exit": entry.get("id"),
                    "node": entry.get("node"),
                    "case": run.get("case"),
                    "call_id": entry.get("call_id"),
                }
            )
    if required and not checked:
        errors.append("no closed invocation was provided by enabled observation runs")
    return {"valid": not errors, "closed_calls": checked, "legacy_events": legacy, "errors": errors}
