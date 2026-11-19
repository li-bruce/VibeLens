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
    from ..concepts import assess, confirm, diff, snapshot

    root = Path(options.root).resolve()
    path = contained(root, options.discovery)
    previous = read(contained(root, options.previous)) if options.previous else None
    model = read_model(contained(root, options.model), project_root=root) if options.model else None
    acceptance = read(contained(root, options.acceptance)) if options.acceptance else None
    with file_lock(path.with_suffix(".lock")):
        document = read(path)
        dialogue = assess_dialogue(
            document, previous=previous, scope=options.scope or None, stage=options.stage
        )
        if not dialogue["valid"]:
            raise ValueError("Invalid dialogue: " + json.dumps(dialogue["errors"]))
        scope = options.scope or None
        if options.action == "review":
            from .construction_review import workbook, markdown
            from ..web.semantic_names import read_names

            result = workbook(
                document,
                dialogue,
                model_ref=options.review_model,
                max_nodes=options.max_nodes,
                locale=options.locale,
                url=options.url,
                names=(read_names(root) or {}).get("names"),
            )
            return {**result, "markdown": markdown(result)}
        if options.action == "snapshot":
            return snapshot(document, scope)
        if options.action == "diff":
            if previous is None:
                raise ValueError("diff requires --previous")
            return diff(previous, document, scope=scope)
        if options.action == "present":
            from ..concepts.construction import present

            if not options.id or not options.sources or not scope:
                raise ValueError("present requires --id, --scope and --sources")
            record = present(
                document,
                scope,
                options.visible or [],
                options.explained or [],
                options.sources,
                options.id,
                options.targets or [],
            )
            existing = next(
                (p for p in document["construction"]["presentations"] if p["id"] == options.id),
                None,
            )
            if existing is not None and existing != record:
                raise ValueError("Presentation identity already exists")
            if existing is None:
                document["construction"]["presentations"].append(record)
                if not assess(document)["valid"]:
                    raise ValueError("Invalid presentation")
                write(path, document)
            return {"valid": True, "presentation": record}
        if options.action == "promote":
            from ..concepts.construction import promote

            if not all(
                (options.target, options.candidate, options.concept, options.expected_revision)
            ):
                raise ValueError(
                    "promote requires target, candidate, concept and expected revision"
                )
            candidate = read(contained(root, options.candidate))
            replacement = promote(
                document, options.target, candidate, options.concept, options.expected_revision
            )
            write(path, replacement)
            return {"valid": True, "target": options.target, "concept": options.concept}
        if options.action == "confirm":
            if not options.id or not options.sources or not scope:
                raise ValueError("confirm requires --id, --scope and --sources")
            if dialogue.get("blocked"):
                # Pending semantic confirmation itself is not an unanswered
                # question. Only recorded blocking business questions prevent
                # acknowledging the matching region.
                selected = set(snapshot(document, scope)["scope"])
                from ..concepts.construction import affects_scope
                from ..concepts.decision_contract import condition_state, due_at

                concepts = dialogue["concepts"]
                pending = [
                    item["id"]
                    for item in document.get("decisions", [])
                    if item.get("blocking")
                    and item.get("status") != "resolved"
                    and (
                        document["schema"] != "business-discovery/v3"
                        or (
                            due_at(item, options.stage)
                            and condition_state(item, {d["id"]: d for d in document["decisions"]})
                            != "inactive"
                        )
                    )
                    and any(
                        affects_scope(
                            ref,
                            concepts["index"],
                            concepts.get("construction", {}).get("targets", {}),
                            selected,
                        )
                        for ref in item.get("affects", [])
                    )
                ]
                if pending:
                    raise ValueError("Unanswered questions: " + ", ".join(pending))
            record = confirm(
                document, scope, options.sources, options.id, presentation_ref=options.presentation
            )
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
        return assess(
            document,
            previous=previous,
            model=model,
            scope=scope,
            acceptance=acceptance,
            stage=options.stage,
        )


def main(argv=None):
    """Run a bounded project-relative operation and print machine-readable results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "validate",
            "check",
            "review",
            "snapshot",
            "present",
            "promote",
            "confirm",
            "diff",
        ),
    )
    parser.add_argument("--root", required=True)
    parser.add_argument("--discovery", default="discovery.json")
    parser.add_argument("--scope", nargs="+")
    parser.add_argument(
        "--stage",
        choices=("before_implementation", "during_coding", "before_acceptance", "before_analysis"),
        default="before_acceptance",
    )
    parser.add_argument("--sources", nargs="+")
    parser.add_argument("--id")
    parser.add_argument("--presentation", help="Exact previously recorded presentation ID")
    parser.add_argument("--visible", nargs="+")
    parser.add_argument("--explained", nargs="+")
    parser.add_argument("--targets", nargs="+")
    parser.add_argument("--target")
    parser.add_argument("--candidate")
    parser.add_argument("--concept")
    parser.add_argument("--expected-revision")
    parser.add_argument("--previous")
    parser.add_argument("--model")
    parser.add_argument("--acceptance", help="Independent business assertions for bound case IDs")
    parser.add_argument("--out", help="Project-relative JSON report path")
    parser.add_argument("--review-model", help="Canonical business, state or rule model to preview")
    parser.add_argument("--max-nodes", type=int, default=12)
    parser.add_argument("--locale", choices=("en", "zh-CN"))
    parser.add_argument("--url", help="Verified viewer URL for the conversation link")
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
