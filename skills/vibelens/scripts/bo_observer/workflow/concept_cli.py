"""Persist scoped concept confirmations without editing business implementation.

This is a coding-agent command. The graph page remains a viewer. A confirmation
references an actual recorded user answer and freezes the precise semantic scope;
opening Web or generating a snapshot does not record agreement.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..graph.behavior_model import contained
from ..model_io import read_model
from ..web.view_preferences import file_lock
from .requirements_dialogue import assess as assess_dialogue, read
from .sync_io import write


def execute(options):
    """Validate before writing and keep already recorded confirmations immutable."""
    from ..concepts import assess, confirm, diff, resolve, snapshot

    root = Path(options.root).resolve()
    path = contained(root, options.discovery)
    previous = read(contained(root, options.previous)) if options.previous else None
    model = read_model(contained(root, options.model)) if options.model else None
    acceptance = read(contained(root, options.acceptance)) if options.acceptance else None
    with file_lock(path.with_suffix(".lock")):
        document = read(path)
        dialogue = assess_dialogue(document)
        if not dialogue["valid"]:
            raise ValueError("Invalid dialogue: " + json.dumps(dialogue["errors"]))
        scope = options.scope or None
        if options.action == "snapshot":
            return snapshot(document, scope)
        if options.action == "diff":
            if previous is None:
                raise ValueError("diff requires --previous")
            return diff(previous, document, scope=scope)
        if options.action == "confirm":
            if not options.id or not options.sources or not scope:
                raise ValueError("confirm requires --id, --scope and --sources")
            if dialogue.get("blocked"):
                # Pending semantic confirmation itself is not an unanswered
                # question. Only recorded blocking business questions prevent
                # acknowledging the matching region.
                selected = set(snapshot(document, scope)["scope"])
                pending = [
                    item["id"]
                    for item in document.get("decisions", [])
                    if item.get("blocking")
                    and item.get("status") != "resolved"
                    and {resolve(document, ref) for ref in item.get("affects", [])} & selected
                ]
                if pending:
                    raise ValueError("Unanswered questions: " + ", ".join(pending))
            record = confirm(document, scope, options.sources, options.id)
            existing = next(
                (item for item in document.get("confirmations", []) if item["id"] == options.id),
                None,
            )
            if existing is not None:
                if existing != record:
                    raise ValueError("Confirmation identity already exists with different content")
            else:
                candidate = {
                    **document,
                    "confirmations": [*document.get("confirmations", []), record],
                }
                report = assess(candidate, previous=document)
                if not report["valid"]:
                    raise ValueError("Invalid confirmation: " + json.dumps(report["errors"]))
                write(path, candidate)
            return {"valid": True, "confirmation": record}
        return assess(document, previous=previous, model=model, scope=scope, acceptance=acceptance)


def main(argv=None):
    """Run a bounded project-relative operation and print machine-readable results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "check", "snapshot", "confirm", "diff"))
    parser.add_argument("--root", required=True)
    parser.add_argument("--discovery", default="discovery.json")
    parser.add_argument("--scope", nargs="+")
    parser.add_argument("--sources", nargs="+")
    parser.add_argument("--id")
    parser.add_argument("--previous")
    parser.add_argument("--model")
    parser.add_argument("--acceptance", help="Independent business assertions for bound case IDs")
    parser.add_argument("--out", help="Project-relative JSON report path")
    parser.add_argument(
        "--full-report", action="store_true", help="Include the full assembled graph on stdout"
    )
    options = parser.parse_args(argv)
    try:
        from .artifact_paths import guard_outputs

        root = Path(options.root).resolve()
        protected = [
            contained(root, name)
            for name in (options.discovery, options.previous, options.model, options.acceptance)
            if name
        ]
        target = guard_outputs(root, [options.out], inputs=protected)[0] if options.out else None
        result = execute(options)
        if target:
            write(target, result)
        from .concept_review import compact_report

        displayed = result if options.full_report else compact_report(result)
        print(json.dumps(displayed, ensure_ascii=False, indent=2))
        return int(
            not result.get("valid", True)
            or (options.action == "check" and not result.get("ready", False))
        )
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(json.dumps({"valid": False, "error": str(error)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
