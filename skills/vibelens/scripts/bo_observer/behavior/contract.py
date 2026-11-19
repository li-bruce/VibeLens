"""Resolve behavior contracts against the existing canonical concept registry.

This loader checks definitions only. Native binding, runtime correspondence and
finite exploration have independent gates; none is inferred from a valid JSON file.
"""

from copy import deepcopy

from ..concepts.common import digest
from ..concepts.model import build
from ..protocol import schema_diagnostics
from .diagnostics import ContractError, index_records, require
from .domains import load_domains
from .references import load_variables, require_reference
from .actions import load_actions
from .expressions import UNKNOWN, Expressions, known_value
from .policy_refs import PolicyReferences
from .capabilities import describe


def _sources(refs, sources, path):
    for number, ref in enumerate(refs):
        require(ref in sources, "unknown_source", f"{path}/{number}", ref)


def assess(contract, discovery):
    """Return structural/semantic findings without changing the inputs or executor.

    Finite-domain summaries concern representations only. No statement about a
    complete finite system, implementation fidelity or formal proof is made here.
    """
    structural = schema_diagnostics(contract, "behavior")
    if structural:
        return {"valid": False, "errors": structural, "status": "invalid"}
    try:
        try:
            data = build(discovery)  # Reuse all existing state, rule and concept checks.
        except (ValueError, KeyError, TypeError, RecursionError) as error:
            raise ContractError("invalid_concept_definition", "/discovery", str(error)) from error
        registry = data["records"]
        require(
            contract["project_id"] == discovery.get("project_id"),
            "project_mismatch",
            "/project_id",
            "Contract and discovery must describe the same project",
        )
        scope = contract["scope"]
        for position, ref in enumerate(scope["model_refs"]):
            require_reference(
                registry,
                ref,
                {"business_network", "state_model", "rule_operation"},
                f"/scope/model_refs/{position}",
            )
        for position, ref in enumerate(scope["object_refs"]):
            require_reference(registry, ref, {"object"}, f"/scope/object_refs/{position}")
        sources = {source["id"] for source in discovery["sources"]}
        for section in ("domains", "variables", "actions", "properties"):
            for position, item in enumerate(contract[section]):
                _sources(item["source_refs"], sources, f"/{section}/{position}/source_refs")
        domains = load_domains(contract["domains"])
        for position, record in enumerate(contract["domains"]):
            if record["type"] == "identity":
                path = f"/domains/{position}/object_ref"
                require_reference(registry, record["object_ref"], {"object"}, path)
                require(
                    record["object_ref"] in scope["object_refs"],
                    "identity_scope",
                    path,
                    "Identity owner must be a selected object",
                )
        variables, owners = load_variables(contract, registry, domains, discovery)
        policy = PolicyReferences(registry, scope["model_refs"])
        expressions = Expressions(domains, variables, policy)
        expressions.expect_boolean(contract["initial"], "/initial")
        initial_states = {
            key: registry[value["concept_ref"]]["initial"]
            for key, value in variables.items()
            if registry[value["concept_ref"]]["kind"] == "state_model"
        }
        initial_result = known_value(contract["initial"], initial_states, expressions)
        require(
            initial_result is not False,
            "empty_initial",
            "/initial",
            "Initial predicate contradicts the canonical initial state",
        )
        actions, summaries = load_actions(
            contract, registry, domains, variables, owners, expressions, data["dependencies"]
        )
        properties = index_records(contract["properties"], "/properties")
        for position, prop in enumerate(contract["properties"]):
            path = f"/properties/{position}"
            require(
                set(prop["action_refs"]) <= set(actions),
                "unknown_action",
                path + "/action_refs",
                "Property action is not declared",
            )
            require(
                bool(prop["action_refs"]) == (prop["kind"] == "transition_constraint"),
                "property_scope",
                path + "/action_refs",
                "Transition constraints select actions; state invariants apply to the selected state",
            )
            expressions.expect_boolean(
                prop["expression"],
                path + "/expression",
                allow_after=prop["kind"] == "transition_constraint",
            )
        return {
            "valid": True,
            "errors": [],
            "status": "unresolved" if scope["unresolved"] else "defined",
            "definition_sha256": digest(contract),
            "concept_sha256": digest(data["records"]),
            "domain_capabilities": {
                key: domain.finite_capability() for key, domain in domains.items()
            },
            "definition_capabilities": describe(),
            "variables": sorted(variables),
            "actions": sorted(actions),
            "action_definitions": summaries,
            "canonical_initial_states": initial_states,
            "initial_consistency": "unresolved" if initial_result is UNKNOWN else "consistent",
            "properties": sorted(properties),
            "policy_references": deepcopy(policy.uses),
            "unresolved": deepcopy(scope["unresolved"]),
            "binding": "not_checked",
            "analysis": "not_run",
        }
    except ContractError as error:
        return {
            "valid": False,
            "errors": [error.diagnostic.as_dict()],
            "status": (
                "unsupported" if error.diagnostic.code.startswith("unsupported_") else "invalid"
            ),
        }
