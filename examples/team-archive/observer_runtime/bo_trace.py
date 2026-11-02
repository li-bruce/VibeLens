"""Check tracing registrations or export the provenance of an existing recording."""

import argparse
import json
from pathlib import Path

from bo_observer.model_io import read_model
from bo_observer.observation.provenance import export_provenance
from bo_observer.observation.telemetry import load_registrations, business_layer_errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("--root", type=Path, required=True)
    check.add_argument("--model", default="bo_stategraph/project.json")
    export = sub.add_parser("export")
    export.add_argument("--recording", type=Path, required=True)
    export.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "check":
        model = read_model(args.root / args.model)
        configuration = load_registrations(args.root, model)
        errors = business_layer_errors(model)
        print(
            json.dumps(
                {
                    "valid": not errors,
                    "backend": "opentelemetry" if configuration else "native",
                    "registrations": len(configuration["registrations"]) if configuration else 0,
                    "errors": errors,
                }
            )
        )
        return int(bool(errors))
    value = json.loads(args.recording.read_text(encoding="utf-8"))
    events = (
        value
        if isinstance(value, list)
        else [*value.get("context", {}).get("events", []), *value["events"]]
    )
    unique = {}
    for event in events:
        if event["id"] in unique and unique[event["id"]] != event:
            raise ValueError("conflicting event identity in export")
        unique[event["id"]] = event
    result = export_provenance(list(unique.values()))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"valid": True, "events": len(unique), "objects": len(result["objects"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
