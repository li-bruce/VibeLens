"""Validate and project logical model traces without creating runtime observations.

The analysis runner supplies actual explored states. This adapter locates them in
the canonical graph; it never invents timestamps, invocation spans or call edges.
Native reproduction remains a separate recording with its own provenance.
"""

from copy import deepcopy

from ..behavior.contract import assess
from ..behavior.domains import load_domains, value_key
from ..concepts.common import canonical_id, digest, fields
from ..concepts.model import build

SCHEMA = "bo-analysis-trace/v1"
FIELDS = {
    "schema",
    "origin",
    "subject",
    "analysis_id",
    "definition_sha256",
    "property_refs",
    "states",
    "steps",
    "loop_back",
}


def project_trace(trace, contract, discovery):
    """Return logical steps, exact values and existing graph references.

    Malformed structure and unknown identities fail closed. A value outside its
    declared domain remains visible with a finding: discarding it could suppress
    the counterexample the user needs to inspect.
    """
    fields(trace, FIELDS, FIELDS, "analysis trace")
    definition = assess(contract, discovery)
    if not definition["valid"]:
        raise ValueError("Invalid trace definition: " + str(definition["errors"]))
    if (
        trace["schema"] != SCHEMA
        or trace["origin"] != "model_analysis"
        or trace["subject"] != "design_model"
    ):
        raise ValueError("Expected a design-model analysis trace")
    if trace["definition_sha256"] != digest(contract):
        raise ValueError("Trace belongs to another definition")
    if not isinstance(trace["analysis_id"], str) or not trace["analysis_id"].strip():
        raise ValueError("Trace requires an analysis identity")
    properties = trace["property_refs"]
    if (
        not isinstance(properties, list)
        or not properties
        or not all(isinstance(p, str) for p in properties)
        or len(properties) != len(set(properties))
        or not set(properties) <= {p["id"] for p in contract["properties"]}
    ):
        raise ValueError("Trace properties must be distinct declared identities")
    states, steps, loop = trace["states"], trace["steps"], trace["loop_back"]
    if (
        not isinstance(states, list)
        or not 1 <= len(states) <= 10000
        or not isinstance(steps, list)
        or len(steps) != len(states) - 1
    ):
        raise ValueError("Trace requires one transition between successive logical states")
    if loop is not None and (type(loop) is not int or not 0 <= loop < len(states) - 1):
        raise ValueError("Invalid trace loop-back index")
    variables = {item["id"]: item for item in contract["variables"]}
    actions = {item["id"]: item for item in contract["actions"]}
    domains = load_domains(contract["domains"])
    graph = build(discovery)["graph"]
    nodes = {node["id"]: node for node in graph["nodes"]}
    members = {item["id"]: set(item["nodes"]) for item in graph["networks"]}
    findings = []
    for index, state in enumerate(states):
        if not isinstance(state, dict) or set(state) != set(variables):
            raise ValueError("Trace state must contain every variable exactly once")
        # Canonical encoding rejects non-finite values rather than repairing them.
        value_key(state)
        for ident, value in state.items():
            if not domains[variables[ident]["domain"]].accepts(value):
                findings.append(
                    {
                        "step": index,
                        "variable": ident,
                        "actual": deepcopy(value),
                        "status": "outside_declared_domain",
                    }
                )
    if loop is not None and value_key(states[-1]) != value_key(states[loop]):
        raise ValueError("Loop closure must retain the repeated state explicitly")
    projected = []
    for index, step in enumerate(steps):
        fields(step, {"action", "parameters"}, {"action", "parameters"}, "logical step")
        action = actions.get(step["action"]) if isinstance(step["action"], str) else None
        if step["action"] is not None and action is None:
            raise ValueError("Unknown trace action")
        if not isinstance(step["parameters"], dict) or set(step["parameters"]) != set(
            action["parameters"] if action else {}
        ):
            raise ValueError("Trace parameters differ from the declared action")
        for name, value in step["parameters"].items():
            if not domains[action["parameters"][name]].accepts(value):
                raise ValueError("Trace parameter is outside its domain")
        before, after = states[index : index + 2]
        changed = [key for key in variables if value_key(before[key]) != value_key(after[key])]
        if action is None and changed:
            raise ValueError("A stuttering step cannot change values")
        if action and set(changed) - set(action["writes"]):
            raise ValueError("Trace action changes an undeclared variable")
        refs = set(action["model_refs"] if action else [])
        if action and action.get("transition_ref"):
            refs.add(action["transition_ref"])
            events = {
                edge["from"]
                for edge in graph["edges"]
                if edge["to"] == action["transition_ref"] and edge["type"] == "requests_transition"
            }
            refs.update(events)
            refs.update(
                edge["from"]
                for edge in graph["edges"]
                if edge["to"] in events and edge["type"] == "action_requests_event"
            )
        changes = []
        for ident in changed:
            variable = variables[ident]
            refs.add(variable["concept_ref"])
            owner = variable["owner"]
            states_for_owner = [
                node["id"]
                for node in graph["nodes"]
                if node.get("concept_kind") == "state"
                and node["id"] in members.get(canonical_id("network", owner), set())
                and node.get("value") in (before[ident], after[ident])
            ]
            refs.update(states_for_owner)
            changes.append(
                {
                    "variable": ident,
                    "before": deepcopy(before[ident]),
                    "after": deepcopy(after[ident]),
                    "concept_ref": variable["concept_ref"],
                }
            )
        original_edges = [
            edge["id"] for edge in graph["edges"] if edge["from"] in refs and edge["to"] in refs
        ]
        projected.append(
            {
                "index": index,
                "action": step["action"],
                "parameters": deepcopy(step["parameters"]),
                "nodes": sorted(refs & set(nodes)),
                "edges": original_edges,
                "changes": changes,
            }
        )
    return {
        **deepcopy(trace),
        "axis": "logical_step",
        "projected_steps": projected,
        "domain_findings": findings,
        "execution_authority": False,
    }
