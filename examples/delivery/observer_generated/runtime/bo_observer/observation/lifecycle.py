"""Resolve observed lifecycle boundaries from the same declarations as the viewer.

These meanings describe event boundaries, never a business success verdict.
Data adapters have a fixed vocabulary; projectors register it in the graph JSON.
"""


def data_lifecycle(action):
    """Declare the real entry/exit vocabulary of the native data adapters."""
    states = [
        {"id": "running", "label": "Running", "kind": "active"},
        {"id": "returned", "label": "Returned", "kind": "ended"},
        {"id": "exception", "label": "Exception exit", "kind": "ended"},
    ]
    bindings = [
        {"phase": "enter", "state": "running", "boundary": "start"},
        {"phase": "return", "state": "returned", "boundary": "end"},
        {"phase": "error", "state": "exception", "boundary": "end"},
    ]
    ending = {
        "transaction": ("commit", "committed", "Committed"),
        "transform": ("change", "transformed", "Transformed"),
    }.get(action)
    if ending:
        phase, state, label = ending
        states.append({"id": state, "label": label, "kind": "ended"})
        bindings.append(
            {
                "phase": phase,
                "state": state,
                "boundary": "end",
                "when": {"direction": "out", "field": "status", "equals": state},
            }
        )
    return {"states": states, "bindings": bindings}


def _equal_scalar(value, expected):
    """Match JSON scalars like JavaScript ===, retaining the boolean/number distinction."""
    numeric = type(value) in (int, float) and type(expected) in (int, float)
    return (numeric or type(value) is type(expected)) and value == expected


def lifecycle_transition(node, event):
    """Resolve a registered binding, then the neutral invocation defaults.

    Older data graphs carry action metadata but no lifecycle declaration. Their
    adapter-defined commit/transform exits remain readable without rewriting facts.
    A generic commit/change on another node never becomes an invocation exit.
    """
    if event.get("context_only") is True:
        boundary = event.get("context_boundary")
        if boundary in {"start", "end"}:
            return {
                "boundary": boundary,
                "state": (
                    "running"
                    if boundary == "start"
                    else "exception" if event.get("phase") == "error" else "returned"
                ),
                "registered": False,
                "context_only": True,
            }
    definition = node.get("lifecycle") or {}
    for binding in definition.get("bindings", []):
        if binding["phase"] != event.get("phase"):
            continue
        selector = binding.get("when")
        if selector:
            values = event.get("inputs" if selector["direction"] == "in" else "outputs", {})
            if selector["field"] not in values or not _equal_scalar(
                values[selector["field"]], selector["equals"]
            ):
                continue
        return {"boundary": binding["boundary"], "state": binding["state"], "registered": True}
    phase = event.get("phase")
    action = node.get("data_metadata", {}).get("action")
    old_data_exit = (
        node.get("data_role") == "query"
        and action == "transaction"
        and phase == "commit"
        and event.get("outputs", {}).get("status") == "committed"
    ) or (
        node.get("data_role") == "transform"
        and phase == "change"
        and event.get("outputs", {}).get("status") == "transformed"
    )
    if not definition and old_data_exit:
        return {"boundary": "end", "state": event["outputs"]["status"], "registered": False}
    fallback = {
        "enter": ("start", "running"),
        "wait": ("update", "waiting"),
        "read": ("update", "running"),
        "return": ("end", "returned"),
        "error": ("end", "exception"),
    }.get(phase)
    return (
        {"boundary": fallback[0], "state": fallback[1], "registered": False} if fallback else None
    )
