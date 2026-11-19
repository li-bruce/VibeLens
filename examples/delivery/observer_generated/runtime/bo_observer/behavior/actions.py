"""Check action frames and derive state changes from canonical transitions."""

from copy import deepcopy

from .diagnostics import index_records, require
from .domains import compatible
from .references import require_reference


def load_actions(contract, registry, domains, variables, owners, expressions, dependencies):
    """Validate frame conditions and native transition references before binding."""
    actions = index_records(contract["actions"], "/actions")
    summaries = {}
    selected = set(contract["scope"]["model_refs"]) | set(contract["scope"]["object_refs"])
    for position, action in enumerate(contract["actions"]):
        path = f"/actions/{position}"
        require(
            set(action["model_refs"]) <= selected,
            "action_scope",
            path + "/model_refs",
            "An action references an owner outside the selected scope",
        )
        for param, domain_id in action["parameters"].items():
            require(
                domain_id in domains, "unknown_domain", path + "/parameters/" + param, domain_id
            )
        writes, unchanged, reads = (set(action[name]) for name in ("writes", "unchanged", "reads"))
        require(
            not writes & unchanged and writes | unchanged == set(variables),
            "frame_partition",
            path,
            "Writes and unchanged must partition selected variables",
        )
        require(
            reads <= set(variables),
            "unknown_variable",
            path + "/reads",
            "Read variable is not selected",
        )
        require(
            all(owners[key] in action["model_refs"] for key in writes),
            "writer_outside_scope",
            path + "/writes",
            "Written variables must belong to an action owner",
        )
        derived = {}
        transition_ref = action.get("transition_ref")
        if transition_ref:
            transition = require_reference(
                registry, transition_ref, {"transition"}, path + "/transition_ref"
            )
            transition_owners = {
                ref
                for ref in dependencies[transition_ref]
                if registry[ref]["kind"] == "state_model"
            }
            require(
                transition_owners <= set(action["model_refs"]),
                "transition_owner",
                path + "/transition_ref",
                "Transition belongs to another model",
            )
            state_variables = {
                key
                for key, variable in variables.items()
                if variable["concept_ref"] in transition_owners
            }
            require(
                bool(state_variables),
                "transition_state_not_selected",
                path,
                "Select the referenced model's state variable",
            )
            if transition["dest"] is not None:
                derived = {
                    key: {
                        "op": "literal",
                        "domain": variables[key]["domain"],
                        "value": transition["dest"],
                    }
                    for key in state_variables
                }
            else:
                require(
                    state_variables <= unchanged,
                    "internal_transition_state_write",
                    path,
                    "An internal transition preserves its state",
                )
        state_writes = {
            key
            for key in writes
            if registry[variables[key]["concept_ref"]]["kind"] == "state_model"
        }
        require(
            state_writes == set(derived),
            "state_write_requires_transition",
            path + "/writes",
            "State updates come from their canonical transition",
        )
        require(
            not set(action["updates"]) & set(derived),
            "duplicate_transition_update",
            path + "/updates",
            "Do not redeclare a transition's destination as a second update",
        )
        require(
            set(action["updates"]) | set(derived) == writes,
            "update_partition",
            path + "/updates",
            "Every write needs an update or canonical transition",
        )
        actual_reads = set(
            expressions.expect_boolean(
                action["enabled"], path + "/enabled", parameters=action["parameters"]
            ).reads
        )
        if transition_ref:
            actual_reads.update((ident, "before") for ident in state_variables)
        for ident, update in action["updates"].items():
            result = expressions.check(
                update, path + "/updates/" + ident, parameters=action["parameters"]
            )
            require(
                compatible(result.domain, variables[ident]["domain"], domains),
                "update_type",
                path + "/updates/" + ident,
                "Update has the wrong value type",
            )
            actual_reads.update(result.reads)
        require(
            {ident for ident, _ in actual_reads} <= reads,
            "undeclared_read",
            path + "/reads",
            "Enablement and update reads must be declared",
        )
        summaries[action["id"]] = {
            "canonical_updates": derived,
            "transition_ref": transition_ref,
            "canonical_transition": deepcopy(registry[transition_ref]) if transition_ref else None,
            "completion": deepcopy(action["completion"]),
        }
    return actions, summaries
