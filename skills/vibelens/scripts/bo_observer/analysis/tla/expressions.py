"""Translate only typed, admitted expressions and canonical shared policy nodes."""

from ...behavior.expressions import Expressions
from ...behavior.policy_refs import PolicyReferences
from ...concepts.model import build
from .values import literal, domain_expression


class Translator:
    """No eval or application imports; all variable and operator names are generated."""

    def __init__(self, contract, discovery, domains, symbols):
        self.domains = domains
        self.variables = {item["id"]: item for item in contract["variables"]}
        self.symbols = symbols
        self.registry = build(discovery)["records"]
        self.checker = Expressions(
            domains,
            self.variables,
            PolicyReferences(self.registry, contract["scope"]["model_refs"]),
        )

    def expression(self, item, parameters=None, parameter_domains=None, after=None):
        parameters = parameters or {}
        parameter_domains = parameter_domains or {}
        op = item["op"]
        recurse = lambda value: self.expression(value, parameters, parameter_domains, after)
        if op == "literal":
            return literal(item["value"], self.domains[item["domain"]])
        if op == "var":
            return (
                (after or {}).get(item["id"], self.symbols[item["id"]] + "'")
                if item["phase"] == "after"
                else self.symbols[item["id"]]
            )
        if op == "param":
            return parameters[item["id"]]
        if op == "policy_ref":
            operation = self.registry[item["id"]]
            bindings = {name: recurse(value) for name, value in item["bindings"].items()}
            return self.policy("policy:" + operation["root"], bindings)
        if op in {"forall", "exists"}:
            symbol = "Q" + str(len(parameters))
            body = self.expression(
                item["body"],
                {**parameters, item["bind"]: symbol},
                {**parameter_domains, item["bind"]: item["domain"]},
                after,
            )
            return (
                "("
                + ("\\A" if op == "forall" else "\\E")
                + " "
                + symbol
                + " \\in "
                + domain_expression(self.domains[item["domain"]])
                + " : "
                + body
                + ")"
            )
        args = [recurse(arg) for arg in item["args"]]
        binary = {
            "eq": "=",
            "ne": "#",
            "lt": "<",
            "le": "<=",
            "add": "+",
            "sub": "-",
            "implies": "=>",
            "all": "/\\",
            "any": "\\/",
        }
        if op in binary:
            return "(" + (" " + binary[op] + " ").join(args) + ")"
        if op == "not":
            return "(~" + args[0] + ")"
        domain = None
        if op in {"length", "append", "tail", "set_add", "set_remove", "member", "select"}:
            operand = item["args"][1 if op == "member" else 0]
            domain = self.domains[
                self.checker.check(
                    operand, "/export", parameters=parameter_domains, allow_after=True
                ).domain
            ]
        if op == "length":
            return ("Cardinality" if domain.kind == "set" else "Len") + "(" + args[0] + ")"
        if op == "append":
            return "Append(" + ", ".join(args) + ")"
        if op == "tail":
            return "(IF Len(" + args[0] + ") = 0 THEN <<>> ELSE Tail(" + args[0] + "))"
        if op in {"set_add", "set_remove"}:
            return "(" + args[0] + (" \\cup " if op == "set_add" else " \\ ") + "{" + args[1] + "})"
        if op == "member":
            collection = (
                args[1]
                if domain.kind == "set"
                else "{" + args[1] + "[i] : i \\in DOMAIN " + args[1] + "}"
            )
            return "(" + args[0] + " \\in " + collection + ")"
        if op == "select" and domain.kind == "sequence":
            return (
                "(IF "
                + args[1]
                + " >= 0 /\\ "
                + args[1]
                + " < Len("
                + args[0]
                + ") THEN "
                + args[0]
                + "["
                + args[1]
                + " + 1] ELSE "
                + args[2]
                + ")"
            )
        raise ValueError("Unsupported admitted expression: " + op)

    def policy(self, ident, bindings):
        """Reuse canonical DAG identity and its exact input bindings; no predicate guesses."""
        node = self.registry[ident]
        op = node["op"]
        if op == "input":
            return bindings[node["name"]]
        if op == "constant":
            return literal(node["value"])
        parts = [self.policy("policy:" + ref, bindings) for ref in node.get("inputs", [])]
        if op == "not":
            return "(~" + parts[0] + ")"
        if op in {"all", "any"}:
            if not parts:
                return "TRUE" if op == "all" else "FALSE"
            return "(" + (" /\\ " if op == "all" else " \\/ ").join(parts) + ")"
        raise ValueError("Opaque policy node: " + ident)
