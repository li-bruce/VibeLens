"""Bind behavior values and boundaries without executing a business action.

This is an additional source/capture obligation check. It does not replace the
existing native machine, policy, implementation inventory or business gates.
Runtime correspondence and application correctness remain separate verdicts.
"""

from ..protocol import schema_diagnostics
from .contract import assess
from .domains import load_domains, value_key
from .diagnostics import ContractError, require, pointer
from .binding_sources import BindingSources, represents

NATIVE_KEYS = {"model", "instance", "invocation", "attempt", "build"}
OBSERVATION_ROOTS = {"events", "projection", "stategraph_export", "mapping_checks"}


def exact_scope(wanted, actual, code, path):
    """Require both completeness and absence of unknown IDs; names are not aliases."""
    missing, extra = set(wanted) - set(actual), set(actual) - set(wanted)
    require(
        not missing and not extra,
        code,
        path,
        "Missing: " + ", ".join(sorted(missing)) + "; unknown: " + ", ".join(sorted(extra)),
    )


def interaction_roles(interaction):
    """Derive boundary obligations from every declared interaction participant."""
    kind = interaction["kind"]
    if kind == "shared_read":
        roles = {(a, "read") for a in interaction["reader_actions"]}
        if interaction["consistency"] == "transaction":
            roles.add((interaction["completion_action"], "commit"))
        return roles
    if kind == "handoff":
        roles = {(interaction["producer"], "send"), (interaction["consumer"], "receive")}
        if "acknowledgement_action" in interaction:
            roles.add((interaction["acknowledgement_action"], "acknowledge"))
        return roles
    if kind == "resource":
        return {(a, "acquire") for a in interaction["acquire_actions"]} | {
            (a, "release") for a in interaction["release_actions"]
        }
    if kind == "join":
        return {(a, "arrive") for a in interaction["arrival_actions"]} | {
            (interaction["release_action"], "join")
        }
    return {(a, "member") for a in interaction["member_actions"]} | {
        (interaction["completion_action"], "commit")
    }


def interaction_fields(interaction, role):
    """Only named business correlation facts establish a cross-model boundary.

    A shared revision uses an explicit snapshot group, so successive legitimate
    reads are not mistaken for an inconsistent joint read. Resource operations
    likewise distinguish repeated acquisitions by the same holder.
    """
    kind = interaction["kind"]
    if kind == "shared_read":
        if role == "commit":
            return {"group", "transaction"}
        consistency = interaction["consistency"]
        return {"value"} | ({"group", consistency} if consistency != "independent" else set())
    if kind == "handoff":
        return {"correlation"} | ({"payload"} if role != "acknowledge" else set())
    if kind == "resource":
        return {"resource", "holder", "operation"}
    if kind == "join":
        return {"correlation", "members" if role == "join" else "member"}
    return {"transaction"}


def assess_bindings(contract, discovery, model, *, index=None, case_ids=None):
    """Check a complete contract-to-source declaration, with explicit unchecked gates.

    ``index`` is the existing independent application source scan. ``case_ids``
    comes from independently configured acceptance cases, not from this binding.
    Omitting either leaves that check visibly pending; it cannot certify runtime.
    """
    definition = assess(contract, discovery)
    if not definition["valid"]:
        return {"valid": False, "status": "invalid_definition", "errors": definition["errors"]}
    binding = model.get("behavior_bindings")
    errors = schema_diagnostics(binding, "behavior-bindings")
    if errors:
        return {"valid": False, "status": "invalid_binding", "errors": errors}
    try:
        require(
            binding["definition_sha256"] == definition["definition_sha256"],
            "stale_behavior_binding",
            "/definition_sha256",
            "Bind the current behavior definition",
        )
        require(
            not definition["unresolved"],
            "behavior_scope_unresolved",
            "/scope",
            "Resolve the selected model scope before binding it",
        )
        if index is not None:
            require(
                not index.get("errors"),
                "binding_source_scan_incomplete",
                "/sources",
                str(index.get("errors")),
            )
        source = BindingSources(model, index)
        domains = load_domains(contract["domains"])
        variables = {v["id"]: v for v in contract["variables"]}
        actions = {a["id"]: a for a in contract["actions"]}
        interactions = {i["id"]: i for i in contract.get("interactions", [])}
        for name, wanted, code in (
            ("variables", variables, "unbound_behavior_variable"),
            ("actions", actions, "unbound_behavior_action"),
            ("interactions", interactions, "unbound_behavior_interaction"),
        ):
            exact_scope(wanted, binding[name], code, "/" + name)

        def cases(names, path):
            require(
                len(names) == len(set(names)),
                "duplicate_binding_case",
                path,
                "Each case has one expected physical boundary",
            )
            if case_ids is not None:
                require(
                    set(names) <= set(case_ids),
                    "binding_case_missing",
                    path,
                    str(sorted(set(names) - set(case_ids))),
                )

        for ident, item in binding["actions"].items():
            cases([c["id"] for c in item["cases"]], pointer("/actions", ident) + "/cases")

        def value(item, domain, path):
            reader = source.source(item["reader"], path + "/reader")
            writers = [source.source(s, path + "/writers") for s in item["writers"]]
            require(
                reader not in writers,
                "reader_is_writer",
                path,
                "Use an independently read native value, not the writer's observation",
            )
            require(
                len(writers) == len(set(writers)),
                "duplicate_binding_writer",
                path,
                "Writer identities must be unique",
            )
            spec = source.field(item["observation"], path + "/observation")
            require(
                domain is None or represents(spec, domain),
                "binding_capture_type",
                path,
                "Capture representation differs from the native domain",
            )
            native = item["native"]
            require(
                native["collection"][0] not in OBSERVATION_ROOTS,
                "observation_derived_native_value",
                path + "/native",
                "Read native facts independently of the graph and captured events",
            )
            names = [key["name"] for key in native["keys"]]
            require(
                NATIVE_KEYS <= set(names) and len(names) == len(set(names)),
                "native_identity_incomplete",
                path + "/native/keys",
                "Retain model, instance, invocation, attempt and build identity",
            )
            cases(item["cases"], path + "/cases")

        refinements = {r["id"]: r for r in contract.get("refinements", [])}
        for ident, item in binding["variables"].items():
            path = pointer("/variables", ident)
            variable = variables[ident]
            domain = domains[variable["domain"]]
            if "refinement_ref" in item:
                refinement = refinements.get(item["refinement_ref"])
                require(
                    refinement is not None and refinement["variable_ref"] == ident,
                    "binding_refinement_differs",
                    path,
                    "Use this variable's declared refinement",
                )
                domain = domains[refinement["concrete_domain"]]
            value(item, domain, path)
            if any(ident in a["writes"] for a in actions.values()):
                require(
                    bool(item["writers"]),
                    "binding_writer_missing",
                    path,
                    "The contract writes this variable; identify its actual native writer",
                )
            expected_cases = {
                c["id"]
                for aid, action in actions.items()
                if ident in action["reads"] or ident in action["writes"]
                for c in binding["actions"][aid]["cases"]
                if "complete" in c["boundaries"]
            }
            require(
                expected_cases <= set(item["cases"]),
                "variable_action_case_missing",
                path,
                "Cover the completed actions that use this value",
            )

        for ident, item in binding["actions"].items():
            path = pointer("/actions", ident)
            action = actions[ident]
            terminal_sites = [item["completion"], *(exit_["site"] for exit_ in item["exits"])]
            require(
                len({value_key(site) for site in terminal_sites}) == len(terminal_sites),
                "duplicate_action_boundary",
                path,
                "A single physical boundary cannot stand for two exits",
            )
            source.site(item["entry"], path + "/entry")
            source.site(item["completion"], path + "/completion")
            require(
                item["entry"]["phase"] == "enter",
                "action_entry_phase",
                path,
                "Entry must be the actual invocation start",
            )
            kind = action["completion"]["kind"]
            phases = {
                "return": {"return"},
                "commit": {"commit"},
                "acknowledgement": {"change", "commit"},
                "event": {"change", "decision"},
            }
            require(
                item["completion"]["phase"] in phases[kind],
                "completion_phase_differs",
                path + "/completion",
                "Observe the declared " + kind + " boundary",
            )

            def boundary(witness, site, expected_cases, location):
                value(witness, None, location)
                require(
                    {k: v for k, v in witness["observation"].items() if k != "path"} == site,
                    "completion_witness_site",
                    location,
                    "Read the exact observed boundary",
                )
                require(
                    set(witness["cases"]) == expected_cases,
                    "completion_witness_cases",
                    location,
                    "Every case for this physical boundary needs an independent native read",
                )

            boundary(
                item["completion_witness"],
                item["completion"],
                {c["id"] for c in item["cases"] if "complete" in c["boundaries"]},
                path + "/completion_witness",
            )
            exact_scope(
                action["parameters"],
                item["parameters"],
                "unbound_behavior_parameter",
                path + "/parameters",
            )
            for parameter, witness in item["parameters"].items():
                require(
                    "refinement_ref" not in witness,
                    "parameter_refinement_unsupported",
                    path,
                    "Parameter mappings need a separately defined correspondence",
                )
                value(witness, domains[action["parameters"][parameter]], pointer(path, parameter))
                require(
                    {c["id"] for c in item["cases"]} <= set(witness["cases"]),
                    "parameter_case_missing",
                    path,
                    "Observe arguments for every selected invocation path",
                )
                require(
                    bool(witness.get("source_parameter")),
                    "parameter_source_missing",
                    path,
                    "Name the actual source parameter; an abstract name is not a binding",
                )
                if index is not None:
                    node = source.nodes[witness["observation"]["node"]]
                    sid = node["source"]["path"] + "::" + node["source"]["symbol"]
                    symbol = index["symbols"][sid]
                    declared = {p["name"] for p in symbol.get("parameters", [])}
                    documented = symbol.get("documentation", {}).get("parameters", {})
                    name = witness["source_parameter"]
                    require(
                        name in declared and bool(documented.get(name, {}).get("description")),
                        "parameter_documentation_missing",
                        path,
                        name,
                    )
            kinds = [exit_["kind"] for exit_ in item["exits"]]
            require(
                len(kinds) == len(set(kinds)),
                "duplicate_action_exit",
                path,
                "An exit kind must have one explicit site",
            )
            for exit_ in item["exits"]:
                source.site(exit_["site"], path + "/exits")
                boundary(
                    exit_["witness"],
                    exit_["site"],
                    {c["id"] for c in item["cases"] if exit_["kind"] in c["boundaries"]},
                    path + "/exits/" + exit_["kind"],
                )
                require(
                    exit_["site"]["phase"] != "enter",
                    "action_exit_phase",
                    path,
                    "An entry is not an exit",
                )
                if exit_["kind"] == "exception":
                    require(
                        exit_["site"]["phase"] == "error",
                        "action_exception_phase",
                        path,
                        "Observe the actual exception boundary",
                    )
            outcomes = {kind for case in item["cases"] for kind in case["boundaries"]}
            require(
                outcomes == {"complete", *kinds},
                "action_exit_case_missing",
                path,
                "Every declared exit and the completion need an independent case",
            )

        for ident, item in binding["interactions"].items():
            path = pointer("/interactions", ident)
            interaction = interactions[ident]
            witnesses = item["witnesses"]
            pairs = [(w["action"], w["role"]) for w in witnesses]
            required = interaction_roles(interaction)
            require(
                len(pairs) == len(set(pairs)) and required == set(pairs),
                "interaction_witness_missing",
                path,
                "Each participating action needs its declared boundary witness",
            )
            for witness in witnesses:
                require(
                    witness["action"] in interaction["action_refs"],
                    "interaction_action_scope",
                    path,
                    witness["action"],
                )
                source.site(witness["site"], path)
                exact_scope(
                    interaction_fields(interaction, witness["role"]),
                    witness["fields"],
                    "interaction_field_scope",
                    path,
                )
                for name, field in witness["fields"].items():
                    boundary(field, witness["site"], set(witness["cases"]), pointer(path, name))
                cases(witness["cases"], path)
                require(
                    set(witness["cases"])
                    <= {c["id"] for c in binding["actions"][witness["action"]]["cases"]},
                    "interaction_case_scope",
                    path,
                    "Witness cases must exercise their owning action",
                )

        return {
            "valid": True,
            "errors": [],
            "status": "declared",
            "definition_sha256": definition["definition_sha256"],
            "source": "checked" if index is not None else "not_checked",
            "cases": "checked" if case_ids is not None else "not_checked",
            "native_semantics": "existing_concept_binding_gate_required",
            "runtime": "not_checked",
            "sources": sorted(source.sources),
            "models": {
                ref: {
                    "variables": [v["id"] for v in variables.values() if v["owner"] == ref],
                    "actions": [a["id"] for a in actions.values() if ref in a["model_refs"]],
                    "interactions": [
                        i["id"] for i in interactions.values() if ref in i["model_refs"]
                    ],
                }
                for ref in contract["scope"]["model_refs"]
            },
        }
    except ContractError as error:
        return {"valid": False, "status": "invalid_binding", "errors": [error.diagnostic.as_dict()]}
