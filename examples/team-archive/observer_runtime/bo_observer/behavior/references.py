"""Resolve typed model and variable ownership through the canonical concept index."""

from ..concepts.common import encoded
from .diagnostics import index_records, require
from .domains import compatible


def require_reference(registry, ident, kinds, path):
    """Require a canonical ID of the requested kind; display aliases never bind."""
    require(ident in registry, "unknown_reference", path, ident)
    require(registry[ident]["kind"] in kinds, "reference_kind", path, ident)
    return registry[ident]


def load_variables(contract, registry, domains, discovery):
    """Give each selected state or fact one authoritative conceptual owner."""
    variables = index_records(contract["variables"], "/variables")
    selected_models = set(contract["scope"]["model_refs"])
    selected_objects = set(contract["scope"]["object_refs"])
    owners, canonical = {}, set()
    for position, variable in enumerate(contract["variables"]):
        path = f"/variables/{position}"
        domain_id, ref, owner = variable["domain"], variable["concept_ref"], variable["owner"]
        require(domain_id in domains, "unknown_domain", path + "/domain", domain_id)
        record = require_reference(registry, ref, {"state_model", "fact"}, path + "/concept_ref")
        require(ref not in canonical, "duplicate_variable_binding", path + "/concept_ref", ref)
        canonical.add(ref)
        if record["kind"] == "state_model":
            require(
                ref in selected_models and owner == ref,
                "variable_owner",
                path,
                "State is owned by its selected state model",
            )
            original = next(
                model for model in discovery["state_models"] if model["id"] == record["id"]
            )
            values = original["states"]
            # Hierarchy is still valid in the concept validator, but this first
            # contract slice cannot equate a configuration with a scalar state.
            require(
                all(isinstance(value, str) for value in values),
                "unsupported_state_domain",
                path,
                "Hierarchical configurations require an explicit value mapping",
            )
            require(
                domains[domain_id].kind == "enum"
                and {encoded(v) for v in values} == {encoded(v) for v in domains[domain_id].values},
                "state_domain_mismatch",
                path + "/domain",
                "Use the canonical model's exact state values",
            )
        else:
            from ..concepts.common import canonical_id

            actual_owner = canonical_id("object", record["object"])
            require(
                owner == actual_owner and owner in selected_objects,
                "variable_owner",
                path + "/owner",
                actual_owner,
            )
            require(
                compatible(domain_id, "$" + record["type"], domains),
                "variable_type",
                path + "/domain",
                "Domain differs from the canonical fact type",
            )
        owners[variable["id"]] = owner
    return variables, owners
