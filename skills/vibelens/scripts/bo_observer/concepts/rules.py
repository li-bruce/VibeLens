"""Shared decision expressions retain semantics independently of source binding."""

from copy import deepcopy
from ..policy.definition import validate as validate_policy
from .common import canonical_id as cid, references, without_display


def policy_semantics(policy):
    """Retain operators, argument bindings and input types, not native/source metadata."""
    validate_policy(policy, bound=False)
    result = {"inputs": deepcopy(policy["inputs"])}
    omitted = {
        "predicates": {"source", "implementation_node"},
        "nodes": set(),
        "operations": {"business_nodes", "cases"},
    }
    for group, skip in omitted.items():
        result[group] = [
            without_display({k: v for k, v in item.items() if k not in skip})
            for item in sorted(policy[group], key=lambda x: x["id"])
        ]
    return result


def add_rules(graph, doc, sources):
    """Render each expression once, including shared inputs and operation results."""
    add, relation = graph.add, graph.relation
    policy = None
    if doc.get("policy"):
        policy = validate_policy(doc["policy"], bound=False)
        for group in ("predicates", "nodes", "operations"):
            for item in doc["policy"][group]:
                references(item, sources, "policy " + group + " " + item["id"])
        canonical = policy_semantics(doc["policy"])
        # Display text comes from the authored document. The canonical records
        # deliberately exclude it so translation never changes a rule identity.
        authored_labels = {
            group: {item["id"]: item.get("label") for item in doc["policy"][group]}
            for group in ("predicates", "operations")
        }
        for pred in canonical["predicates"]:
            add(
                cid("policy-predicate", pred["id"]),
                "rule_predicate",
                pred,
                label=authored_labels["predicates"][pred["id"]],
                aliases=[pred["id"]],
                layer="rules",
            )
        for item in canonical["nodes"]:
            ident = "policy:" + item["id"]
            deps = []
            if item["op"] == "predicate":
                deps = [
                    cid("policy-predicate", item["predicate"]),
                    *["policy:" + x for x in item["arguments"].values()],
                ]
            elif item["op"] in {"all", "any", "not"}:
                deps = ["policy:" + x for x in item["inputs"]]
            value = {
                **item,
                **(
                    {"input_type": canonical["inputs"][item["name"]]}
                    if item["op"] == "input"
                    else {}
                ),
            }
            add(
                ident,
                "rule_expression",
                value,
                label=next(
                    x.get("label", item["id"])
                    for x in doc["policy"]["nodes"]
                    if x["id"] == item["id"]
                ),
                aliases=[item["id"]],
                layer="rules",
                deps=deps,
                operator=item["op"],
            )
            for offset, dependency in enumerate(deps):
                relation(
                    cid("policy-dependency", item["id"], str(offset)),
                    dependency,
                    ident,
                    "guard" if item["op"] in {"all", "any", "not"} else "data",
                )
        for operation in canonical["operations"]:
            opid = cid("policy-operation", operation["id"])
            add(
                opid,
                "rule_operation",
                operation,
                label=authored_labels["operations"][operation["id"]],
                aliases=[operation["id"], "policy:operation:" + operation["id"]],
                layer="rules",
                deps=["policy:" + operation["root"]],
            )
            relation(
                cid("policy-result", operation["id"]),
                "policy:" + operation["root"],
                opid,
                "decision_result",
            )

    return policy
