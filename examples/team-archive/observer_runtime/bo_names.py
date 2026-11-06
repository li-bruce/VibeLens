"""Prepare, validate and install layer-aware semantic names maintained by the coding agent."""

import argparse
import json
from pathlib import Path
from bo_observer.web.semantic_names import assess, install, inventory, project_inventory, read_names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["inventory", "check", "apply"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--view", type=Path, help="Optional current viewer export, including a loaded source slice"
    )
    parser.add_argument("--input", type=Path, help="AI-authored bo-semantic-names/v1 document")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    items = (
        inventory(json.loads(args.view.read_text(encoding="utf-8-sig")))
        if args.view
        else project_inventory(args.root)
    )
    document = read_names(args.root)
    if args.action == "inventory":
        result = {"items": items, "coverage": assess(items, document)}
    elif args.action == "apply":
        if not args.input:
            parser.error("apply requires --input")
        result = install(args.root, json.loads(args.input.read_text(encoding="utf-8-sig")), items)
    else:
        result = assess(items, document)
        if not result["configured"]:
            result.update(valid=False, errors=["Semantic names have not been generated"])
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if result.get("valid", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
