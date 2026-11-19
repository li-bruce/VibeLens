"""Resolve cross-model boundaries without inventing a second execution engine.

Resource and join semantics are read from the canonical state/activity registry.
Other records describe obligations for later native witnesses; a valid declaration
does not prove delivery, consistency or transaction atomicity in an application.
"""

from copy import deepcopy

from .diagnostics import index_records, require
from .references import require_reference


def load_interactions(contract, registry, dependencies, domains, variables, actions, assumptions):
    """Validate endpoints, ownership and completion boundaries for every interaction."""
    records = contract.get("interactions", [])
    indexed = index_records(records, "/interactions")
    selected = set(contract["scope"]["model_refs"] + contract["scope"]["object_refs"])
    normalized = {}
    for position, item in enumerate(records):
        path = f"/interactions/{position}"
        require(
            set(item["model_refs"]) <= selected,
            "interaction_scope",
            path + "/model_refs",
            "Interaction owner is outside the selected scope",
        )
        require(
            set(item["action_refs"]) <= set(actions),
            "unknown_action",
            path + "/action_refs",
            "Interaction action is not declared",
        )
        require(
            all(
                set(actions[ref]["model_refs"]) <= set(item["model_refs"])
                for ref in item["action_refs"]
            ),
            "interaction_action_owner",
            path,
            "Include the owners of every participating action",
        )

        def action_refs(refs, field):
            require(
                set(refs) <= set(item["action_refs"]),
                "interaction_action_scope",
                path + "/" + field,
                "Endpoint must belong to the interaction's actions",
            )

        def domain_ref(field):
            ref = item[field]
            require(ref in domains, "unknown_domain", path + "/" + field, ref)
            return domains[ref]

        def completion(field, kind):
            action_refs([item[field]], field)
            require(
                actions[item[field]]["completion"]["kind"] == kind,
                "completion_boundary",
                path + "/" + field,
                "Completion must reference an actual declared " + kind + " boundary",
            )

        def assumption_refs():
            refs = item["assumption_refs"]
            require(
                set(refs) <= set(assumptions),
                "unknown_assumption",
                path + "/assumption_refs",
                "Interaction assumption is not declared",
            )
            return refs

        canonical = None
        kind = item["kind"]
        if kind == "shared_read":
            ref = item["variable_ref"]
            require(ref in variables, "unknown_variable", path + "/variable_ref", ref)
            require(
                variables[ref]["owner"] in item["model_refs"],
                "interaction_owner",
                path,
                "Include the authoritative owner of the shared value",
            )
            action_refs(item["reader_actions"], "reader_actions")
            require(
                all(ref in actions[a]["reads"] for a in item["reader_actions"]),
                "interaction_read_missing",
                path,
                "Every reader must declare the shared read",
            )
            if item["consistency"] == "revision":
                revision = item.get("revision_variable")
                require(
                    revision in variables
                    and domains[variables[revision]["domain"]].kind
                    in {"integer", "string", "identity"},
                    "revision_variable",
                    path,
                    "Revision consistency needs a typed revision variable",
                )
                require(
                    all(revision in actions[a]["reads"] for a in item["reader_actions"]),
                    "revision_read_missing",
                    path,
                    "Readers must capture the revision",
                )
            else:
                require(
                    "revision_variable" not in item,
                    "interaction_fields",
                    path,
                    "Revision variable applies only to revision consistency",
                )
            if item["consistency"] == "transaction":
                require(
                    "completion_action" in item,
                    "completion_boundary",
                    path,
                    "Transactional consistency needs its commit boundary",
                )
                completion("completion_action", "commit")
            else:
                require(
                    "completion_action" not in item,
                    "interaction_fields",
                    path,
                    "Commit boundary applies only to transaction consistency",
                )
        elif kind == "handoff":
            action_refs([item["producer"], item["consumer"]], "producer")
            payload, queue = domain_ref("payload_domain"), domain_ref("queue_domain")
            require(
                queue.kind == "sequence" and queue.element.id == payload.id,
                "queue_payload",
                path,
                "Queue must be a sequence of the declared payload domain",
            )
            require(
                domain_ref("correlation_domain").kind == "identity",
                "correlation_domain",
                path,
                "Handoff correlation requires a model-qualified identity domain",
            )
            require(
                (item["retry"] == "bounded") == ("max_attempts" in item),
                "retry_bound",
                path,
                "Only bounded retries declare max_attempts",
            )
            refs = assumption_refs()
            require(
                item["delivery"] != "exactly_once"
                or (item["deduplication"] == "correlation" and bool(refs)),
                "delivery_assumption",
                path,
                "Exactly-once claims need deduplication and an explicit assumption",
            )
            if "acknowledgement_action" in item:
                completion("acknowledgement_action", "acknowledgement")
        elif kind in {"resource", "join"}:
            field = "resource_ref" if kind == "resource" else "join_ref"
            ref = item[field]
            canonical = require_reference(registry, ref, {kind}, path + "/" + field)
            owners = {r for r in dependencies[ref] if registry[r]["kind"] == "state_model"}
            require(
                owners <= set(item["model_refs"]),
                "interaction_owner",
                path,
                "Canonical activity owner must belong to the interaction",
            )
            if kind == "resource":
                action_refs(item["acquire_actions"] + item["release_actions"], "acquire_actions")
                identity = domain_ref("holder_domain")
            else:
                action_refs(item["arrival_actions"] + [item["release_action"]], "arrival_actions")
                identity = domain_ref("invocation_domain")
            require(
                identity.kind == "identity",
                "interaction_identity",
                path,
                "Resource holders and join invocations need typed identity domains",
            )
        elif kind == "transaction":
            action_refs(item["member_actions"], "member_actions")
            completion("completion_action", "commit")
            require(
                item["completion_action"] in item["member_actions"],
                "transaction_completion",
                path,
                "Commit must belong to this transaction",
            )
            refs = assumption_refs()
            require(
                item["atomicity"] != "external_protocol" or bool(refs),
                "atomicity_assumption",
                path,
                "External atomicity needs a stated protocol assumption",
            )
        normalized[item["id"]] = {
            "definition": deepcopy(item),
            "canonical_activity": deepcopy(canonical),
            "binding": "not_checked",
            "witnesses": "not_checked",
        }
    return indexed, normalized
