"""Validate a language-neutral expression DAG before binding or execution.

Predicate definitions describe functions. Expression nodes bind their parameters.
Only nodes with the same identity share a result inside one evaluation.
"""

from __future__ import annotations

import hashlib
import json
import math
import re

TYPES = {"string", "boolean", "number"}
OPERATORS = {"input", "constant", "predicate", "all", "any", "not"}
IDENTITY = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,159}$")


def fingerprint(value):
    """Use portable JSON bytes to identify the complete declaration, not its label."""
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def matches(value, kind):
    return (
        (kind == "string" and isinstance(value, str) and len(value) <= 256)
        or (kind == "boolean" and type(value) is bool)
        or (
            kind == "number"
            and type(value) in (int, float)
            and math.isfinite(value)
            and abs(value) <= 9007199254740991
        )
    )


def records(values, name, *, allow_empty=False):
    if not isinstance(values, list) or (not values and not allow_empty):
        raise ValueError(name + " must be a nonempty list")
    result = {}
    for value in values:
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("id"), str)
            or not IDENTITY.fullmatch(value["id"])
        ):
            raise ValueError(name + " contains an invalid identity")
        if value["id"] in result:
            raise ValueError(name + " contains a duplicate identity: " + value["id"])
        result[value["id"]] = value
    return result


def provenance(value, name):
    refs = value.get("source_refs")
    if (
        not isinstance(refs, list)
        or not refs
        or any(not isinstance(ref, str) or not ref.strip() for ref in refs)
    ):
        raise ValueError(name + " needs conversation or existing-rule provenance")


def dependencies(node):
    if node["op"] == "predicate":
        return list(dict.fromkeys(node["arguments"].values()))
    return node.get("inputs", [])


def validate(policy, *, bound=True):
    """Reject malformed rules; return indexes and a dependency-first order.

    A draft can reserve predicate identities before source exists. It cannot pass
    the bound runtime gate. Business-flow loops are outside this expression DAG.
    """
    if not isinstance(policy, dict) or policy.get("schema") != "bo-policy/v1":
        raise ValueError("expected bo-policy/v1")
    if not isinstance(policy.get("revision"), str) or not policy["revision"].strip():
        raise ValueError("policy revision is required")
    if (
        not isinstance(policy.get("stage"), str)
        or policy.get("stage") not in {"draft", "bound"}
        or (bound and policy["stage"] != "bound")
    ):
        raise ValueError("runtime policy must be bound")
    inputs = policy.get("inputs")
    if not isinstance(inputs, dict) or any(
        not isinstance(k, str)
        or not IDENTITY.fullmatch(k)
        or not isinstance(v, str)
        or v not in TYPES
        for k, v in inputs.items()
    ):
        raise ValueError("policy inputs need named portable scalar types")
    predicates = records(policy.get("predicates"), "predicates", allow_empty=True)
    nodes = records(policy.get("nodes"), "policy nodes")
    operations = records(policy.get("operations"), "policy operations")
    if len(nodes) > 4096:
        raise ValueError("policy expression budget exceeded (4096 nodes)")
    for pred in predicates.values():
        provenance(pred, pred["id"])
        parameters = pred.get("parameters")
        if not isinstance(parameters, dict) or any(
            not isinstance(k, str)
            or not IDENTITY.fullmatch(k)
            or not isinstance(v, str)
            or v not in TYPES
            for k, v in parameters.items()
        ):
            raise ValueError("invalid predicate parameters: " + pred["id"])
        source = pred.get("source")
        if bound or source is not None:
            if (
                not isinstance(source, dict)
                or set(source) != {"path", "symbol"}
                or not all(isinstance(v, str) and v.strip() for v in source.values())
                or source["path"].startswith(("/", "\\"))
                or ":" in source["path"]
                or ".." in source["path"].replace("\\", "/").split("/")
            ):
                raise ValueError(
                    "predicate needs a project-relative source function: " + pred["id"]
                )
    output_types = {}
    used_predicates = set()
    for node in nodes.values():
        provenance(node, node["id"])
        op = node.get("op")
        if not isinstance(op, str) or op not in OPERATORS:
            raise ValueError("unsupported policy operator: " + str(op))
        fields = {"id", "op", "label", "summary", "source_refs"}
        fields |= (
            {"name"}
            if op == "input"
            else (
                {"value", "type"}
                if op == "constant"
                else {"predicate", "arguments"} if op == "predicate" else {"inputs"}
            )
        )
        if set(node) - fields:
            raise ValueError("unknown policy node fields: " + node["id"])
        if op == "input":
            if not isinstance(node.get("name"), str) or node.get("name") not in inputs:
                raise ValueError("undefined policy input: " + node["id"])
            output_types[node["id"]] = inputs[node["name"]]
        elif op == "constant":
            if (
                not isinstance(node.get("type"), str)
                or node.get("type") not in TYPES
                or not matches(node.get("value"), node["type"])
            ):
                raise ValueError("constant type differs: " + node["id"])
            output_types[node["id"]] = node["type"]
        elif op == "predicate":
            pred = (
                predicates.get(node.get("predicate"))
                if isinstance(node.get("predicate"), str)
                else None
            )
            args = node.get("arguments")
            if (
                not pred
                or not isinstance(args, dict)
                or set(args) != set(pred["parameters"])
                or any(not isinstance(ref, str) for ref in args.values())
            ):
                raise ValueError("predicate argument names differ: " + node["id"])
            used_predicates.add(pred["id"])
            output_types[node["id"]] = "boolean"
        else:
            refs = node.get("inputs")
            if (
                not isinstance(refs, list)
                or not refs
                or any(not isinstance(r, str) for r in refs)
                or len(set(refs)) != len(refs)
                or (op == "not" and len(refs) != 1)
            ):
                raise ValueError("invalid operator arity: " + node["id"])
            output_types[node["id"]] = "boolean"
    if used_predicates != set(predicates):
        raise ValueError("unreferenced predicate definitions")
    order, visiting, done = [], set(), set()

    def visit(ident):
        if len(visiting) >= 128:
            raise ValueError("policy dependency depth budget exceeded (128)")
        if not isinstance(ident, str) or ident not in nodes:
            raise ValueError("dangling policy dependency: " + str(ident))
        if ident in visiting:
            raise ValueError("policy expression cycle: " + ident)
        if ident in done:
            return
        visiting.add(ident)
        node = nodes[ident]
        for dependency in dependencies(node):
            visit(dependency)
        if node["op"] in {"all", "any", "not"} and any(
            output_types[r] != "boolean" for r in node["inputs"]
        ):
            raise ValueError("logical operator needs Boolean expressions: " + ident)
        if node["op"] == "predicate":
            pred = predicates[node["predicate"]]
            if any(
                output_types[r] != pred["parameters"][arg] for arg, r in node["arguments"].items()
            ):
                raise ValueError("predicate argument types differ: " + ident)
        visiting.remove(ident)
        done.add(ident)
        order.append(ident)

    for operation in operations.values():
        provenance(operation, operation["id"])
        if bound and (not operation.get("business_nodes") or not operation.get("cases")):
            raise ValueError(
                "bound operation needs business nodes and verification cases: " + operation["id"]
            )
        for field in ("business_nodes", "cases"):
            values = operation.get(field, [])
            if (
                not isinstance(values, list)
                or any(not isinstance(v, str) or not v for v in values)
                or len(values) != len(set(values))
            ):
                raise ValueError("invalid operation " + field)
        visit(operation.get("root"))
        if output_types[operation["root"]] != "boolean":
            raise ValueError("operation root must produce a Boolean decision")
    if done != set(nodes):
        raise ValueError("unreachable policy expressions: " + ", ".join(sorted(set(nodes) - done)))
    return {
        "nodes": nodes,
        "predicates": predicates,
        "operations": operations,
        "order": order,
        "types": output_types,
    }
