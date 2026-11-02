"""Validate explicit invocation-entry references without changing observed facts.

File/entity identity and request ownership are separate. A parent call ID alone
retains its old scoped meaning; an explicit entry ID can link different entities.
"""


def parent_references(events, *, complete=False):
    """Check only supplied entry references; missing legacy ownership stays unknown."""
    by_id = {event.get("id"): event for event in events if event.get("id")}
    errors, gaps, checked = [], [], 0
    for event in events:
        reference = event.get("parent_event_id")
        if reference is None:
            continue
        checked += 1
        problem = None
        if not isinstance(reference, str) or not reference or len(reference) > 512:
            problem = "invalid parent entry identity"
        elif reference == event.get("id"):
            problem = "an event cannot parent itself"
        elif reference not in by_id:
            gap = {"event": event.get("id"), "missing_parent_entry": reference}
            (errors if complete else gaps).append(gap)
            continue
        else:
            parent = by_id[reference]
            if parent.get("phase") != "enter" or not parent.get("call_id"):
                problem = "parent reference must target an invocation entry"
            elif any(
                parent.get(key) != event.get(key)
                for key in ("project_id", "build_id", "model_revision")
            ):
                problem = "parent entry belongs to another project, build or model"
            elif event.get("parent_call_id") not in (None, parent["call_id"]):
                problem = "parent entry and parent call identities disagree"
            elif (parent.get("producer_id"), parent.get("run_id")) == (
                event.get("producer_id"),
                event.get("run_id"),
            ):
                before, after = parent.get("seq"), event.get("seq")
                if type(before) is int and type(after) is int and before >= after:
                    problem = "parent entry does not precede its observation"
        if problem:
            errors.append({"event": event.get("id"), "parent_entry_error": problem})
    # Explicit cross-producer references have no shared sequence counter. Their
    # entry graph must still be acyclic; do not compare wall clocks to guess it.
    settled = set()
    for identity in by_id:
        path = set()
        current = identity
        while current in by_id and current not in settled:
            if current in path:
                errors.append({"event": current, "parent_entry_error": "cyclic parent entries"})
                break
            path.add(current)
            reference = by_id[current].get("parent_event_id")
            if not isinstance(reference, str):
                break
            current = reference
        settled.update(path)
    return {"valid": not errors, "checked": checked, "errors": errors, "gaps": gaps}


def observation_ownership(events, model):
    """Require internal point facts to belong to a witnessed invocation.

    Entry events establish real root calls. A source-bound external notification
    may instead declare ``observation_root`` on its node. File IDs, static graph
    edges and wall-clock proximity never substitute for runtime ownership.
    """
    from .lifecycle import lifecycle_transition

    nodes = {node["id"]: node for node in model.get("nodes", [])}
    by_id = {event.get("id"): event for event in events if event.get("id")}
    active, active_entries = {}, set()
    errors, assigned, roots = [], 0, 0

    def scope(event):
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
            )
        )

    # Producer sequence orders local entries and exits, even if delivery groups
    # arrive out of order. Different producers have no shared sequence clock.
    ordered = sorted(
        enumerate(events),
        key=lambda item: (
            str(item[1].get("producer_id", "")),
            str(item[1].get("run_id", "")),
            item[1].get("seq") if type(item[1].get("seq")) is int else item[0],
        ),
    )
    for _, event in ordered:
        phase = event.get("phase")
        node = nodes.get(event.get("node"), {})
        local_scope = scope(event)
        key = (local_scope, event.get("node"), event.get("call_id"))
        parent = by_id.get(event.get("parent_event_id"))
        owned = key in active
        if parent is not None:
            same_producer = all(
                event.get(field) == parent.get(field) for field in ("producer_id", "run_id")
            )
            # Causal children may start or finish after their parent completes.
            # A bare late point cannot borrow an ended parent's lifetime.
            if (
                same_producer
                and parent.get("id") not in active_entries
                and not (owned or phase == "enter")
            ):
                errors.append({"event": event.get("id"), "inactive_parent_entry": parent.get("id")})
            owned = True  # Reference identity/type/cycles are checked separately.
        elif event.get("parent_call_id"):
            matches = [
                entry
                for (entry_scope, _, call), entry in active.items()
                if entry_scope == local_scope and call == event["parent_call_id"]
            ]
            owned = owned or len(matches) == 1
        if phase == "enter":
            if not owned and event.get("parent_call_id"):
                errors.append(
                    {"event": event.get("id"), "missing_parent_call": event["parent_call_id"]}
                )
            active[key] = event
            active_entries.add(event.get("id"))
            roots += int(not owned and not event.get("parent_call_id"))
        elif not owned:
            if node.get("observation_root") is True and not (
                event.get("parent_call_id") or event.get("parent_event_id")
            ):
                roots += 1
            else:
                errors.append(
                    {
                        "event": event.get("id"),
                        "node": event.get("node"),
                        "missing_observation_owner": True,
                    }
                )
        else:
            assigned += 1
        boundary = (
            {"return": "end", "error": "end"}.get(phase)
            if event.get("lifecycle") == "span"
            else (lifecycle_transition(node, event) or {}).get("boundary")
        )
        if boundary == "end" and key in active:
            active_entries.discard(active.pop(key).get("id"))
    return {"valid": not errors, "assigned": assigned, "roots": roots, "errors": errors}
