"""Typed semantic dependencies for impact and evidence freshness.

This is a derived index of existing declarations, not another editable model.
Edges mean that a consumer depends on a declaration. They never establish a
runtime call or a business route. The canonical loaders validate definitions.
"""

from copy import deepcopy
from collections import defaultdict, deque

from ..concepts.common import digest, without_display
from ..concepts.model import build


def expression_refs(value):
    """Read references from expression operators, preserving literal payloads."""
    if not isinstance(value, dict) or "op" not in value:
        return set()
    refs = set()
    if value["op"] == "var":
        refs.add("variable/" + value["id"])
    elif value["op"] == "policy_ref":
        refs.add("concept/" + value["id"])
    if "domain" in value:
        refs.add("domain/" + value["domain"])
    if value["op"] != "literal":
        for arg in value.get("args", []):
            refs.update(expression_refs(arg))
        refs.update(expression_refs(value.get("body")))
        for arg in value.get("bindings", {}).values():
            refs.update(expression_refs(arg))
    return refs


def _record_refs(section, record):
    """Resolve only protocol reference fields; never treat arbitrary strings as IDs."""
    refs = set()
    for field, prefix in {
        "model_refs": "concept/",
        "object_refs": "concept/",
        "action_refs": "action/",
        "assumption_refs": "assumption/",
        "property_refs": "property/",
    }.items():
        refs.update(prefix + ref for ref in record.get(field, []))
    for field, prefix in {
        "concept_ref": "concept/",
        "owner": "concept/",
        "transition_ref": "concept/",
        "resource_ref": "concept/",
        "join_ref": "concept/",
        "object_ref": "concept/",
        "variable_ref": "variable/",
        "revision_variable": "variable/",
        "domain": "domain/",
    }.items():
        if field in record:
            refs.add(prefix + record[field])
    for field, value in record.items():
        if field.endswith("_domain") and isinstance(value, str):
            refs.add("domain/" + value)
    for field in ("expression", "enabled", "predicate", "condition", "initial", "trigger"):
        refs.update(expression_refs(record.get(field)))
    if section == "refinement":
        refs.add("action/" + record["completion_action"])
        refs.update("action/" + ref for ref in record["internal_actions"])
    if section == "initial_alternative":
        refs.update("variable/" + ref for ref in record["values"])
    if section == "action":
        refs.update("domain/" + domain for domain in record.get("parameters", {}).values())
        for field in ("reads", "writes", "unchanged"):
            refs.update("variable/" + ref for ref in record.get(field, []))
        for value in record.get("updates", {}).values():
            refs.update(expression_refs(value))
    return refs


def _native_definition(model):
    """Remove known display envelopes, retaining nested values and capture semantics."""
    value = without_display(model)
    for kind in ("nodes", "edges", "networks"):
        if kind in model:
            value[kind] = [without_display(item) for item in model[kind]]

    # State labels are a display dictionary. State values and transition targets
    # remain exact; a business payload with a field named "labels" is untouched.
    def machine(chart):
        return {key: item for key, item in without_display(chart).items() if key != "labels"}

    if "machine" in model:
        value["machine"] = machine(model["machine"])
    if "machines" in model:
        value["machines"] = {key: machine(chart) for key, chart in model["machines"].items()}
    if isinstance(value.get("policy"), dict):
        value["policy"] = without_display(value["policy"])
        for kind in ("nodes", "operations"):
            if kind in value["policy"]:
                value["policy"][kind] = [without_display(item) for item in value["policy"][kind]]
    bindings = value.get("behavior_bindings")
    if bindings:
        # The exact artifact pin is validated on load. Semantic dependencies below
        # decide reuse, so editing source citations alone cannot change an effect.
        value["behavior_bindings"] = {k: v for k, v in bindings.items() if k != "definition_sha256"}
    return value


def dependency_index(snapshot):
    """Return immutable fingerprints and exact prerequisites for one checked snapshot.

    Call after the normal schema/source gates. Missing dependencies are errors,
    not a smaller analysis scope. Invalid snapshots cannot produce evidence.
    """
    contract = snapshot.get("behavior")
    if contract is None:
        return {}
    data = build(snapshot["behavior_discovery"])
    index = {}

    def add(key, kind, value, refs=()):
        if key in index:
            raise ValueError("duplicate dependency: " + key)
        index[key] = {"kind": kind, "hash": digest(value), "requires": sorted(set(refs))}

    for ident, record in data["records"].items():
        add(
            "concept/" + ident,
            record["kind"],
            record,
            ("concept/" + ref for ref in data["dependencies"][ident]),
        )
    for plural, singular in (
        ("domains", "domain"),
        ("variables", "variable"),
        ("actions", "action"),
        ("properties", "property"),
        ("assumptions", "assumption"),
        ("interactions", "interaction"),
        ("refinements", "refinement"),
        ("initial_alternatives", "initial_alternative"),
    ):
        for record in contract.get(plural, []):
            add(
                singular + "/" + record["id"],
                singular,
                without_display(record),
                _record_refs(singular, record),
            )
    add("$scope", "scope", contract["scope"], _record_refs("scope", contract["scope"]))
    add("$initial", "initial", contract["initial"], expression_refs(contract["initial"]))
    # Global environmental assumptions can constrain otherwise independent actions.
    # Include them conservatively until a narrower reuse rule has differential tests.
    add(
        "$environment",
        "environment",
        {},
        [
            prefix + "/" + item["id"]
            for section, prefix in (
                ("assumptions", "assumption"),
                ("initial_alternatives", "initial_alternative"),
            )
            for item in contract.get(section, [])
        ],
    )
    for item in contract.get("actions", []):
        index["action/" + item["id"]]["requires"].extend(["$scope", "$initial", "$environment"])
    for item in contract.get("interactions", []):
        # A changed boundary affects every participant, including a producer whose
        # own action body is unchanged. This is dependency closure, not a DAG claim.
        for action in item["action_refs"]:
            index["action/" + action]["requires"].append("interaction/" + item["id"])
    for item in contract.get("refinements", []):
        index["variable/" + item["variable_ref"]]["requires"].append("refinement/" + item["id"])
    for profile in snapshot.get("analysis_profiles", []):
        add(
            "profile/" + profile["id"],
            "profile",
            profile,
            _record_refs("profile", profile) | {"$scope", "$initial", "$environment"},
        )
        # Every declared action in the selected models participates in exploration.
        index["profile/" + profile["id"]]["requires"].extend(
            "action/" + a["id"]
            for a in contract.get("actions", [])
            if set(a["model_refs"]) & set(profile["model_refs"])
        )
    owned = snapshot.get("source_inventory", {}).get("files", {})
    source = {p: snapshot.get("files", {}).get(p) for p in owned}
    add(
        "$native-source",
        "native_source",
        {
            "files": source,
            "structure": snapshot.get("structure"),
            "scope": snapshot.get("source_inventory", {}).get("scope_inputs", {}),
        },
    )
    add("$native-model", "native_model", _native_definition(snapshot.get("model", {})))
    add("$native-tools", "native_tools", snapshot.get("tools", {}))
    add(
        "$native-checks",
        "native_checks",
        {
            key: snapshot.get(key)
            for key in (
                "verification_contract",
                "acceptance",
                "mapping_contract",
                "whitebox",
                "stategraph_contract",
                "database_contract",
            )
        },
    )
    for key, item in index.items():
        item["requires"] = sorted(set(item["requires"]))
        missing = set(item["requires"]) - set(index)
        if missing:
            raise ValueError("unknown dependency for " + key + ": " + ", ".join(sorted(missing)))
    return index


def closure(index, roots):
    """Resolve prerequisites including cycles, without changing the index."""
    selected, pending = set(), list(roots)
    while pending:
        key = pending.pop()
        if key not in index:
            raise ValueError("unknown dependency: " + key)
        if key not in selected:
            selected.add(key)
            pending.extend(index[key]["requires"])
    return {key: deepcopy(index[key]) for key in sorted(selected)}


def impact(before, after):
    """Find changed declarations and their consumers in both revisions.

    Removed edges are still relevant to the old consumers. A display name or
    unchanged ID is never used as a semantic equivalence assertion.
    """
    old, new = dependency_index(before), dependency_index(after)
    changed = {key for key in set(old) | set(new) if old.get(key) != new.get(key)}
    consumers = defaultdict(set)
    for version in (old, new):
        for key, record in version.items():
            for ref in record["requires"]:
                consumers[ref].add(key)
    affected, pending = set(changed), deque(changed)
    while pending:
        for consumer in consumers[pending.popleft()] - affected:
            affected.add(consumer)
            pending.append(consumer)
    return {
        "changed": sorted(changed),
        "affected": sorted(affected),
        "removed": sorted(set(old) - set(new)),
        "added": sorted(set(new) - set(old)),
        "meaning": "Potential impact through declared prerequisites; not observed execution",
    }
