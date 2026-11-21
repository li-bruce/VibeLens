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


def _retain_witnesses(events, selected, model):
    """Close selected facts over witnessed invocation boundaries, not value history.

    An entry's identity distinguishes consecutive uses of a call ID. Ends are
    associated in source order, so an old completed ancestor does not become a
    fictitious open invocation. Explicit missing entry IDs never fall back to a
    different invocation that happens to reuse its call ID.
    """
    nodes = {node["id"]: node for node in model["nodes"]}
    by_id = {event["id"]: event for event in events}
    active, groups, owners, parents = {}, {}, {}, {}
    for event in sorted(by_id.values(), key=lambda item: item["seq"]):
        key = call_key(event)
        group = (*key[:-2], key[-1])
        parent = by_id.get(event.get("parent_event_id"))
        if not event.get("parent_event_id") and event.get("parent_call_id"):
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
    needed, queue = set(), [by_id[identity] for identity in selected if identity in by_id]
    while queue:
        event = queue.pop()
        own = owners.get(event["id"])
        parent = parents.get(event["id"])
        for entry in (own, parent):
            if entry is not None and entry.get("phase") == "enter" and entry["id"] not in needed:
                needed.add(entry["id"])
                queue.append(entry)

    retained = []
    for event in by_id.values():
        if event["id"] in selected:
            retained.append(event)
        elif (owners.get(event["id"]) or {}).get("id") in needed:
            header = minimal_boundary(event, nodes.get(event["node"], {}))
            if header:
                retained.append(header)
    return sorted(retained, key=lambda event: event["seq"])


def recording_context(events, opened, model, *, limit=2000):
    """Return recent values with their ancestry, plus bounded boundary candidates.

    Values retain the existing recent-event limit. Older available events provide
    only entry/exit metadata. Candidates stay private to this recording so a later
    asynchronous child can reference a caller completed before recording began.
    Both lists are bounded by the already bounded history/open-invocation caches;
    this function neither increases those caches nor reads more source history.
    """
    nodes = {node["id"]: node for node in model["nodes"]}
    recent = {event["id"] for event in events[-limit:]}
    selected = recent | {event["id"] for event in opened}
    available = {event["id"]: event for event in [*opened, *events]}
    candidates = []
    for event in available.values():
        value = (
            event
            if event["id"] in recent
            else minimal_boundary(event, nodes.get(event["node"], {}))
        )
        if value is not None:
            candidates.append(value)
    candidates.sort(key=lambda event: event["seq"])
    return _retain_witnesses(candidates, selected, model), candidates


def _split_witnesses(events, context, selected, model):
    """Keep original interval membership after selecting the causal closure."""
    kept = _retain_witnesses([*context, *events], selected, model)
    interval_ids = {event["id"] for event in events}
    return (
        [event for event in kept if event["id"] in interval_ids],
        [event for event in kept if event["id"] not in interval_ids],
    )


def retain_recording(events, context, initial_ids, model):
    """Retain every interval fact and only required older invocation metadata."""
    selected = initial_ids | {event["id"] for event in events}
    return _split_witnesses(events, context, selected, model)


def retain_scope(events, context, allowed, model):
    """Keep selected values and their actual ancestor entries/exits across start."""
    selected = {
        event["id"]
        for event in [*context, *events]
        if event["node"] in allowed and not event.get("context_only")
    }
    return _split_witnesses(events, context, selected, model)
