"""Read authored trial source without importing or changing the application."""

import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

REPOSITORY = Path(__file__).resolve().parents[4]
TRIAL = REPOSITORY.parent / "VibeLensTrials/graph-quality-dialogue-20261104-01"
AUTHORED = (
    "models.py",
    "service.py",
    "server.py",
    "observe.py",
    "ports.py",
    "dev.py",
    "build_model.py",
    "test_app.py",
    "integrations/bo_integration.py",
    "bo_stategraph/workflow.py",
)


def source_facts(name):
    path = TRIAL / name
    if not path.is_file():
        return {"status": "not_yet_created"}
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    result = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    if "Planned project module; implementation begins after the frozen baseline." in text:
        return {**result, "status": "explicit_placeholder"}
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        return {**result, "status": "parse_pending", "line": error.lineno}
    functions, spans, declarations, drive_calls = [], [], [], []

    def visit(body, prefix=""):
        for node in body:
            if isinstance(node, ast.ClassDef):
                visit(node.body, prefix + node.name + ".")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbol = prefix + node.name
                documentation = ast.get_docstring(node) or ""
                functions.append(
                    {
                        "symbol": symbol,
                        "line": node.lineno,
                        "end_line": node.end_lineno,
                        "parameters": [
                            item.arg
                            for item in [
                                *node.args.posonlyargs,
                                *node.args.args,
                                *node.args.kwonlyargs,
                            ]
                            if item.arg not in {"self", "cls"}
                        ],
                        "docstring": documentation,
                    }
                )
                for decorator in node.decorator_list:
                    if (
                        isinstance(decorator, ast.Call)
                        and isinstance(decorator.func, ast.Attribute)
                        and decorator.func.attr
                        in {"route", "get", "post", "put", "patch", "delete"}
                    ):
                        declarations.append(
                            {
                                "symbol": symbol,
                                "line": decorator.lineno,
                                "declaration": ast.unparse(decorator),
                                "documentation": documentation,
                            }
                        )
                for call in ast.walk(node):
                    if not isinstance(call, ast.Call):
                        continue
                    if (
                        isinstance(call.func, ast.Attribute)
                        and call.func.attr == "span"
                        and call.args
                        and isinstance(call.args[0], ast.Constant)
                        and isinstance(call.args[0].value, str)
                    ):
                        spans.append(
                            {"symbol": symbol, "line": call.lineno, "node": call.args[0].value}
                        )
                    if isinstance(call.func, ast.Name) and call.func.id == "advance":
                        drive_calls.append(
                            {"symbol": symbol, "line": call.lineno, "call": ast.unparse(call)}
                        )
                visit(node.body, symbol + ".")

    visit(tree.body)
    return {
        **result,
        "status": "authored_source",
        "functions": functions,
        "span_nodes": spans,
        "api_declarations": declarations,
        "native_drive_calls": drive_calls,
    }


def declaration_facts(name):
    path = TRIAL / name
    if not path.is_file():
        return {"status": "not_yet_created"}
    raw = path.read_bytes()
    result = {"sha256": hashlib.sha256(raw).hexdigest()}
    try:
        payload = json.loads(raw)
    except (UnicodeError, ValueError):
        return {**result, "status": "write_pending"}
    if name.endswith("project.json"):
        model = payload["model"]
        return {
            **result,
            "status": "present",
            "project_id": payload["project_id"],
            "selection": payload.get("selection"),
            "revision": model["revision"],
            "nodes": [
                {key: node[key] for key in ("id", "layer", "kind", "summary") if key in node}
                for node in model["nodes"]
            ],
            "machine": model.get("machine"),
            "policy_present": "policy" in model,
        }
    if name.endswith("telemetry.json"):
        return {**result, "status": "present", "registrations": payload.get("registrations", [])}
    if name == "implementation.json":
        return {**result, "status": "present", "features": payload.get("features", [])}
    return {**result, "status": "present", "payload": payload}


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "in-progress-01"
    if not re.fullmatch(r"[a-z0-9-]+", phase):
        raise SystemExit("Use a simple evidence phase name")
    output = Path(__file__).parent / ("snapshot-" + phase + ".json")
    if output.exists():
        raise SystemExit("Preserve existing evidence; choose a new phase")
    report = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "trial": str(TRIAL),
        "boundary": "Read-only per-file snapshot of an actively generated application; pending placeholders are not failed acceptance.",
        "source": {name: source_facts(name) for name in AUTHORED},
        "declarations": {
            name: declaration_facts(name)
            for name in (
                "bo_stategraph/project.json",
                "bo_stategraph/telemetry.json",
                "bo_stategraph/runtime-version.json",
                "implementation.json",
            )
        },
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "evidence": str(output),
                "source": {name: value["status"] for name, value in report["source"].items()},
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
