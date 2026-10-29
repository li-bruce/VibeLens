"""Validate, project and check a project's shared rule network."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from bo_observer.policy.definition import validate
from bo_observer.policy.evidence import evaluation_errors
from bo_observer.policy.sync import synchronize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "sync", "check"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--model", default="bo_stategraph/project.json")
    parser.add_argument("--policy", help="Standalone declaration for initial dialogue modeling")
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--evaluation", help="Actual native policy evaluation JSON")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "validate":
        path = (root / (args.policy or args.model)).resolve()
        if not path.is_relative_to(root):
            parser.error("policy path escapes project")
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        policy = value if args.policy else value.get("model", value).get("policy")
        result = validate(policy, bound=not args.draft)
        report = {
            "valid": True,
            "stage": policy["stage"],
            "nodes": len(result["nodes"]),
            "operations": list(result["operations"]),
            "order": result["order"],
        }
    else:
        report = synchronize(root, model_path=args.model, update=args.command == "sync")
        if args.command == "check" and report["enabled"] and report["valid"]:
            from bo_observer.graph.code_structure import scan
            from bo_observer.policy.evidence import binding_errors

            document = json.loads((root / args.model).read_text(encoding="utf-8-sig"))
            policy = document.get("model", document)["policy"]
            paths = sorted({pred["source"]["path"] for pred in policy["predicates"]})
            structure = scan(root, paths)
            report["errors"] += structure["errors"] + binding_errors(policy, structure)
            report["valid"] = not report["errors"]
        if args.evaluation:
            path = (root / args.evaluation).resolve()
            if not path.is_relative_to(root):
                parser.error("evaluation path escapes project")
            document = json.loads((root / args.model).read_text(encoding="utf-8-sig"))
            policy = document.get("model", document)["policy"]
            # Standalone checks need the same freshness boundary as the coding
            # gate. A structurally valid report from older source is not current.
            manifest = {
                "files": {
                    pred["source"]["path"]: sha256(
                        (root / pred["source"]["path"]).read_bytes()
                    ).hexdigest()
                    for pred in policy["predicates"]
                }
            }
            report["errors"] += evaluation_errors(
                policy, json.loads(path.read_text(encoding="utf-8")), manifest=manifest
            )
            report["valid"] = not report["errors"]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
