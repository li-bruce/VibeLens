"""Extract literal Python route registrations without importing the application.

Only statically identified Flask/FastAPI receivers and callable bindings resolve.
Computed paths and dynamic dispatch remain unknown. Methods omitted from source
stay unspecified because handler attributes can change framework defaults.
"""

import ast

ROUTERS = {"flask.Flask", "flask.Blueprint", "fastapi.FastAPI", "fastapi.APIRouter"}


def registrations(tree, path):
    """Track lexical names into factory functions and bound local handlers."""
    result = []

    def reference(node, names):
        if isinstance(node, ast.Name):
            return names.get(node.id)
        if isinstance(node, ast.Attribute):
            owner = reference(node.value, names)
            if owner and owner[0] == "module":
                return ("module", owner[1] + "." + node.attr)
            if owner and owner[0] in {"instance", "class"}:
                return ("callable", owner[1] + "." + node.attr)
        return None

    def assigned(node, names):
        if isinstance(node, ast.Call):
            constructor = reference(node.func, names)
            if constructor and constructor[1] in ROUTERS:
                return ("router", constructor[1])
            if constructor and constructor[0] in {"class", "module"}:
                return ("instance", constructor[1])
            return None
        return reference(node, names)

    def route(call, names, owner, handler_symbol=None):
        if not isinstance(call.func, ast.Attribute):
            return
        receiver = reference(call.func.value, names)
        verb = call.func.attr
        decorators = {
            "get",
            "post",
            "put",
            "patch",
            "delete",
            "head",
            "options",
            "route",
            "api_route",
            "websocket",
        }
        allowed = decorators if handler_symbol else {"add_url_rule", "add_api_route"}
        if not receiver or receiver[0] != "router" or verb not in allowed:
            return
        keywords = {value.arg: value.value for value in call.keywords if value.arg}
        route_path = (
            call.args[0]
            if call.args
            else keywords.get("rule" if verb in {"add_url_rule", "route"} else "path")
        )
        if not isinstance(route_path, ast.Constant) or not isinstance(route_path.value, str):
            return
        position, keyword = (2, "view_func") if verb == "add_url_rule" else (1, "endpoint")
        handler = call.args[position] if len(call.args) > position else keywords.get(keyword)
        target = ("callable", handler_symbol) if handler_symbol else reference(handler, names)
        methods = [verb.upper()] if handler_symbol and verb not in {"route", "api_route"} else []
        if "methods" in keywords:
            try:
                value = ast.literal_eval(keywords["methods"])
                if isinstance(value, (list, tuple, set)) and all(
                    isinstance(item, str) for item in value
                ):
                    methods = (
                        [item.upper() for item in value]
                        if handler_symbol
                        else sorted({item.upper() for item in value})
                    )
            except (ValueError, TypeError):
                pass
        result.append(
            {
                "path": route_path.value,
                "methods": methods,
                "declaration": ast.unparse(call),
                "handler": target[1] if target and target[0] in {"callable", "module"} else None,
                "handler_expression": ast.unparse(handler) if handler else "",
                "registration_kind": "decorator" if handler_symbol else "call",
                "receiver": ast.unparse(call.func.value),
                "framework": receiver[1],
                "source": {
                    "path": path,
                    "symbol": owner or "<module>",
                    "line": call.lineno,
                    "column": call.col_offset,
                    "end_line": call.end_lineno,
                    "end_column": call.end_col_offset,
                },
            }
        )

    def body(statements, inherited, owner="", method_outer=None):
        """Class attributes are not free variables captured by method bodies."""
        names = dict(inherited)
        for statement in statements:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbol = owner + "." + statement.name if owner else statement.name
                category = "class" if isinstance(statement, ast.ClassDef) else "callable"
                if category == "callable":
                    for decorator in statement.decorator_list:
                        if isinstance(decorator, ast.Call):
                            route(decorator, names, symbol, handler_symbol=symbol)
                names[statement.name] = (category, symbol)
                local = dict(
                    method_outer if category == "callable" and method_outer is not None else names
                )
                if category == "callable":
                    args = statement.args
                    for arg in [
                        *args.posonlyargs,
                        *args.args,
                        *args.kwonlyargs,
                        *[a for a in (args.vararg, args.kwarg) if a],
                    ]:
                        local[arg.arg] = None
                body(
                    statement.body,
                    local,
                    symbol,
                    method_outer=names if category == "class" else None,
                )
            elif isinstance(statement, ast.Import):
                for alias in statement.names:
                    names[alias.asname or alias.name.split(".")[0]] = (
                        "module",
                        alias.name if alias.asname else alias.name.split(".")[0],
                    )
            elif isinstance(statement, ast.ImportFrom):
                package = path.removesuffix(".py").split("/")[:-1]
                prefix = package[: len(package) - statement.level + 1] if statement.level else []
                module = ".".join(prefix + ([statement.module] if statement.module else []))
                for alias in statement.names:
                    names[alias.asname or alias.name] = (
                        "module",
                        ".".join(filter(None, [module, alias.name])),
                    )
            elif isinstance(statement, (ast.Assign, ast.AnnAssign)):
                value = assigned(statement.value, names) if statement.value else None
                targets = (
                    statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                )
                for target in targets:
                    for name in ast.walk(target):
                        if isinstance(name, ast.Name) and isinstance(name.ctx, ast.Store):
                            names[name.id] = value if isinstance(target, ast.Name) else None
            elif isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                route(statement.value, names, owner)
            elif isinstance(statement, ast.If):
                branches = [
                    body(statement.body, names, owner, method_outer),
                    body(statement.orelse, names, owner, method_outer),
                ]
                names = {
                    name: (
                        branches[0].get(name)
                        if branches[0].get(name) == branches[1].get(name)
                        else None
                    )
                    for name in set(branches[0]) | set(branches[1])
                }
            elif isinstance(
                statement, (ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)
            ):
                # Visit source declarations, but do not treat branch-dependent
                # assignments as an unconditional receiver/handler binding.
                local = dict(names)
                targets = []
                if isinstance(statement, (ast.For, ast.AsyncFor)):
                    targets.append(statement.target)
                if isinstance(statement, (ast.With, ast.AsyncWith)):
                    targets.extend(
                        item.optional_vars for item in statement.items if item.optional_vars
                    )
                for target in targets:
                    for name in ast.walk(target):
                        if isinstance(name, ast.Name):
                            local[name.id] = None
                blocks = [
                    (getattr(statement, name, []), local)
                    for name in ("body", "orelse", "finalbody")
                ]
                for handler in getattr(statement, "handlers", []):
                    context = dict(local)
                    if handler.name:
                        context[handler.name] = None
                    blocks.append((handler.body, context))
                for block, context in blocks:
                    changed = body(block, context, owner, method_outer)
                    for name in set(names) | set(changed):
                        if changed.get(name) != names.get(name):
                            names[name] = None
            elif isinstance(statement, (ast.AugAssign, ast.Delete)):
                targets = (
                    statement.targets if isinstance(statement, ast.Delete) else [statement.target]
                )
                for target in targets:
                    for name in ast.walk(target):
                        if isinstance(name, ast.Name):
                            names[name.id] = None
        return names

    body(tree.body, {})
    return result
