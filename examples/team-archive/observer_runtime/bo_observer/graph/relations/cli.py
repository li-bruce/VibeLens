"""Atomic JSON graph mutations through the same construction-time relation index."""

import argparse
from copy import deepcopy
import json
from pathlib import Path

from ..behavior_model import contained, read
from ...web.view_preferences import file_lock
from ...workflow.sync_io import write
from .model import attach, construct, validate


def operate(document, action, payload=None, *, expected_revision=None):
    """Return a detached document; failed validation never publishes a partial edit."""
    value = deepcopy(document)
    model = value["model"] if value.get("protocol") == "bo-project/v1" else value
    index = validate(model)
    if action == "init":
        if index is not None:
            raise ValueError("Graph already has a relation registry")
        if not isinstance(payload, dict) or set(payload) - {"rules", "registrations", "limits"}:
            raise ValueError("init needs rules, registrations and optional limits")
        if any(not isinstance(payload[key], dict) for key in payload):
            raise ValueError("init fields must be JSON objects")
        model = construct(
            model,
            payload.get("rules"),
            registrations=payload.get("registrations"),
            limits=payload.get("limits"),
        )
    else:
        if index is None:
            raise ValueError("Initialize graph relations before mutation")
        if action != "check":
            if action == "insert":
                operations = [{"op": "insert", "entry": payload}]
            elif action == "update":
                operations = [{"op": "update", "id": payload["edge"]["id"], "entry": payload}]
            elif action == "remove":
                if not isinstance(payload, dict) or set(payload) != {"id"}:
                    raise ValueError("remove needs exactly one id")
                operations = [{"op": "remove", "id": payload["id"]}]
            elif action == "batch":
                operations = payload
            else:
                raise ValueError("Unknown relation action")
            # A physical edge appended by another projector cannot be overwritten
            # by registering its ID with a different payload.
            if not isinstance(operations, list):
                raise ValueError("Expected a list of relation operations")
            registered = set(index.export()["decisions"])
            opaque = {edge["id"] for edge in model["edges"] if edge["id"] not in registered}
            if any(
                op.get("entry", {}).get("edge", {}).get("id") in opaque
                for op in operations
                if isinstance(op, dict)
            ):
                raise ValueError(
                    "Registering an external edge requires rebuilding its construction source"
                )
            index.apply(operations, expected_revision=expected_revision)
            model = attach(model, index)
    if value.get("protocol") == "bo-project/v1":
        value["model"] = model
        from ...protocol import validate_project

        validate_project(value)
    else:
        value = model
        if model.get("schema_version") == 3:
            # Retain the preexisting graph/machine checks for real project files.
            try:
                from bo_contracts import validate_graph
            except ImportError:
                from ....bo_contracts import validate_graph

            validate_graph(model)
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "insert", "update", "remove", "batch", "check"])
    parser.add_argument("--root", required=True)
    parser.add_argument("--model", required=True, help="Project-relative graph JSON")
    parser.add_argument("--input", help="Project-relative mutation JSON")
    parser.add_argument("--expected-revision", help="Reject a concurrent graph mutation")
    args = parser.parse_args(argv)
    try:
        root = Path(args.root).resolve()
        target = contained(root, args.model)
        if args.action != "check" and not args.input:
            raise ValueError("Mutation requires --input")
        payload = read(contained(root, args.input)) if args.input else None
        with file_lock(target.with_name(target.name + ".relations.lock")):
            result = operate(
                read(target), args.action, payload, expected_revision=args.expected_revision
            )
            if args.action != "check":
                write(target, result)
        model = result["model"] if result.get("protocol") == "bo-project/v1" else result
        saved = model["relation_registry"]
        counts = {
            status: sum(item["status"] == status for item in saved["decisions"].values())
            for status in ("retained", "duplicate", "represented")
        }
        print(
            json.dumps(
                {
                    "valid": True,
                    "revision": saved["revision"],
                    "counts": counts,
                    "decisions": saved["decisions"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
