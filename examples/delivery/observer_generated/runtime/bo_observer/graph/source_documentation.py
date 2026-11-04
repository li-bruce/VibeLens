"""Read authored source explanations and report missing mapped documentation.

Documentation is source evidence, separate from graph identity and AI aliases.
Only explicit parameter documentation is attributed to a parameter; capture
outputs never acquire the meaning of a similarly named lexical variable.
"""

import ast
import inspect
import re


def summary(text):
    """Use one short source sentence as a display explanation."""
    paragraph = re.split(r"\n\s*\n", text.strip(), maxsplit=1)[0]
    sentence = re.split(r"(?<=[.!?])\s+|(?<=[。！？])", " ".join(paragraph.split()), maxsplit=1)[0]
    return sentence[:100]


def python_documentation(path, name, node):
    """Extract Python docstrings, including Google, NumPy and Sphinx parameters."""
    expression = node.body[0] if node.body else None
    literal = expression.value if isinstance(expression, ast.Expr) else None
    present = isinstance(literal, ast.Constant) and isinstance(literal.value, str)
    text = inspect.cleandoc(literal.value) if present else ""
    parameters = {}
    section, current = None, None
    leading = (
        len(literal.value.splitlines()) - len(literal.value.lstrip("\n").splitlines())
        if present
        else 0
    )
    for offset, raw in enumerate(text.splitlines()):
        line = raw.strip()
        if line in {"Args:", "Arguments:", "Parameters:", "Parameters"}:
            section, current = "numpy" if line == "Parameters" else "parameters", None
            continue
        sphinx = re.match(r":param\s+(?:\S+\s+)?([\w*]+)\s*:\s*(.*)", line)
        google = re.match(r"([\w*]+)(?:\s*\([^)]*\))?\s*:\s*(.*)", line)
        match = sphinx or (
            google
            if section == "numpy" or (section == "parameters" and raw.startswith(" "))
            else None
        )
        if match:
            current = match[1].lstrip("*")
            parameters[current] = {
                "description": "" if section == "numpy" and not sphinx else match[2].strip(),
                "line": (literal.lineno if present else node.lineno) + leading + offset,
            }
            continue
        if line.startswith(":") or (
            section in {"parameters", "numpy"}
            and line
            and not raw.startswith(" ")
            and set(line) != {"-"}
        ):
            section, current = None, None
        elif current and line and set(line) != {"-"}:
            parameters[current]["description"] += " " + line
    return {
        "status": "documented" if text else "missing",
        "format": "python-docstring",
        "summary": summary(text) if text else "",
        "description": text,
        "parameters": parameters,
        "source": {
            "path": path,
            "symbol": name,
            "line": literal.lineno if present else node.lineno,
            "end_line": literal.end_lineno if present else node.lineno,
        },
    }


def report(index, model, *, all_symbols=False):
    """Check mapped declarations and explicitly represented source parameters.

    API handlers are independently discovered from source. They are included
    even when an authored graph accidentally omits their function binding.
    Legacy missing comments remain visible findings, never invented prose.
    """
    from ..code_graph.endpoints import endpoints
    from ..code_graph.index import handler_key

    symbols = index["symbols"]
    selected, parameters = set(), {}
    for node in model.get("nodes", []):
        for role in ("source", "represents"):
            source = node.get(role)
            if not source or not source.get("path") or not source.get("symbol"):
                continue
            key = source["path"] + "::" + source["symbol"]
            selected.add(key)
            if role == "represents":
                parameters.setdefault(key, set()).add(source["parameter"])
    for feature in (model.get("implementation") or {}).get("features", []):
        for parameter in feature.get("parameters", []):
            key, name = parameter.get("source"), parameter.get("name")
            if isinstance(key, str) and isinstance(name, str):
                selected.add(key)
                parameters.setdefault(key, set()).add(name)
    for key, symbol in symbols.items():
        if all_symbols or endpoints(symbol):
            selected.add(key)
    for path, unit in index["units"].items():
        for route in unit.get("http_registrations", []):
            key = handler_key(path, route.get("handler") or "", index["units"], symbols)
            if key in symbols:
                selected.add(key)
    checked, missing = [], []
    for key in sorted(selected):
        symbol = symbols.get(key)
        if symbol is None:
            missing.append({"symbol": key, "reason": "source_symbol_missing"})
            continue
        if symbol.get("role") == "template" or symbol["symbol"] == "<module>":
            continue
        documentation = symbol.get("documentation", {})
        checked.append(key)
        if not documentation.get("summary"):
            missing.append({"symbol": key, "reason": "source_summary_missing"})
        declared = {p["name"] for p in symbol.get("parameters", [])}
        wanted = parameters.get(key, set())
        if all_symbols:
            wanted = wanted | (declared - {"self", "cls"})
        for parameter in sorted(wanted):
            if parameter not in declared:
                reason = "source_parameter_missing"
            elif (
                not documentation.get("parameters", {})
                .get(parameter, {})
                .get("description", "")
                .strip()
            ):
                reason = "parameter_description_missing"
            else:
                continue
            missing.append({"symbol": key, "parameter": parameter, "reason": reason})
    return {
        "schema": "bo-source-documentation/v1",
        "scope": "all" if all_symbols else "mapped-and-api",
        "checked_symbols": checked,
        "missing": missing,
        "errors": index.get("errors", []),
        "valid": not missing and not index.get("errors"),
    }
