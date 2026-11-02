"""Retain witnessed invocation headers without collecting unselected values.

Headers are explicit partial observations, not replacements for full capture.
They keep original event identities, phases and times. Scope extraction follows
actual entry references; labels, entity equality and time never invent a caller.
"""

from .lifecycle import lifecycle_transition


def call_key(event):
    """A call ID can be reused in another producer, stream, entity or node."""
    return tuple(
        event.get(key)
        for key in (
            "project_id",
            "model_revision",
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


def invocation_boundary(event, node):
    """Resolve physical call boundaries, separately from semantic residence."""
    if event.get("context_only") is True:
        return event.get("context_boundary")
    if event.get("lifecycle") == "span":
        return {"enter": "start", "return": "end", "error": "end"}.get(event.get("phase"))
    return (lifecycle_transition(node, event) or {}).get("boundary")


def minimal_boundary(event, node):
    """Project an actual entry/exit to metadata; never evaluate a value builder."""
    boundary = invocation_boundary(event, node)
    if boundary not in {"start", "end"} or (boundary == "start" and event.get("phase") != "enter"):
        return None
    value = {
        **event,
        "context_only": True,
        "context_boundary": boundary,
        "inputs": {},
        "outputs": {},
        "depends": [],
        "basis": {},
    }
    value.pop("revision", None)
    value.pop("provenance", None)
    value.pop("exception", None)
    return value


def context_candidates(events, allowed, model):
    """Bounded pre-recording candidates contain no unselected value payloads."""
    nodes = {node["id"]: node for node in model["nodes"]}
    result = []
    for event in events:
        if event["node"] in allowed and not event.get("context_only"):
            result.append(event)
        else:
            header = minimal_boundary(event, nodes.get(event["node"], {}))
            if header:
                result.append(header)
    return result


def retain_scope(events, context, allowed, model):
    """Keep selected facts and only their actual ancestor entries and exits.

    Context and interval events remain separate so a caller already open at the
    recording boundary has the correct clipped interval. No identity is rewritten.
    """
    nodes = {node["id"]: node for node in model["nodes"]}
    by_id = {event["id"]: event for event in [*context, *events]}
    active, groups, owners, parents = {}, {}, {}, {}
    for event in sorted(by_id.values(), key=lambda item: item["seq"]):
        key = call_key(event)
        group = (*key[:-2], key[-1])
        parent = by_id.get(event.get("parent_event_id"))
        if parent is None and event.get("parent_call_id"):
            # Resolve an explicit scoped call against witnessed open entries.
            matches = groups.get((*key[:-2], event["parent_call_id"]), {})
            parent = next(iter(matches.values())) if len(matches) == 1 else None
        parents[event["id"]] = parent
        if event.get("phase") == "enter":
            active[key] = event
            groups.setdefault(group, {})[key] = event
        owners[event["id"]] = active.get(key)
        if invocation_boundary(event, nodes.get(event["node"], {})) == "end":
            active.pop(key, None)
            groups.get(group, {}).pop(key, None)
    selected = {
        event["id"]
        for event in by_id.values()
        if event["node"] in allowed and not event.get("context_only")
    }
    needed, queue = set(), [by_id[identity] for identity in selected]
    while queue:
        event = queue.pop()
        own = owners.get(event["id"])
        parent = parents.get(event["id"])
        for entry in (own, parent):
            if entry is not None and entry.get("phase") == "enter" and entry["id"] not in needed:
                needed.add(entry["id"])
                queue.append(entry)

    def keep(source):
        retained = []
        for event in source:
            if event["id"] in selected:
                retained.append(event)
            elif (owners.get(event["id"]) or {}).get("id") in needed:
                header = minimal_boundary(event, nodes.get(event["node"], {}))
                if header:
                    retained.append(header)
        return sorted(retained, key=lambda event: event["seq"])

    return keep(events), keep(context)
