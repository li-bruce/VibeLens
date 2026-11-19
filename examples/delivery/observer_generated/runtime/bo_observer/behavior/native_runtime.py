"""Inspect native value and completion witnesses using actual event identities.

This module observes. It neither advances state machines nor evaluates business
permissions. Existing source, native semantics, lineage and parity checks remain
required alongside these additional behavior-contract checks.
"""

from collections import defaultdict

from ..concepts.runtime import InvocationEvidence
from ..concepts.common import canonical_id
from ..observation.ownership import parent_references
from ..observation.provenance import trace_references
from ..protocol import validate_event
from .bindings import assess_bindings
from .domains import load_domains
from .native_values import compare_values, matches
from .native_interactions import assess_interactions
from .native_lineage import dependency_errors, owning_entries


def assess_runtime(contract, discovery, model, payload, *, index=None, case_ids=None):
    """Compare the entire configured behavior scope; hiding a layer changes nothing."""
    declared = assess_bindings(contract, discovery, model, index=index, case_ids=case_ids)
    if not declared["valid"]:
        return {
            "valid": False,
            "errors": declared["errors"],
            "binding": declared,
            "status": "invalid_binding",
        }
    binding = model["behavior_bindings"]
    variables = {item["id"]: item for item in contract["variables"]}
    actions = {item["id"]: item for item in contract["actions"]}
    domains = load_domains(contract["domains"])
    refinements = {r["id"]: r for r in contract.get("refinements", [])}
    errors, values, boundaries, domain_findings = [], [], [], []
    runs = defaultdict(list)
    for run in payload.get("runs", []):
        if run.get("mode") == "on":
            runs[run.get("case")].append(run)
    build_id = payload.get("build_id")
    if not isinstance(build_id, str) or not build_id:
        return {"valid": False, "errors": [{"code": "native_build_missing"}], "binding": declared}
    # Reuse the transport and lineage contracts before correlating native facts.
    # An explicit parent ID cannot bridge an unrelated build or project.
    for case, case_runs in runs.items():
        for run in case_runs:
            events = run.get("events", [])
            for event in events:
                try:
                    validate_event(
                        event, {"project_id": contract["project_id"], "model": model}, build_id
                    )
                except (ValueError, TypeError, KeyError) as error:
                    errors.append(
                        {
                            "code": "native_event_invalid",
                            "case": case,
                            "event": event.get("id"),
                            "message": str(error),
                        }
                    )
            if not errors:
                errors.extend({**error, "case": case} for error in dependency_errors(events))
                for result in (parent_references(events, complete=True), trace_references(events)):
                    errors.extend(
                        {"code": "native_lineage_invalid", "case": case, "detail": error}
                        for error in result["errors"]
                    )
    if errors:
        return {"valid": False, "errors": errors, "binding": declared, "status": "invalid_events"}

    def selected(case):
        matches_ = runs[case]
        if len(matches_) != 1:
            errors.append({"code": "native_case_missing_or_duplicate", "case": case})
            return None
        return matches_[0]

    def value_scope(ident, witness, owners, domain=None):
        for case in witness["cases"]:
            run = selected(case)
            if run is None:
                continue
            result = compare_values(run, witness, build_id=build_id, owners=owners, domain=domain)
            values.append({"id": ident, "case": case, **result})
            errors.extend({**error, "binding": ident, "case": case} for error in result["errors"])
            domain_findings.extend(
                {**item, "binding": ident, "case": case} for item in result["domains"]
            )

    for ident, item in binding["variables"].items():
        variable = variables[ident]
        domain = domains[variable["domain"]]
        if item.get("refinement_ref"):
            domain = domains[refinements[item["refinement_ref"]]["concrete_domain"]]
        value_scope(canonical_id("variable", ident), item, {variable["owner"]}, domain)
    for ident, item in binding["actions"].items():
        owners = set(actions[ident]["model_refs"])
        value_scope(canonical_id("completion", ident), item["completion_witness"], owners)
        for exit_ in item["exits"]:
            value_scope(canonical_id("exit", ident, exit_["kind"]), exit_["witness"], owners)
        for name, witness in item["parameters"].items():
            value_scope(
                canonical_id("parameter", ident, name),
                witness,
                owners,
                domains[actions[ident]["parameters"][name]],
            )
        terminal_sites = {
            "complete": item["completion"],
            **{exit_["kind"]: exit_["site"] for exit_ in item["exits"]},
        }
        for case in item["cases"]:
            run = selected(case["id"])
            if run is None:
                continue
            events = run.get("events", [])
            if any(not e.get("id") for e in events) or len({e["id"] for e in events}) != len(
                events
            ):
                errors.append({"code": "native_event_identity", "case": case["id"]})
                continue
            invocations = InvocationEvidence(events)
            entries = [e for e in events if matches(e, item["entry"]) and not e.get("context_only")]
            if not entries:
                errors.append({"code": "action_entry_missing", "action": ident, "case": case["id"]})
            for name, witness in item["parameters"].items():
                for event in events:
                    if matches(event, witness["observation"]) and not event.get("context_only"):
                        if len(owning_entries(invocations, entries, event)) != 1:
                            errors.append(
                                {
                                    "code": "action_parameter_unowned",
                                    "action": ident,
                                    "case": case["id"],
                                    "parameter": name,
                                    "event": event["id"],
                                }
                            )
            terminals = [
                (kind, event)
                for kind, site in terminal_sites.items()
                for event in events
                if matches(event, site) and not event.get("context_only")
            ]
            assigned = defaultdict(list)
            for kind, event in terminals:
                parents = owning_entries(invocations, entries, event)
                if len(parents) != 1:
                    errors.append(
                        {
                            "code": "action_completion_unowned",
                            "action": ident,
                            "case": case["id"],
                            "event": event["id"],
                        }
                    )
                    continue
                assigned[parents[0]["id"]].append((kind, event))
            for entry in entries:
                actual = assigned[entry["id"]]
                # An action may commit and later return. Only the configured
                # physical completion/alternative exits are selected above.
                valid = (
                    len(actual) == len(case["boundaries"])
                    and {kind for kind, _ in actual} == set(case["boundaries"])
                    and len({e["id"] for _, e in actual}) == len(actual)
                )
                boundaries.append(
                    {
                        "action": ident,
                        "case": case["id"],
                        "entry": entry["id"],
                        "terminals": [event["id"] for _, event in actual],
                        "valid": valid,
                    }
                )
                if not valid:
                    errors.append(
                        {
                            "code": "action_completion_differs",
                            "action": ident,
                            "case": case["id"],
                            "entry": entry["id"],
                            "expected": case["boundaries"],
                            "actual": [kind for kind, _ in actual],
                        }
                    )
    interactions = assess_interactions(contract, binding, runs, build_id)
    errors.extend(interactions["errors"])
    return {
        "valid": not errors,
        "errors": errors,
        "binding": declared,
        "values": values,
        "boundaries": boundaries,
        "domain_findings": domain_findings,
        "interactions": interactions,
        "scope": "Native value correspondence and action boundaries; business expectations are separate",
    }
