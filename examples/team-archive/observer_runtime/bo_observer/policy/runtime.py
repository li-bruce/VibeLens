"""Optional native rule execution; the observer never calls it to invent facts.

The application explicitly supplies predicate callables and a request fact basis.
There is no eval(), dynamic import, database access or process-global result cache.
"""

from __future__ import annotations

import inspect
import uuid
from copy import deepcopy

from .definition import validate, fingerprint, matches
from .bindings import callable_binding


def combine(op, values):
    """Three-valued composition; predicate errors remain separate diagnostics."""
    if op == "not":
        return None if values[0] is None else not values[0]
    decisive = False if op == "all" else True
    if any(value is decisive for value in values):
        return decisive
    if any(value is None for value in values):
        return None
    return not decisive


def evaluate(
    policy, operation, inputs, callbacks, *, fact_revision, source_root, check_id=None, on_step=None
):
    """Evaluate one operation, sharing identical nodes only within this check.

    A change of input or fact revision requires a new check. Callers decide what
    business action to take; unknown/error evidence never becomes a fabricated deny.
    """
    index = validate(policy)
    if not isinstance(operation, str) or operation not in index["operations"]:
        raise ValueError("unknown policy operation")
    if not isinstance(fact_revision, str) or not fact_revision:
        raise ValueError("a fact revision or explicit request-basis identity is required")
    if not isinstance(inputs, dict) or set(inputs) - set(policy["inputs"]):
        raise ValueError("undeclared policy inputs")
    for key, value in inputs.items():
        if not matches(value, policy["inputs"][key]):
            raise ValueError("policy input type differs: " + key)
    inputs = deepcopy(inputs)
    bindings = {}
    for pred in index["predicates"].values():
        callback = callbacks.get(pred["id"])
        if not callable(callback):
            raise ValueError("missing native predicate: " + pred["id"])
        try:
            inspect.signature(callback).bind(**{name: None for name in pred["parameters"]})
        except (ValueError, TypeError) as exc:
            raise ValueError("native predicate signature differs: " + pred["id"]) from exc
        bindings[pred["id"]] = callable_binding(callback, pred["source"], source_root)
    check_id = check_id or uuid.uuid4().hex
    if not isinstance(check_id, str) or not check_id:
        raise ValueError("invalid check identity")
    cache, trace, diagnostics = {}, [], []

    def compute(ident):
        if ident in cache:
            return cache[ident]
        node = index["nodes"][ident]
        op, used, skipped, arguments = node["op"], [], [], {}
        status = "completed"
        if op == "input":
            value = inputs.get(node["name"])
            if node["name"] not in inputs:
                status = "unknown"
        elif op == "constant":
            value = node["value"]
        elif op == "predicate":
            for argument, reference in node["arguments"].items():
                arguments[argument] = compute(reference)
                if reference not in used:
                    used.append(reference)
            if any(value is None for value in arguments.values()):
                value, status = None, "unknown"
            else:
                try:
                    value = callbacks[node["predicate"]](**arguments)
                    if value is not None and type(value) is not bool:
                        raise ValueError("predicate did not return Boolean or unknown")
                    status = "unknown" if value is None else "completed"
                except Exception as exc:
                    value, status = None, "error"
                    diagnostics.append({"node": ident, "error": type(exc).__name__})
        else:
            values = []
            for offset, reference in enumerate(node["inputs"]):
                values.append(compute(reference))
                used.append(reference)
                if (op == "all" and values[-1] is False) or (op == "any" and values[-1] is True):
                    skipped = node["inputs"][offset + 1 :]
                    break
            value = combine(op, values)
            status = "unknown" if value is None else "completed"
        step = {
            "node": ident,
            "value": value,
            "status": status,
            "arguments": arguments,
            "used": used,
            "skipped": skipped,
        }
        cache[ident] = value
        trace.append(step)
        if on_step:
            try:
                on_step(deepcopy(step))
            except Exception:
                # Observation transport failures cannot change a business result.
                diagnostics.append({"node": ident, "error": "observation_sink_failed"})
        return value

    root = index["operations"][operation]["root"]
    value = compute(root)
    return {
        "schema": "bo-policy-evaluation/v1",
        "policy_revision": policy["revision"],
        "policy_hash": fingerprint(policy),
        "check_id": check_id,
        "fact_revision": fact_revision,
        "operation": operation,
        "inputs": deepcopy(inputs),
        "bindings": bindings,
        "root": root,
        "value": value,
        "decision": "allow" if value is True else "deny" if value is False else "unknown",
        "trace": trace,
        "diagnostics": diagnostics,
    }
