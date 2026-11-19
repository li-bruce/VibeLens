"""Validate recorded causal references before joining cross-model witnesses.

Producer sequence orders local facts. Different producers require explicit
references and a common build, not comparable wall clocks or nearby timestamps.
Parent-entry and trace checks remain owned by the existing observation modules.
"""

from collections import defaultdict, deque


def owning_entries(index, entries, event):
    """Resolve the nearest actual invocation, including an entry observing itself."""
    ancestors = index.upstream(event)
    candidates = [entry for entry in entries if entry["id"] in ancestors]
    return [
        entry
        for entry in candidates
        if not any(
            entry["id"] != other["id"] and entry["id"] in index.upstream(other)
            for other in candidates
        )
    ]


def dependency_errors(events):
    """Reject missing, cyclic or locally backwards dependency references."""
    by_id = {e["id"]: e for e in events}
    if len(by_id) != len(events):
        return [{"code": "native_event_identity"}]
    edges, indegree, errors = defaultdict(set), dict.fromkeys(by_id, 0), []
    for event in events:
        refs = [r["event"] for r in event.get("depends", [])]
        if event.get("parent_event_id"):
            refs.append(event["parent_event_id"])
        for ref in set(refs):
            prior = by_id.get(ref)
            if prior is None:
                errors.append(
                    {"code": "native_dependency_missing", "event": event["id"], "reference": ref}
                )
                continue
            local = all(
                prior.get(k) == event.get(k) for k in ("producer_id", "run_id", "stream_id")
            )
            if local and prior["seq"] >= event["seq"]:
                errors.append(
                    {"code": "native_dependency_order", "event": event["id"], "reference": ref}
                )
            if event["id"] not in edges[ref]:
                edges[ref].add(event["id"])
                indegree[event["id"]] += 1
    ready = deque(identity for identity, count in indegree.items() if not count)
    visited = 0
    while ready:
        visited += 1
        for target in edges[ready.popleft()]:
            indegree[target] -= 1
            if not indegree[target]:
                ready.append(target)
    if visited != len(by_id):
        errors.append({"code": "native_dependency_cycle"})
    return errors
