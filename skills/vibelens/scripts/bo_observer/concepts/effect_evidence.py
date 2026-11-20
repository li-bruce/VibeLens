"""Compare native effect completions within their actual business invocations.

An attempted effect can commit or abort. Only an observed completion satisfies
its declared outcome; a separately witnessed failure can close an attempt without
being promoted to a committed state transition.
"""

from collections import defaultdict

from .common import encoded


def _same_identity(entry, terminal, field):
    """Accept a native start input or output, rejecting conflicting captures."""
    if field is None:
        return True
    starts = [
        entry[direction][field]
        for direction in ("inputs", "outputs")
        if field in entry.get(direction, {})
    ]
    return (
        bool(starts)
        and all(isinstance(value, str) and value and value == starts[0] for value in starts)
        and terminal.get("outputs", {}).get(field) == starts[0]
    )


def _failed_owners(entry, event_node, index):
    """An error closes an attempt only with explicit failed owning invocations.

    An error inside a successful or unobserved business call is insufficient.
    Multiple matching ancestors must agree; timestamps or a shared entity cannot
    choose a convenient failed owner from another request.
    """
    owners = [
        index.by_id[identity]
        for identity in index.upstream(entry)
        if index.by_id[identity].get("node") == event_node
        and index.by_id[identity].get("phase") == "enter"
    ]
    terminals = [index.endings(owner, {"return", "error"}) for owner in owners]
    return bool(terminals) and all(
        len(values) == 1 and values[0].get("phase") == "error" for values in terminals
    )


def effect_errors(binding, transition, witness, event_node, run, index):
    """Require actual invocation, completion value and stable transaction identity."""
    errors = []
    effect = witness["effect"]
    completion = witness["completion"]
    cases = binding["expectations"].get(completion["expectation"], [])
    if run.get("case") not in cases:
        return errors
    prefix = transition + "/" + effect + "/" + str(run.get("case"))
    targets = set(binding["effects"].get(effect, []))
    entries = [
        event
        for event in index.events
        if event.get("node") in targets and event.get("phase") == "enter"
    ]
    related = []
    for entry in entries:
        if any(
            index.by_id[identity].get("node") == event_node
            and index.by_id[identity].get("phase") == "enter"
            for identity in index.upstream(entry)
        ):
            related.append(entry)
    if {entry["node"] for entry in related} != targets or not targets:
        errors.append("concept effect invocation missing: " + prefix)
    completed, aborted = set(), set()
    for entry in related:
        if entry["node"] != completion["node"]:
            continue
        # Each exact call needs one applicable terminal. Never choose a success
        # from a contradictory pair or another transaction using the same node.
        endings = index.endings(entry, {completion["phase"], "error"})
        if len(endings) != 1 or index.entry(endings[0]) is not entry:
            if len(endings) > 1:
                errors.append("concept effect has conflicting terminals: " + prefix)
            continue
        event = endings[0]
        # A successful return from another transaction cannot complete this
        # effect. The native collector captures the identity at both boundaries.
        if not _same_identity(entry, event, completion.get("identity_field")):
            errors.append("concept completion identity differs: " + prefix)
            continue
        if event.get("phase") == "error" and completion["phase"] != "error":
            # A rollback is a closed failed attempt, never a completed effect.
            # Its owning action must also have failed. A conflicting success
            # value (for example committed=true) still fails the contract.
            if _failed_owners(entry, event_node, index) and (
                completion["field"] not in event.get("outputs", {})
                or encoded(event["outputs"][completion["field"]]) != encoded(completion["equals"])
            ):
                aborted.add(entry["id"])
            else:
                errors.append("concept effect abort lacks matching failed owner: " + prefix)
            continue
        if completion["field"] not in event.get("outputs", {}) or encoded(
            event["outputs"][completion["field"]]
        ) != encoded(completion["equals"]):
            errors.append("concept effect completion value differs: " + prefix)
            continue
        completed.add(entry["id"])
    required = {entry["id"] for entry in related if entry["node"] == completion["node"]}
    # The independently expected successful effect must still be observed.
    # A scenario containing only aborted attempts cannot satisfy it.
    if not completed or completed | aborted != required:
        errors.append("concept effect completion missing: " + prefix)
    return errors


def effect_ownership_errors(binding, specifications, run, index):
    """Reject orphan effects once, accepting each declared transition owner.

    Sharing and revoking may reuse the same native transaction function. Their
    call instances stay separate even when one independent case exercises both.
    """
    errors, owners, completions = [], defaultdict(set), defaultdict(set)
    for _, event_node, witness in specifications:
        completion = witness["completion"]
        cases = binding["expectations"].get(completion["expectation"], [])
        if run.get("case") not in cases:
            continue
        for target in binding["effects"].get(witness["effect"], []):
            owners[target].add(event_node)
        completions[completion["node"]].update({completion["phase"], "error"})
    for event in index.events:
        node = event.get("node")
        if node in owners and event.get("phase") == "enter":
            if not any(
                index.by_id[identity].get("node") in owners[node]
                and index.by_id[identity].get("phase") == "enter"
                for identity in index.upstream(event)
            ):
                errors.append("concept effect has no transition invocation: " + event["id"])
        if event.get("phase") in completions.get(node, set()) and index.entry(event) is None:
            errors.append("concept completion has no matching effect entry: " + event["id"])
    return errors
