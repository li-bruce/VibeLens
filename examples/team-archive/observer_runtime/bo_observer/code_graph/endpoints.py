"""Extract literal HTTP registrations already identified by the source adapters."""

import ast
from ..observation.observation_scope import observer_route


def endpoints(symbol):
    """Preserve unknown/dynamic routes in source evidence instead of guessing URLs."""
    result = []
    for declaration in symbol.get("entrypoints", []):
        try:
            call = ast.parse(declaration, mode="eval").body
            if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
                continue
            verb = call.func.attr.lower()
            if verb not in {"get", "post", "put", "patch", "delete", "route", "websocket"}:
                continue
            path = (
                call.args[0]
                if call.args
                else next(k.value for k in call.keywords if k.arg == "path")
            )
            if not isinstance(path, ast.Constant) or not isinstance(path.value, str):
                continue
            if observer_route(path.value):
                continue
            methods = [verb.upper()] if verb != "route" else []
            if verb == "route":
                for keyword in call.keywords:
                    if keyword.arg == "methods":
                        value = ast.literal_eval(keyword.value)
                        if isinstance(value, (list, tuple)) and all(
                            isinstance(v, str) for v in value
                        ):
                            methods = [v.upper() for v in value]
            # A route decorator can use framework-specific defaults; do not assume GET.
            result.append({"path": path.value, "methods": methods, "declaration": declaration})
        except (SyntaxError, ValueError, TypeError, StopIteration, IndexError):
            continue
    return result
