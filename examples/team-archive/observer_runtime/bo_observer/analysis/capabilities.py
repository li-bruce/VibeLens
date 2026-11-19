"""Admit a declared finite subset before any optional exporter or runner starts.

Eligibility is about this version's exact design representation. It is neither a
proof nor a claim that application code implements the design. Tools are not
imported, downloaded or executed by this module.
"""

from copy import deepcopy

from ..behavior import assess
from ..concepts.common import digest, canonical_id
from ..protocol import schema_diagnostics

CAPABILITIES = {
    "id": "finite-design-admission/2",
    "subject": "design_model",
    "state_semantics": "flat_interleaving",
    "domains": ["boolean", "enum", "integer", "identity", "sequence", "set"],
    "property_kinds": ["state_invariant", "transition_constraint", "progress_property"],
    "policy_nodes": ["input", "constant", "all", "any", "not"],
    "operators": [
        "literal",
        "var",
        "param",
        "all",
        "any",
        "not",
        "implies",
        "eq",
        "ne",
        "lt",
        "le",
        "add",
        "sub",
        "policy_ref",
        "length",
        "append",
        "tail",
        "set_add",
        "set_remove",
        "member",
        "select",
        "forall",
        "exists",
    ],
    "exporter_available": True,
    "runner_available": True,
}


def admit(contract, discovery, profile):
    """Return exact unresolved/unsupported dimensions instead of a false pass."""
    errors = schema_diagnostics(profile, "analysis-profile")
    if errors:
        return {"status": "invalid", "eligible": False, "diagnostics": errors}
    original = assess(contract, discovery)
    if not original["valid"]:
        return {
            "status": original["status"],
            "eligible": False,
            "diagnostics": original["errors"],
            "capabilities": deepcopy(CAPABILITIES),
        }
    candidate = deepcopy(contract)
    issues = []

    def issue(code, path, message, status="unsupported"):
        issues.append({"code": code, "path": path, "message": message, "status": status})

    if profile["subject"] != "design_model":
        issue(
            "implementation_analysis_unavailable",
            "/subject",
            "Native abstraction is not implemented",
        )
    domains = {d["id"]: d for d in candidate.get("domains", [])}
    for ident, bound in profile["bounds"].items():
        if ident not in domains:
            issue("unknown_domain", "/bounds/" + ident, "Bound has no domain", "invalid")
            continue
        # Bounds affect a detached design only. Origin is retained in the receipt;
        # no native declaration or runtime limit is updated.
        domains[ident].update({k: v for k, v in bound.items() if k != "origin"})
        domains[ident]["bound_origin"] = bound["origin"]
    definition = assess(candidate, discovery)
    if not definition["valid"]:
        return {
            "status": definition["status"],
            "eligible": False,
            "diagnostics": definition["errors"],
            "capabilities": deepcopy(CAPABILITIES),
        }
    if set(profile["model_refs"]) != set(contract["scope"]["model_refs"]):
        issue(
            "partial_model_scope",
            "/model_refs",
            "This adapter requires the complete declared model scope",
        )
    selected_properties = set(profile["property_refs"])
    properties = {p["id"]: p for p in candidate["properties"]}
    if not selected_properties <= set(properties):
        issue("unknown_property", "/property_refs", "Profile property is not declared", "invalid")
    assumptions = {a["id"]: a for a in candidate.get("assumptions", [])}
    if not set(profile["assumption_refs"]) <= set(assumptions):
        issue(
            "unknown_assumption",
            "/assumption_refs",
            "Profile assumption is not declared",
            "invalid",
        )
    for ident in profile["assumption_refs"]:
        if ident in assumptions and assumptions[ident]["status"] != "confirmed":
            issue("unconfirmed_assumption", "/assumption_refs", ident, "unresolved")
        elif ident in assumptions and (
            assumptions[ident]["kind"] != "scheduling" or not assumptions[ident]["action_refs"]
        ):
            issue(
                "unsupported_assumption",
                "/assumption_refs",
                "Only explicit nonempty scheduling action sets are interpreted: " + ident,
            )
    for name in contract["scope"]["unresolved"]:
        issue("unresolved_scope", "/scope/unresolved", name, "unresolved")
    for name in contract["scope"]["exclusions"]:
        issue("unmodeled_boundary", "/scope/exclusions", name, "unresolved")
    for section, status in definition["configuration"].items():
        if status == "not_configured":
            issue(
                "unconfigured_boundary",
                "/" + section,
                "Declare applicable boundaries or an empty list",
                "unresolved",
            )
    required = {v["domain"] for v in candidate["variables"]}
    required.update(d for a in candidate["actions"] for d in a["parameters"].values())

    def visit(value, path):
        if isinstance(value, dict):
            if "op" in value:
                if value["op"] not in CAPABILITIES["operators"]:
                    issue("unsupported_operator", path, value["op"])
                if "domain" in value:
                    required.add(value["domain"])
            for key, child in value.items():
                visit(child, path + "/" + key)
        elif isinstance(value, list):
            for number, child in enumerate(value):
                visit(child, f"{path}/{number}")

    visit(candidate["initial"], "/initial")
    for n, action in enumerate(candidate["actions"]):
        visit(action, f"/actions/{n}")
        canonical = definition["action_definitions"][action["id"]]["canonical_transition"]
        if canonical and any(canonical.get(key) for key in ("conditions", "unless", "effects")):
            issue(
                "unmodeled_transition_callback",
                f"/actions/{n}/transition_ref",
                "Native guards/effects require explicit supported correspondence",
            )
    for n, prop in enumerate(candidate["properties"]):
        if prop["id"] in selected_properties:
            visit(prop, f"/properties/{n}")
            if prop["kind"] not in CAPABILITIES["property_kinds"]:
                issue("unsupported_property", f"/properties/{n}", prop["kind"])
            if not set(prop.get("assumption_refs", [])) <= set(profile["assumption_refs"]):
                issue(
                    "missing_property_assumption",
                    f"/properties/{n}",
                    "Include this property's assumptions",
                    "unresolved",
                )
    termination = profile.get("termination")
    if termination:
        from ..behavior.domains import load_domains
        from ..behavior.expressions import Expressions
        from ..behavior.policy_refs import PolicyReferences
        from ..concepts.model import build

        sources = {s["id"] for s in discovery["sources"]}
        if not set(termination["source_refs"]) <= sources:
            issue(
                "unknown_source",
                "/termination/source_refs",
                "Termination needs recorded intent",
                "invalid",
            )
        try:
            checker = Expressions(
                load_domains(candidate["domains"]),
                {v["id"]: v for v in candidate["variables"]},
                PolicyReferences(build(discovery)["records"], candidate["scope"]["model_refs"]),
            )
            checker.expect_boolean(termination["condition"], "/termination/condition")
            visit(termination["condition"], "/termination/condition")
        except ValueError as error:
            issue("invalid_termination", "/termination", str(error), "invalid")
    # A collection is finite only if every nested carrier is supported as well.
    pending = list(required)
    while pending:
        item = domains[pending.pop()]
        for ref in (item.get("element_domain"), item.get("key_domain")):
            if ref and ref not in required:
                required.add(ref)
                pending.append(ref)
    for ident in sorted(required):
        if not definition["domain_capabilities"][ident]["supported"]:
            issue(
                "unbounded_representation",
                "/domains/" + ident,
                definition["domain_capabilities"][ident]["reason"],
            )
        elif domains[ident]["type"] not in CAPABILITIES["domains"]:
            issue("unsupported_domain", "/domains/" + ident, domains[ident]["type"])
        elif (
            domains[ident]["type"] == "enum"
            and len({type(v).__name__ for v in domains[ident]["values"]}) > 1
        ):
            issue(
                "unsupported_mixed_enum",
                "/domains/" + ident,
                "TLC comparisons require a homogeneous scalar carrier",
            )
    for ident, value in definition["policy_references"].items():
        if value["opaque_predicates"]:
            issue(
                "opaque_policy_predicate", "/policy/" + ident, ", ".join(value["opaque_predicates"])
            )
    for item in candidate.get("interactions", []):
        if item["kind"] != "shared_read" or item["consistency"] != "independent":
            issue("unsupported_interaction", "/interactions/" + item["id"], item["kind"])
    if candidate.get("refinements"):
        issue(
            "unsupported_refinement",
            "/refinements",
            "Native abstraction correspondence is not implemented",
        )
    for state in discovery.get("state_models", []):
        if canonical_id("state-model", state["id"]) in profile["model_refs"]:
            if any(not isinstance(value, str) for value in state["states"]):
                issue(
                    "unsupported_state_hierarchy",
                    "/state_models/" + state["id"],
                    "This adapter admits flat string-valued states",
                )
            if state.get("execution"):
                issue(
                    "unsupported_activity_semantics",
                    "/state_models/" + state["id"],
                    "Resources/joins need their adapter",
                )
            modeled = {a.get("transition_ref") for a in candidate["actions"]}
            for transition in state["transitions"]:
                ref = canonical_id("transition", state["id"], transition["id"])
                if ref not in modeled:
                    issue(
                        "unmapped_model_transition",
                        "/state_models/" + state["id"],
                        ref,
                        "unresolved",
                    )
    if candidate.get("initial_alternatives"):
        issue(
            "unsupported_recovery_initialization",
            "/initial_alternatives",
            "Recovery export is not implemented",
        )
    status = next(
        (
            s
            for s in ("invalid", "unresolved", "unsupported")
            if any(i["status"] == s for i in issues)
        ),
        "eligible",
    )
    return {
        "status": status,
        "eligible": not issues,
        "diagnostics": issues,
        "capabilities": deepcopy(CAPABILITIES),
        "analysis": "not_run",
        "definition_sha256": digest(candidate),
        "original_sha256": digest(contract),
        "profile_sha256": digest(profile),
        "bounds": deepcopy(profile["bounds"]),
        "claim_scope": "selected_design_representation",
    }
