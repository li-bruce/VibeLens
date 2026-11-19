"""Export one selected property with deterministic source identities.

Each property gets its own specification so one property's scheduling assumption
cannot silently strengthen another property's check. Observation-only metadata
identifies the chosen action/parameters and checks transition postconditions;
it is excluded from the physical tuple used by fairness.
"""

from copy import deepcopy
from itertools import product

from ..capabilities import admit
from ...behavior import assess
from ...behavior.domains import load_domains
from ...concepts.common import digest
from ...concepts.model import build
from .values import literal, domain_expression, finite_values, ExportLimit
from .expressions import Translator

EXPORTER = "vibelens-tla-design/1"
MAX_ACTION_VARIANTS = 8192


def export_model(contract, discovery, profile, property_id=None):
    """Return generated text and a source map, or fail before invoking any tool."""
    admission = admit(contract, discovery, profile)
    if not admission["eligible"]:
        raise ValueError("Analysis admission: " + str(admission["diagnostics"]))
    chosen = property_id or (
        profile["property_refs"][0] if len(profile["property_refs"]) == 1 else None
    )
    if chosen not in profile["property_refs"]:
        raise ValueError("Select exactly one property for this analysis run")
    candidate = deepcopy(contract)
    for domain in candidate["domains"]:
        if domain["id"] in profile["bounds"]:
            bound = profile["bounds"][domain["id"]]
            domain.update({key: value for key, value in bound.items() if key != "origin"})
            domain["bound_origin"] = bound["origin"]
    defined = assess(candidate, discovery)
    domains = load_domains(candidate["domains"])
    variables = sorted(candidate["variables"], key=lambda item: item["id"])
    symbols = {item["id"]: "V" + str(index) for index, item in enumerate(variables)}
    translator = Translator(candidate, discovery, domains, symbols)
    dependencies = build(discovery)["dependencies"]
    prop = next(p for p in candidate["properties"] if p["id"] == chosen)
    lines = [
        "---- MODULE Model ----",
        "EXTENDS Integers, Sequences, FiniteSets",
        "VARIABLES " + ", ".join([*symbols.values(), "VLStep", "VLCheck"]),
        "physical == <<" + ", ".join(symbols.values()) + ">>",
        "vars == <<" + ", ".join([*symbols.values(), "VLStep", "VLCheck"]) + ">>",
    ]
    source_map = {
        "schema": "bo-tla-map/v1",
        "exporter": EXPORTER,
        "subject": "design_model",
        "definition_sha256": digest(contract),
        "analysis_definition_sha256": digest(candidate),
        "profile_sha256": digest(profile),
        "property": chosen,
        "variables": {},
        "actions": {},
        "assumptions": profile["assumption_refs"],
        "bounds": deepcopy(profile["bounds"]),
    }
    domain_checks = []
    for index, var in enumerate(variables):
        symbol = symbols[var["id"]]
        domain = domains[var["domain"]]
        check = "Type" + str(index)
        lines.append(check + " == " + symbol + " \\in " + domain_expression(domain))
        domain_checks.append(check)
        source_map["variables"][symbol] = {
            **deepcopy(var),
            "type_check": check,
            "domain_kind": domain.kind,
            "bound_origin": domain.bound_origin,
        }
    init = [
        *domain_checks,
        translator.expression(candidate["initial"]),
        *[
            symbols[key]
            + " = "
            + literal(value, domains[next(v["domain"] for v in variables if v["id"] == key)])
            for key, value in defined["canonical_initial_states"].items()
        ],
        "VLStep = -1",
        "VLCheck = TRUE",
    ]
    lines.append("Init ==\n  /\\ " + "\n  /\\ ".join(init))
    action_groups = {}
    for action in sorted(candidate["actions"], key=lambda item: item["id"]):
        parameters = sorted(action["parameters"])
        choices = [finite_values(domains[action["parameters"][key]]) for key in parameters]
        count = 1
        for choice in choices:
            count *= len(choice)
            if count + len(source_map["actions"]) > MAX_ACTION_VARIANTS:
                raise ExportLimit("Action parameter combinations exceed the export budget")
        for values in product(*choices):
            number = len(source_map["actions"])
            name = "A" + str(number)
            params = dict(zip(parameters, values))
            encoded = {
                key: literal(value, domains[action["parameters"][key]])
                for key, value in params.items()
            }
            expr = lambda item: translator.expression(item, encoded, action["parameters"])
            info = defined["action_definitions"][action["id"]]
            updates = {
                key: expr(value)
                for key, value in {**action["updates"], **info["canonical_updates"]}.items()
            }
            after = {key: updates.get(key, symbol) for key, symbol in symbols.items()}
            body = [expr(action["enabled"])]
            transition = info["canonical_transition"]
            if transition:
                owners = {
                    v["id"]
                    for v in variables
                    if v["concept_ref"] in dependencies[action["transition_ref"]]
                    and v["concept_ref"].startswith("state-model:")
                }
                for key in owners:
                    source = transition["source"]
                    sources = source if isinstance(source, list) else [source]
                    if "*" not in sources:
                        body.append(
                            symbols[key] + " \\in {" + ", ".join(literal(s) for s in sources) + "}"
                        )
            body.extend(symbols[key] + "' = " + after[key] for key in symbols)
            check = (
                translator.expression(prop["expression"], encoded, action["parameters"], after)
                if prop["kind"] == "transition_constraint" and action["id"] in prop["action_refs"]
                else "TRUE"
            )
            body.extend(["VLStep' = " + str(number), "VLCheck' = " + check])
            source_map["actions"][str(number)] = {
                "operator": name,
                "action": action["id"],
                "parameters": params,
                "transition_ref": action.get("transition_ref"),
                "line": len("\n".join(lines).splitlines()) + 1,
            }
            lines.append(name + " ==\n  /\\ " + "\n  /\\ ".join(body))
            action_groups.setdefault(action["id"], []).append(name)
    next_actions = [entry["operator"] for entry in source_map["actions"].values()]
    termination = profile.get("termination")
    if termination:
        lines.append("Terminal == " + translator.expression(termination["condition"]))
        lines.append("Finish == Terminal /\\ UNCHANGED vars")
        next_actions.append("Finish")
    lines.append("Next == " + (" \\/ ".join(next_actions) or "FALSE"))
    fairness = []
    if prop["kind"] == "progress_property" and prop["fairness"] != "none":
        assumptions = {item["id"]: item for item in candidate["assumptions"]}
        actions = {
            action
            for ref in prop.get("assumption_refs", [])
            if assumptions[ref]["kind"] == "scheduling"
            for action in assumptions[ref]["action_refs"]
        }
        for ident in sorted(actions):
            lines.append("Fair" + str(len(fairness)) + " == " + " \\/ ".join(action_groups[ident]))
            fairness.append(
                ("WF" if prop["fairness"] == "weak" else "SF")
                + "_physical(Fair"
                + str(len(fairness))
                + ")"
            )
    lines.append("Spec == Init /\\ [][Next]_vars" + "".join(" /\\ " + item for item in fairness))
    if prop["kind"] == "state_invariant":
        property_expression = translator.expression(prop["expression"])
    elif prop["kind"] == "transition_constraint":
        property_expression = "VLCheck"
    else:
        property_expression = (
            "("
            + translator.expression(prop["trigger"])
            + " ~> "
            + translator.expression(prop["expression"])
            + ")"
        )
    lines.extend(["CheckedProperty == " + property_expression, "===="])
    config = [
        "SPECIFICATION Spec",
        *["INVARIANT " + check for check in domain_checks],
        ("PROPERTY " if prop["kind"] == "progress_property" else "INVARIANT ") + "CheckedProperty",
    ]
    # No CONSTRAINT/ACTION_CONSTRAINT: properties never filter the explored graph.
    return {
        "tla": "\n".join(lines) + "\n",
        "cfg": "\n".join(config) + "\n",
        "source_map": source_map,
        "admission": admission,
        "contract": candidate,
    }
