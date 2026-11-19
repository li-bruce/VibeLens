"""Validate independent expectations and their explicitly stated assumptions."""

from copy import deepcopy

from .diagnostics import index_records, require


def load_assumptions(contract, sources, actions):
    """Retain human/project-rule review separately from an agent's declaration."""
    records = contract.get("assumptions", [])
    assumptions = index_records(records, "/assumptions")
    selected = set(contract["scope"]["model_refs"])
    for position, item in enumerate(records):
        path = f"/assumptions/{position}"
        require(
            set(item["model_refs"]) <= selected,
            "assumption_scope",
            path + "/model_refs",
            "Assumption models must belong to the selected scope",
        )
        require(
            set(item["action_refs"]) <= set(actions),
            "unknown_action",
            path + "/action_refs",
            "Assumption references an undeclared action",
        )
        refs = item["review_source_refs"]
        require(
            all(
                set(actions[ref]["model_refs"]) <= set(item["model_refs"])
                for ref in item["action_refs"]
            ),
            "assumption_action_owner",
            path,
            "An assumption must include the owners of its selected actions",
        )
        require(
            all(ref in sources for ref in refs),
            "unknown_source",
            path + "/review_source_refs",
            "Review source is not recorded",
        )
        require(
            item["status"] != "confirmed"
            or (
                bool(refs) and all(sources[ref]["kind"] in {"user", "project_rule"} for ref in refs)
            ),
            "assumption_confirmation",
            path,
            "Confirmed assumptions require recorded user or adopted project-rule evidence",
        )
    return assumptions


def load_properties(contract, actions, assumptions, expressions):
    """Keep properties outside enablement; progress has explicit scheduling scope."""
    properties = index_records(contract["properties"], "/properties")
    for position, item in enumerate(contract["properties"]):
        path = f"/properties/{position}"
        require(
            set(item["action_refs"]) <= set(actions),
            "unknown_action",
            path + "/action_refs",
            "Property action is not declared",
        )
        require(
            bool(item["action_refs"]) == (item["kind"] == "transition_constraint"),
            "property_scope",
            path + "/action_refs",
            "Transition constraints select actions; other properties apply to selected state",
        )
        refs = item.get("assumption_refs", [])
        require(
            set(refs) <= set(assumptions),
            "unknown_assumption",
            path + "/assumption_refs",
            "Property assumptions must be declared",
        )
        if item["kind"] == "progress_property":
            require(
                "trigger" in item and "fairness" in item,
                "progress_definition",
                path,
                "Progress needs a trigger, eventual condition and explicit fairness",
            )
            require(
                item["fairness"] == "none"
                or any(assumptions[ref]["kind"] == "scheduling" for ref in refs),
                "fairness_assumption",
                path + "/assumption_refs",
                "Weak/strong fairness needs a scheduling assumption",
            )
            expressions.expect_boolean(item["trigger"], path + "/trigger")
        else:
            require(
                "trigger" not in item and "fairness" not in item,
                "property_fields",
                path,
                "Only progress properties define trigger and fairness",
            )
        expressions.expect_boolean(
            item["expression"],
            path + "/expression",
            allow_after=item["kind"] == "transition_constraint",
        )
    return deepcopy(properties)
