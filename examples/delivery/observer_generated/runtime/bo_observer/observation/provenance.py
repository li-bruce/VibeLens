"""Optional execution metadata, distinct from graph definitions and business truth.

OTel supplies execution identities. Qualified object references borrow the useful
distinction between activities, objects and actors from PROV/OCEL. They neither
authorize actions nor infer causal links from objects that happen to be equal.
"""

from copy import deepcopy
import re


def _identity(value, name, limit=256):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"invalid {name}")
    return value


def _hex(value, size, name):
    if not isinstance(value, str) or not re.fullmatch(f"[0-9a-f]{{{size}}}", value):
        raise ValueError(f"invalid {name}")
    if not int(value, 16):
        raise ValueError(f"zero {name}")


def trace_metadata(value):
    """Validate a copied SDK SpanContext; this JSON is not an OTLP envelope."""
    if not isinstance(value, dict) or set(value) - {
        "trace_id",
        "span_id",
        "parent_span_id",
        "trace_flags",
        "tracestate",
        "links",
    }:
        raise ValueError("invalid trace metadata fields")
    _hex(value.get("trace_id"), 32, "trace ID")
    _hex(value.get("span_id"), 16, "span ID")
    parent = value.get("parent_span_id")
    if parent is not None:
        _hex(parent, 16, "parent span ID")
        if parent == value["span_id"]:
            raise ValueError("span cannot parent itself")
    if type(value.get("trace_flags")) is not int or not 0 <= value["trace_flags"] <= 255:
        raise ValueError("invalid trace flags")
    if "tracestate" in value and (
        not isinstance(value["tracestate"], str) or len(value["tracestate"]) > 512
    ):
        raise ValueError("invalid tracestate")
    links = value.get("links", [])
    if not isinstance(links, list) or len(links) > 32:
        raise ValueError("trace links exceed bound")
    for link in links:
        if not isinstance(link, dict) or set(link) - {
            "trace_id",
            "span_id",
            "relation",
            "source_build_id",
        }:
            raise ValueError("invalid span link")
        _hex(link.get("trace_id"), 32, "linked trace ID")
        _hex(link.get("span_id"), 16, "linked span ID")
        if "source_build_id" in link:
            _identity(link["source_build_id"], "source build identity")
        if link.get("relation", "trigger") not in {"trigger", "data", "control", "recheck"}:
            raise ValueError("invalid link relation")
        if (link["trace_id"], link["span_id"]) == (value["trace_id"], value["span_id"]):
            raise ValueError("span cannot link to itself")
    return deepcopy(value)


def object_metadata(value):
    """Keep explicitly supplied business references; never read identity from headers."""
    if not isinstance(value, dict) or set(value) - {"workflow_id", "objects", "actor"}:
        raise ValueError("invalid provenance fields")
    if "workflow_id" in value:
        _identity(value["workflow_id"], "workflow identity")
    objects = value.get("objects", [])
    if not isinstance(objects, list) or len(objects) > 64:
        raise ValueError("object references exceed bound")
    seen = set()
    for item in objects:
        if not isinstance(item, dict) or set(item) - {"id", "type", "role", "version"}:
            raise ValueError("invalid object reference")
        for key in ("id", "type", "role"):
            _identity(item.get(key), f"object {key}")
        if "version" in item:
            _identity(item["version"], "object version")
        key = tuple(item.get(field) for field in ("type", "id", "version", "role"))
        if key in seen:
            raise ValueError("duplicate qualified object reference")
        seen.add(key)
    if "actor" in value and value["actor"] is not None:
        actor = value["actor"]
        if not isinstance(actor, dict) or set(actor) != {"id", "kind"}:
            raise ValueError("invalid actor reference")
        _identity(actor["id"], "actor identity")
        if actor["kind"] not in {"user", "service"}:
            raise ValueError("invalid actor kind")
    return deepcopy(value)


def exception_metadata(value):
    """Retain the physical exception class only, without messages or business verdicts."""
    if not isinstance(value, dict) or set(value) != {"type"}:
        raise ValueError("invalid exception metadata fields")
    name = _identity(value["type"], "exception type")
    if any(not part.replace("$", "_").isidentifier() for part in name.split(".")):
        raise ValueError("exception type must identify a code class")
    return deepcopy(value)


def trace_references(events):
    """Check explicit trace/call consistency and causal cycles, without clock inference.

    Unmapped SDK spans may be technical library work outside the selected graph.
    Their IDs are reported separately and cannot manufacture an observation owner.
    """
    errors, spans, calls, parents, causes = [], {}, {}, {}, {}
    by_id = {event.get("id"): event for event in events}
    for event in events:
        trace = event.get("trace")
        try:
            if trace is not None:
                trace_metadata(trace)
            if "provenance" in event:
                object_metadata(event["provenance"])
            if "exception" in event:
                exception_metadata(event["exception"])
        except ValueError as error:
            errors.append({"event": event.get("id"), "trace_error": str(error)})
            continue
        if trace is None:
            continue
        span = (trace["trace_id"], trace["span_id"])
        parent = trace.get("parent_span_id")
        if span in parents and parents[span] != parent:
            errors.append({"event": event.get("id"), "trace_error": "conflicting span parent"})
        parents[span] = parent
        spans[span] = True
        causes.setdefault(span, set()).update(
            (link["trace_id"], link["span_id"]) for link in trace.get("links", [])
        )
        if parent:
            causes[span].add((trace["trace_id"], parent))
        if event.get("lifecycle") == "span":
            call = tuple(
                event.get(k)
                for k in (
                    "build_id",
                    "run_id",
                    "producer_id",
                    "entity",
                    "attempt",
                    "node",
                    "call_id",
                )
            )
            if call in calls and calls[call] != span:
                errors.append(
                    {"event": event.get("id"), "trace_error": "call changed span identity"}
                )
            calls[call] = span
        owner = by_id.get(event.get("parent_event_id"), {}).get("trace")
        if owner and owner["trace_id"] != trace["trace_id"]:
            errors.append(
                {"event": event.get("id"), "trace_error": "parent call belongs to another trace"}
            )
    settled = set()
    for span in parents:
        path, current = set(), span
        while current in parents and current not in settled:
            if current in path:
                errors.append({"trace_error": "cyclic span parents", "span": current})
                break
            path.add(current)
            current = (current[0], parents[current])
        settled.update(path)
    external = sorted(
        {
            (trace, parent)
            for (trace, _), parent in parents.items()
            if parent and (trace, parent) not in spans
        }
    )
    # Links can have several causes. Iterative DFS avoids recursion limits for
    # long recordings and checks cycles across both parent and linked executions.
    colors = {}
    for origin in causes:
        if colors.get(origin) == 2:
            continue
        colors[origin] = 1
        stack = [(origin, iter(causes.get(origin, ())))]
        while stack:
            current, children = stack[-1]
            child = next(children, None)
            if child is None:
                colors[current] = 2
                stack.pop()
            elif colors.get(child) == 1:
                errors.append({"trace_error": "cyclic span causality", "span": list(child)})
            elif colors.get(child) != 2:
                colors[child] = 1
                stack.append((child, iter(causes.get(child, ()))))
    return {
        "valid": not errors,
        "spans": len(spans),
        "errors": errors,
        "external_parent_spans": [list(item) for item in external],
        "external_link_spans": [
            list(item)
            for item in sorted(
                {
                    (link["trace_id"], link["span_id"])
                    for event in events
                    for link in event.get("trace", {}).get("links", [])
                    if (link["trace_id"], link["span_id"]) not in spans
                }
            )
        ],
    }


def admission_reference(event, seen):
    """Reject known invalid entry references before the session publishes an event.

    An absent parent can arrive from another producer later; complete recording
    and acceptance checks still require its explicit witness. Never invent it.
    """
    reference = event.get("parent_event_id")
    if reference == event["id"]:
        raise ValueError("event cannot parent itself")
    parent = seen.get(reference)
    if parent:
        if parent.get("phase") != "enter" or not parent.get("call_id"):
            raise ValueError("parent reference must target an invocation entry")
        if event.get("parent_call_id") not in (None, parent["call_id"]):
            raise ValueError("parent entry and call identity disagree")
    visited = set()
    while reference in seen and reference not in visited:
        visited.add(reference)
        reference = seen[reference].get("parent_event_id")
        if reference == event["id"]:
            raise ValueError("cyclic parent entries")


def export_provenance(events):
    """Export explicit event/object/actor relations without merging execution instances."""
    checked = trace_references(events)
    if not checked["valid"]:
        raise ValueError("invalid execution provenance")
    objects, relations = {}, []
    for event in events:
        provenance = object_metadata(event.get("provenance", {}))
        for item in provenance.get("objects", []):
            key = tuple(item.get(field) for field in ("type", "id", "version"))
            objects[key] = {k: v for k, v in item.items() if k != "role"}
            relations.append({"event": event["id"], "object": objects[key], "role": item["role"]})
    return {
        "protocol": "bo-provenance/v1",
        "events": deepcopy(events),
        "objects": list(objects.values()),
        "event_objects": relations,
        "trace_check": checked,
    }
