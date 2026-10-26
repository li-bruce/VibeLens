"""Check existing graph export foundations; this is not a web-export acceptance test."""

import argparse
import json
from pathlib import Path
import sys

# The maintained copy belongs in docs/features/graph-context-for-ai/.
ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "skills/vibelens/scripts").is_dir()
)
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from focus_graph import extract, markdown


def check_case(version):
    """Use the immutable execution capture and its producer identity."""
    artifact = json.loads(
        (ROOT / f"docs/site/case-data/v{version}.json").read_text(encoding="utf-8")
    )
    recording = artifact["recording"]
    model = artifact["view"]["model"]
    producer = next(
        event["run_id"] for event in recording["events"] if event["node"] == "review-policy"
    )
    focused = extract(
        model,
        ["review-policy"],
        depth=1,
        max_nodes=8,
        max_edges=16,
        events=recording["events"],
        run_id=producer,
        build_id=recording["build_id"],
    )
    verdicts = [
        event["outputs"].get("verdict")
        for event in focused["events"]
        if event["node"] == "review-policy" and event["phase"] == "return"
    ]
    assert ("allowed" if version == 1 else "stale_review") in verdicts
    assert focused["mapping"]["review-policy"]["source"]["path"] == "policy.py"
    assert "```mermaid" in markdown(focused)
    originals = {edge["id"] for edge in model["edges"]}
    assert all(edge["id"] in originals for edge in focused["edges"])
    wrong = extract(
        model,
        ["review-policy"],
        events=recording["events"],
        run_id=producer,
        build_id="different-build",
    )
    assert not wrong["events"] and wrong["coverage"]["evidence_gaps"]
    observer = extract(
        model,
        ["review-policy"],
        events=recording["events"],
        run_id=recording["run_id"],
        build_id=recording["build_id"],
    )
    assert not observer["events"] and observer["coverage"]["evidence_gaps"]
    result = {
        "case": version,
        "nodes": len(focused["nodes"]),
        "events": len(focused["events"]),
        "verdicts": verdicts,
        "source_binding": True,
        "markdown_export": True,
        "original_edge_identities": True,
        "wrong_build_events_excluded": True,
        "observer_and_producer_runs_must_be_distinguished": True,
        "web_selection_to_assistant_export": "not_implemented",
        "exact_event_cursor_export": "not_implemented",
    }
    if version == 2:
        stale = next(
            event
            for event in focused["events"]
            if event["phase"] == "return" and event["outputs"].get("verdict") == "stale_review"
        )
        future = [event for event in focused["events"] if event["seq"] > stale["seq"]]
        assert any(event.get("outputs", {}).get("verdict") == "allowed" for event in future)
        result["whole_run_export_includes_events_after_stale_review"] = True
        result["stale_review_seq"] = stale["seq"]
    return result


def main():
    """Print a reproducible baseline; write only when an output path is supplied."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {
        "baseline_checks_passed": True,
        "complete_web_feature": False,
        "cases": [check_case(1), check_case(2)],
    }
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
