"""Type-check a deliberately small JSON expression language without eval.

Expression traversal records the exact before/after reads. Action updates are
simultaneous: an update may only refer to pre-state values and typed parameters.
The analysis exporter and any later evaluator must declare their own capabilities.
"""

from dataclasses import dataclass

from .diagnostics import require
from .domains import compatible

UNKNOWN = object()


@dataclass(frozen=True)
class ExpressionType:
    domain: str
    reads: frozenset[tuple[str, str]] = frozenset()


class Expressions:
    """One contract's typed environment; no file access, native calls or side effects."""

    def __init__(self, domains, variables):
        self.domains = domains
        self.variables = variables

    def check(self, expression, path, *, parameters=None, allow_after=False, depth=0):
        """Return a type and read set, or a diagnostic with the exact JSON path."""
        require(depth < 64, "expression_depth", path, "Expression nesting exceeds 64")
        parameters = parameters or {}
        op = expression["op"]
        if op == "literal":
            domain = expression["domain"]
            require(domain in self.domains, "unknown_domain", path + "/domain", domain)
            require(
                self.domains[domain].accepts(expression["value"]),
                "literal_type",
                path + "/value",
                "Value is outside its declared domain",
            )
            return ExpressionType(domain)
        if op == "var":
            ident, phase = expression["id"], expression["phase"]
            require(ident in self.variables, "unknown_variable", path + "/id", ident)
            require(
                phase == "before" or allow_after,
                "after_state_not_allowed",
                path + "/phase",
                "Initial conditions, enablement and updates read pre-state only",
            )
            return ExpressionType(self.variables[ident]["domain"], frozenset({(ident, phase)}))
        if op == "param":
            ident = expression["id"]
            require(ident in parameters, "unknown_parameter", path + "/id", ident)
            return ExpressionType(parameters[ident])
        args = [
            self.check(
                arg,
                f"{path}/args/{number}",
                parameters=parameters,
                allow_after=allow_after,
                depth=depth + 1,
            )
            for number, arg in enumerate(expression["args"])
        ]
        reads = frozenset(read for arg in args for read in arg.reads)
        if op in {"all", "any", "not", "implies"}:
            require(
                all(compatible(arg.domain, "$boolean", self.domains) for arg in args),
                "expression_type",
                path,
                "Boolean operands required",
            )
            return ExpressionType("$boolean", reads)
        require(
            compatible(args[0].domain, args[1].domain, self.domains),
            "expression_type",
            path,
            "Operands have different types",
        )
        if op in {"eq", "ne"}:
            return ExpressionType("$boolean", reads)
        require(
            all(compatible(arg.domain, "$integer", self.domains) for arg in args),
            "expression_type",
            path,
            "Ordered and arithmetic operands require integers",
        )
        return ExpressionType("$boolean" if op in {"lt", "le"} else "$integer", reads)

    def expect_boolean(self, expression, path, **options):
        result = self.check(expression, path, **options)
        require(
            compatible(result.domain, "$boolean", self.domains),
            "expression_type",
            path,
            "A condition must be Boolean",
        )
        return result


def known_value(expression, values):
    """Partially evaluate a checked initial predicate using canonical start values.

    Unspecified facts stay unknown. This only finds definite contradictions; it
    does not solve arbitrary initialization constraints or execute an application.
    """
    op = expression["op"]
    if op == "literal":
        return expression["value"]
    if op == "var":
        return values.get(expression["id"], UNKNOWN)
    if op == "param":
        return UNKNOWN
    args = [known_value(arg, values) for arg in expression["args"]]
    if op == "all" and any(arg is False for arg in args):
        return False
    if op == "any" and any(arg is True for arg in args):
        return True
    if op == "implies" and (args[0] is False or args[1] is True):
        return True
    if any(arg is UNKNOWN for arg in args):
        return UNKNOWN
    if op == "all":
        return all(args)
    if op == "any":
        return any(args)
    if op == "not":
        return not args[0]
    if op == "implies":
        return not args[0] or args[1]
    if op in {"eq", "ne"}:
        from .domains import value_key

        equal = value_key(args[0]) == value_key(args[1])
        return equal if op == "eq" else not equal
    if op == "lt":
        return args[0] < args[1]
    if op == "le":
        return args[0] <= args[1]
    return args[0] + args[1] if op == "add" else args[0] - args[1]
