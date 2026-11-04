"""Check conceptual associations using original invocation and value evidence.

This module never evaluates permissions or runs effects. It joins already
recorded IDs and compares selected observations with independently confirmed
outcomes. Static containment, shared entities and timestamp proximity do not
establish ownership.
"""

from collections import defaultdict

from .common import canonical_id, encoded

IDENTITY_FIELDS = (
    "project_id",
    "model_revision",
    "build_id",
    "run_id",
    "producer_id",
    "stream_id",
)


class InvocationEvidence:
    """Index exact call entries and explicit causal references within one case."""

    def __init__(self, events):
        self.events = events
        self.by_id = {event["id"]: event for event in events}
        self.entries = defaultdict(list)
        self.calls = defaultdict(list)
        for event in events:
            if event.get("phase") == "enter" and event.get("call_id"):
                self.entries[self.key(event)].append(event)
                self.calls[self.call_key(event)].append(event)

    @staticmethod
    def key(event):
        # Call IDs are scoped by the observed entity and attempt, as in the
        # original lifecycle protocol. Two users may reuse a local call name;
        # their explicit parent entry IDs still identify distinct invocations.
        return (
            *[event.get(key) for key in IDENTITY_FIELDS],
            event.get("entity"),
            event.get("attempt"),
            event.get("node"),
            event.get("call_id"),
        )

    @staticmethod
    def call_key(event, parent=False):
        # A bare legacy parent call stays local to its entity and attempt. The
        # explicit parent entry ID is the cross-entity / cross-producer bridge.
        return (
            *[event.get(key) for key in IDENTITY_FIELDS],
            event.get("entity"),
            event.get("attempt"),
            event.get("parent_call_id" if parent else "call_id"),
        )

    def entry(self, event):
        matches = self.entries.get(self.key(event), [])
        return matches[0] if len(matches) == 1 else None

    def upstream(self, event):
        """Return witnessed ancestors, bounding malformed or cyclic input work."""
        pending, visited = [event], set()
        while pending and len(visited) < 4096:
            current = pending.pop()
            identity = current["id"]
            if identity in visited:
                continue
            visited.add(identity)
            references = []
            if current.get("parent_event_id"):
                references.append(current["parent_event_id"])
            elif current.get("parent_call_id"):
                matches = self.calls.get(self.call_key(current, parent=True), [])
                if len(matches) == 1:
                    references.append(matches[0]["id"])
            entry = self.entry(current)
            if entry is not None:
                references.append(entry["id"])
            references.extend(
                item["event"]
                for item in current.get("depends", [])
                if item.get("type") in {"control", "trigger", "recheck"}
            )
            pending.extend(self.by_id[ref] for ref in references if ref in self.by_id)
        return visited


def _policy_errors(model, run, index):
    """Keep the native policy result with its declared business invocation."""
    errors = []
    operations = {item["id"]: item for item in (model.get("policy") or {}).get("operations", [])}
    for evaluation in run.get("policy_evaluations", []):
        operation = operations.get(evaluation.get("operation"))
        if not operation:
            continue  # The existing policy gate reports invalid declarations.
        roots = [
            event
            for event in index.events
            if event.get("node") == "policy:" + operation["root"]
            and event.get("phase") == "decision"
            and event.get("inputs", {}).get("bo_check") == evaluation.get("check_id")
        ]
        if len(roots) != 1:
            errors.append("concept rule lacks one observed root: " + operation["id"])
            continue
        root = roots[0]
        targets = set(operation["business_nodes"])
        ancestor_ids = index.upstream(root)
        owns_check = any(
            index.by_id[identity].get("node") in targets
            and index.by_id[identity].get("phase") == "enter"
            for identity in ancestor_ids
        )
        # A check may precede entry to the guarded action. In that case the
        # invocation must explicitly consume this decision, not merely occur
        # later in the same request or use the same file identity.
        uses_check = any(
            event.get("node") in targets
            and event.get("phase") == "enter"
            and root["id"] in index.upstream(event)
            for event in index.events
        )
        if not owns_check and not uses_check:
            errors.append("concept rule invocation target differs: " + evaluation["check_id"])
    return errors


def _effect_errors(binding, transition, witness, event_node, run, index):
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
    completed = set()
    for event in index.events:
        if event.get("node") != completion["node"] or event.get("phase") != completion["phase"]:
            continue
        entry = index.entry(event)
        if entry is None or entry not in related:
            # A shared effect can execute for another declared transition in the
            # same case. The case-wide ownership gate handles real orphans;
            # this transition only checks completions of its own invocations.
            continue
        # A successful return from another transaction cannot complete this
        # effect. The native collector captures the identity at both boundaries.
        identity = completion.get("identity_field")
        if identity and (
            not isinstance(entry.get("outputs", {}).get(identity), str)
            or not entry["outputs"][identity]
            or event.get("outputs", {}).get(identity) != entry["outputs"][identity]
        ):
            errors.append("concept completion identity differs: " + prefix)
            continue
        if completion["field"] not in event.get("outputs", {}) or encoded(
            event["outputs"][completion["field"]]
        ) != encoded(completion["equals"]):
            errors.append("concept effect completion value differs: " + prefix)
            continue
        completed.add(entry["id"])
    required = {entry["id"] for entry in related if entry["node"] == completion["node"]}
    if not required or completed != required:
        errors.append("concept effect completion missing: " + prefix)
    return errors


def _effect_ownership_errors(binding, specifications, run, index):
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
        completions[completion["node"]].add(completion["phase"])
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


def runtime_errors(doc, model, payload):
    """Add association evidence to the existing source, policy and business gates.

    Only v2 conceptual projects opt into these requirements. Legacy projects
    retain their existing validation. Completion cases come from independent
    expectations, so a denied request is not falsely required to execute effects.
    """
    if not isinstance(doc, dict) or doc.get("schema") != "business-discovery/v2":
        return []
    binding = model["concepts"]
    errors = []
    specifications = []
    for state in doc["state_models"]:
        for transition in state["transitions"]:
            tid = canonical_id("transition", state["id"], transition["id"])
            event = binding.get("events", {}).get(
                canonical_id("event", state["id"], transition["trigger"]), {}
            )
            specifications.extend(
                (tid, event.get("node"), witness)
                for witness in binding.get("transition_effects", {}).get(tid, [])
            )
    on_runs = [run for run in payload.get("runs", []) if run.get("mode") == "on"]
    for run in on_runs:
        events = run.get("events", [])
        if any(not isinstance(event, dict) or not event.get("id") for event in events):
            errors.append("concept runtime requires original event identities")
            continue
        if len({event["id"] for event in events}) != len(events):
            errors.append("concept runtime has duplicate event identities")
            continue
        index = InvocationEvidence(events)
        errors.extend(_policy_errors(model, run, index))
        errors.extend(_effect_ownership_errors(binding, specifications, run, index))
        for tid, event_node, witness in specifications:
            errors.extend(_effect_errors(binding, tid, witness, event_node, run, index))
    required_cases = {
        case
        for witnesses in binding.get("transition_effects", {}).values()
        for witness in witnesses
        for case in binding["expectations"].get(witness["completion"]["expectation"], [])
    }
    for case in sorted(required_cases - {run.get("case") for run in on_runs}):
        errors.append("concept effect completion case missing: " + case)
    return errors
