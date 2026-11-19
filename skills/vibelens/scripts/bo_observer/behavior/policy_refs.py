"""Resolve shared policy inputs without copying or executing predicate functions."""

from .diagnostics import require
from .references import require_reference
from .domains import compatible


class PolicyReferences:
    """A read-only view of the already validated canonical policy DAG."""

    def __init__(self, registry, selected_models):
        self.registry = registry
        self.selected = set(selected_models)
        self.uses = {}

    def signature(self, ident, path):
        """Find reachable inputs and opaque predicates for exactly one operation."""
        operation = require_reference(self.registry, ident, {"rule_operation"}, path)
        require(
            ident in self.selected,
            "policy_scope",
            path,
            "Select the referenced rule operation in the contract scope",
        )
        inputs, predicates, seen = {}, set(), set()
        pending = ["policy:" + operation["root"]]
        while pending:
            ref = pending.pop()
            if ref in seen:
                continue
            seen.add(ref)
            node = self.registry[ref]
            if node["op"] == "input":
                inputs[node["name"]] = node["input_type"]
            elif node["op"] == "predicate":
                predicates.add(node["predicate"])
                pending.extend("policy:" + value for value in node["arguments"].values())
            else:
                pending.extend("policy:" + value for value in node.get("inputs", []))
        self.uses[ident] = {
            "input_types": inputs,
            "node_refs": sorted(seen),
            "opaque_predicates": sorted(predicates),
        }
        return inputs

    def check(self, expression, path, checker, options):
        """Bind every reachable input once and preserve its actual variable reads."""
        signature = self.signature(expression["id"], path + "/id")
        require(
            set(expression["bindings"]) == set(signature),
            "policy_bindings",
            path + "/bindings",
            "Bindings must match this operation's reachable inputs",
        )
        reads = set()
        for name, value in expression["bindings"].items():
            result = checker.check(value, path + "/bindings/" + name, **options)
            require(
                compatible(result.domain, "$" + signature[name], checker.domains),
                "policy_binding_type",
                path + "/bindings/" + name,
                "Binding differs from the canonical policy input type",
            )
            reads.update(result.reads)
        return frozenset(reads)
