"""Separate intent, definitions, mapping, capture and outcome coverage.

Denominators come from the complete configured contract and protected checks,
never the visible graph. Missing evidence is pending, not an empty successful run.
"""

from collections import defaultdict
from urllib.parse import quote
from ..concepts.common import canonical_id

from .contract import assess
from .bindings import assess_bindings
from .evidence import applicability
from .iteration import SECTIONS


def key(kind, *parts):
    """Keep coverage identities unambiguous when user IDs contain separators."""
    return kind + "/" + "/".join(quote(str(part), safe="") for part in parts)


def section(expected, checked=(), *, errors=(), required=True, scope="", evidence=None):
    """Build an explicit denominator and keep failed execution separate from absence."""
    expected, checked = set(expected), set(checked)
    missing = expected - checked
    status = (
        "failed" if errors else "pending" if missing else "passed" if expected else "not_applicable"
    )
    return {
        "status": status,
        "required": required,
        "scope": scope,
        "expected": sorted(expected),
        "checked": sorted(expected & checked),
        "missing": sorted(missing),
        "errors": list(errors),
        "coverage": {"required": len(expected), "checked": len(expected & checked)},
        "evidence": evidence,
    }


def capture_scope(contract, binding):
    """List every declared value/case and action/boundary requirement independently."""
    expected, parents = set(), defaultdict(set)

    def value(ident, item, parent):
        for case in item.get("cases", []):
            identity = key("value", ident, case)
            expected.add(identity)
            parents[parent].add(identity)

    for variable in contract["variables"]:
        ident = variable["id"]
        parents[key("variable", ident)]
        value(
            canonical_id("variable", ident),
            binding.get("variables", {}).get(ident, {}),
            key("variable", ident),
        )
    for action in contract["actions"]:
        ident = action["id"]
        item = binding.get("actions", {}).get(ident, {})
        parent = key("action", ident)
        parents[parent]
        value(canonical_id("completion", ident), item.get("completion_witness", {}), parent)
        for name, witness in item.get("parameters", {}).items():
            value(canonical_id("parameter", ident, name), witness, parent)
        for exit_ in item.get("exits", []):
            value(canonical_id("exit", ident, exit_["kind"]), exit_["witness"], parent)
        for case in item.get("cases", []):
            identity = key("boundary", ident, case["id"])
            expected.add(identity)
            parents[parent].add(identity)
    for interaction in contract.get("interactions", []):
        ident = interaction["id"]
        parents[key("interaction", ident)]
        for witness in binding.get("interactions", {}).get(ident, {}).get("witnesses", []):
            for case in witness["cases"]:
                identity = key("interaction-case", ident, case)
                expected.add(identity)
                parents[key("interaction", ident)].add(identity)
    return expected | set(parents), parents


def capture_report(contract, binding, native):
    """Consume actual checker results; no values or lifetimes are fabricated."""
    expected, parents = capture_scope(contract, binding)
    checked = set()
    for value in native.get("values", []):
        if value["valid"] and value["checks"]:
            checked.add(key("value", value["id"], value["case"]))
    groups = defaultdict(list)
    for boundary in native.get("boundaries", []):
        groups[(boundary["action"], boundary["case"])].append(boundary)
    for (action, case), values in groups.items():
        if all(item["valid"] for item in values):
            checked.add(key("boundary", action, case))
    for item in native.get("interactions", {}).get("checks", []):
        if item["valid"] and item["witnesses"]:
            checked.add(key("interaction-case", item["interaction"], item["case"]))
    for parent, children in parents.items():
        if children and children <= checked:
            checked.add(parent)
    return section(
        expected,
        checked,
        errors=native.get("errors", []),
        scope="Selected native values and actual action/interaction boundaries",
    )


def reports(snapshot, original, *, formal_results=(), analysis_tools=None):
    """Add scoped reports without replacing any existing verification gate.

    Optional analysis failures are visible but do not stop native execution.
    A required profile with absent, stale or incomplete evidence blocks acceptance.
    """
    contract = snapshot.get("behavior")
    if contract is None:
        return {"configured": False, "categories": {}, "blocking": []}
    definition = assess(contract, snapshot["behavior_discovery"])
    ids = [section + "/" + item["id"] for section in SECTIONS for item in contract.get(section, [])]
    defined = definition["valid"] and not definition.get("unresolved")
    cases = {c["case"] for c in snapshot["acceptance"].get("checks", [])}
    binding = assess_bindings(
        contract,
        snapshot["behavior_discovery"],
        snapshot["model"],
        index=snapshot["structure"],
        case_ids=cases,
    )
    mapped = [
        prefix + "/" + item["id"]
        for prefix in ("variables", "actions", "interactions")
        for item in contract.get(prefix, [])
    ]
    concept = original.get("concepts", {})
    model_refs = contract["scope"]["model_refs"]
    native = original.get("mapping", {}).get("behavior", {})
    categories = {
        "intent": section(
            model_refs,
            model_refs if concept.get("status") == "passed" else [],
            errors=concept.get("errors", []),
            scope="Recorded scoped model agreement",
        ),
        "definition": section(
            ids,
            ids if defined else [],
            errors=definition.get("errors", []),
            scope="Strict definition and reference validation",
        ),
        "mapping": section(
            mapped,
            mapped if binding["valid"] else [],
            errors=binding["errors"],
            scope="Independent owned-source scan and declared capture/case bindings",
        ),
        "capture": capture_report(contract, snapshot["model"].get("behavior_bindings", {}), native),
    }
    domain_errors = [
        finding
        for finding in native.get("domain_findings", [])
        if finding["status"] == "outside_application_domain"
    ]
    rule = original.get("state_rules", {})
    states = [m for m in model_refs if m.startswith("state-model:")]
    categories["state_rules"] = section(
        states,
        states if rule.get("status") == "passed" and native.get("valid") else [],
        errors=[*rule.get("errors", []), *domain_errors],
        scope="Configured native state checks and actual application value domains",
    )
    categories["state_rules"]["analysis_domain_findings"] = [
        f for f in native.get("domain_findings", []) if f["status"] == "outside_analysis_domain"
    ]
    modes = (snapshot.get("verification_contract") or {}).get("probe_modes") or [
        "on",
        "off",
        "fault",
    ]
    checks = [
        c["id"] + "/" + mode for c in snapshot["acceptance"].get("checks", []) for mode in modes
    ]
    business = original.get("business", {})
    verified = business.get("status") == "passed" and business.get("assertions", {}).get(
        "executed"
    ) == len(checks)
    categories["business"] = section(
        checks,
        checks if verified else [],
        errors=business.get("errors", []),
        scope="Independent configured business expectations in every required mode",
    )
    commands = (snapshot.get("verification_contract") or {}).get("test_commands") or []
    ids = ["command/" + str(i) for i in range(len(commands))]
    project = original.get("project_checks", {})
    categories["project_checks"] = section(
        ids,
        ids if project.get("status") == "passed" else [],
        errors=project.get("errors", []),
        scope="Original project, architecture and viewer checks",
    )
    formal = {}
    for profile in snapshot.get("analysis_profiles", []):
        key = profile["id"]
        subject = profile.get("subject", "design_model")
        candidates = [
            r
            for r in formal_results
            if isinstance(r, dict)
            and r.get("roots") == ["profile/" + key]
            and r.get("subject") == "design_model"
            and subject == "design_model"
        ]
        identities = (analysis_tools or {}).get(key)

        # The artifact reader may verify several Java installations. Keep every
        # current result; filesystem/UUID order must not hide conflicting proofs.
        def expected_tool(receipt):
            if isinstance(identities, list):
                return receipt["tool_identity"] if receipt["tool_identity"] in identities else {}
            return identities

        current = [
            (r, applicability(r, snapshot, tool_identity=expected_tool(r))) for r in candidates
        ]
        outcomes = {r["outcome"] for r, fresh in current if fresh["current"]}
        passing = outcomes == {"pass"}
        formal[key] = section(
            profile["property_refs"],
            profile["property_refs"] if passing else [],
            required=profile["required_for_acceptance"],
            scope="Finite design model, profile " + key,
            evidence=[fresh for _, fresh in current],
        )
        if len(outcomes) > 1:
            formal[key].update(
                status="failed", errors=["Conflicting results for the same current dependencies"]
            )
        elif outcomes and not passing:
            outcome = next(iter(outcomes))
            formal[key]["status"] = {
                "fail": "failed",
                "error": "error",
                "incomplete": "incomplete",
                "unsupported": "unsupported",
                "pending": "pending",
            }[outcome]
        if subject != "design_model":
            formal[key].update(
                status="unsupported", errors=["No implementation-model analysis adapter"]
            )
    categories["formal_analysis"] = {
        "profiles": formal,
        "status": "not_configured" if not formal else "scoped",
    }
    blocking = [
        name
        for name, value in categories.items()
        if value.get("required") and value["status"] not in {"passed", "not_applicable"}
    ]
    blocking += [
        "formal_analysis/" + key
        for key, value in formal.items()
        if value["required"] and value["status"] != "passed"
    ]
    return {
        "configured": True,
        "categories": categories,
        "blocking": blocking,
        "scope": contract["scope"],
        "meaning": "Separate configured evidence categories; not exhaustive software correctness",
    }
