"""Validate declared native-to-concept mappings without upgrading their evidence.

Mapping entries describe value correspondence. Whether the source actually emits
those values, and whether a property is preserved, require independent witnesses.
"""

from .diagnostics import index_records, pointer, require
from .expressions import UNKNOWN, known_value


def initial_alternatives(contract, variables, domains, expressions):
    """Check explicit recovery states; missing observations never become defaults."""
    values = contract.get("initial_alternatives", [])
    indexed = index_records(values, "/initial_alternatives")
    results = {}
    for number, item in enumerate(values):
        path = f"/initial_alternatives/{number}"
        require(
            set(item["values"]) == set(variables),
            "initial_value_scope",
            path + "/values",
            "A recovery alternative supplies every selected value",
        )
        for ref, value in item["values"].items():
            require(
                domains[variables[ref]["domain"]].accepts(value),
                "initial_value_type",
                pointer(path + "/values", ref),
                "Recovery value is outside its domain",
            )
        expressions.expect_boolean(item["condition"], path + "/condition")
        result = known_value(item["condition"], item["values"], expressions)
        require(
            result is not False,
            "empty_initial_alternative",
            path,
            "Recovery values contradict this alternative's predicate",
        )
        results[item["id"]] = "unresolved" if result is UNKNOWN else "consistent"
    return indexed, results


def load_refinements(contract, variables, domains, actions, properties):
    """Check mapping determinism, unknown handling and unchanged internal steps."""
    items = contract.get("refinements", [])
    index_records(items, "/refinements")
    results = {}
    for number, item in enumerate(items):
        path = f"/refinements/{number}"
        ref, concrete = item["variable_ref"], item["concrete_domain"]
        require(ref in variables, "unknown_variable", path + "/variable_ref", ref)
        require(concrete in domains, "unknown_domain", path + "/concrete_domain", concrete)
        require(
            set(item["property_refs"]) <= set(properties),
            "unknown_property",
            path,
            "Preservation expectations must reference declared properties",
        )
        require(
            item["completion_action"] in actions,
            "unknown_action",
            path + "/completion_action",
            "Completion action is not declared",
        )
        require(
            set(item["internal_actions"]) <= set(actions),
            "unknown_action",
            path,
            "Internal action is not declared",
        )
        require(
            all(ref in actions[a]["unchanged"] for a in item["internal_actions"]),
            "internal_step_changes_value",
            path + "/internal_actions",
            "An internal step must preserve the selected abstract value",
        )
        require(
            item["evidence_kind"] == "declared" or bool(item["evidence_refs"]),
            "refinement_evidence_missing",
            path,
            "A stronger evidence claim needs artifacts; their validity is checked separately",
        )
        before, after = domains[concrete], domains[variables[ref]["domain"]]
        mapping = item["mapping"]
        if mapping["kind"] == "identity":
            require(
                concrete == after.id,
                "identity_mapping_domain",
                path + "/mapping",
                "Identity mapping requires the exact same named domain",
            )
            coverage = "total"
        else:
            seen = set()
            for offset, entry in enumerate(mapping["entries"]):
                target = f"{path}/mapping/entries/{offset}"
                require(
                    before.accepts(entry["from"]) and after.accepts(entry["to"]),
                    "mapping_value_type",
                    target,
                    "Mapping entry differs from its declared domains",
                )
                key = before.value_key(entry["from"])
                require(
                    key not in seen,
                    "duplicate_mapping_input",
                    target,
                    "A concrete value has more than one mapping entry",
                )
                seen.add(key)
            size = before.finite_capability()
            coverage = (
                "total" if size["supported"] and size["cardinality"] == len(seen) else "partial"
            )
        results[item["id"]] = {
            "value_coverage": coverage,
            "claimed_evidence_kind": item["evidence_kind"],
            "evidence_status": "not_checked",
            "completion": actions[item["completion_action"]]["completion"],
        }
    return results
