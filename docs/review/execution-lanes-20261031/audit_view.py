"""Read an actual observer view and summarize original identities without mutation.

This independent review helper never infers missing parent links from timestamps.
Business outcomes and source inventory still have their own protected checks.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.workflow.observation_requirements import invocation_closure, layer_of


def scope(event, call=None):
    keys = ("build_id", "run_id", "producer_id", "stream_id", "entity", "attempt")
    return tuple(event.get(key) for key in keys) + (call or event.get("call_id"),)


def audit(view):
    """Report only witnessed source/event links and declared layer membership."""
    model, events = view["model"], view["events"]
    nodes = {node["id"]: node for node in model["nodes"]}
    by_id = {event["id"]: event for event in events}
    entries = {scope(event): event for event in events if event["phase"] == "enter"}
    nested, unresolved, roots = [], [], []

    def enclosing(event):
        """Cross file identities only with an actual explicit entry reference."""
        reference = event.get("parent_event_id")
        if reference:
            parent = by_id.get(reference)
            return parent if parent and parent["phase"] == "enter" else None
        return entries.get(scope(event, event["parent_call_id"])) if event.get("parent_call_id") else None

    for event in entries.values():
        parent = event.get("parent_call_id")
        if parent or event.get("parent_event_id"):
            outer = enclosing(event)
            item = {"event": event["id"], "node": event["node"], "parent_call_id": parent}
            if outer:
                nested.append({**item, "parent_event": outer["id"], "parent_node": outer["node"]})
            else:
                unresolved.append(item)
        else:
            roots.append({"event": event["id"], "node": event["node"]})
    data = [event for event in entries.values() if layer_of(nodes[event["node"]]) == "operations"]
    points = [event for event in events if event["phase"] not in {"enter", "return", "error"}]
    unowned_points = []
    for event in points:
        own = entries.get(scope(event))
        if not enclosing(event) and not (own and own["node"] == event["node"]):
            if not nodes[event["node"]].get("observation_root"):
                unowned_points.append({"event": event["id"], "node": event["node"]})
    layers = Counter(layer_of(node) for node in model["nodes"])
    edges = Counter()
    missing_endpoints = []
    for edge in model["edges"]:
        if edge["from"] not in nodes or edge["to"] not in nodes:
            missing_endpoints.append(edge["id"])
        else:
            edges[layer_of(nodes[edge["from"]]) + " -> " + layer_of(nodes[edge["to"]])] += 1
    return {
        "build_id": view.get("manifest", {}).get("build_id"),
        "events": len(events),
        "entered_calls": len(entries),
        "nested_calls": len(nested),
        "unresolved_parent_references": unresolved,
        "roots": roots,
        "data_calls": len(data),
        "data_calls_with_parent": sum(bool(event.get("parent_call_id")) for event in data),
        "point_facts": len(points),
        "unowned_internal_points": unowned_points,
        "parent_links": nested,
        "declared_layers": dict(layers),
        "direct_observations_by_layer": dict(
            Counter(layer_of(nodes[event["node"]]) for event in events)
        ),
        "edge_layer_pairs": dict(edges),
        "missing_edge_endpoints": missing_endpoints,
        "invocation_closure": invocation_closure(
            {"runs": [{"mode": "on", "events": events}]}, required=True, model=model
        ),
        "health": view.get("health"),
        "meaning": "Original observed parents and declared layers; no inferred history, business verdict or runtime claim for static-only structures.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--url")
    source.add_argument("--file", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.url:
        with urlopen(args.url, timeout=10) as response:
            raw = response.read()
    else:
        raw = args.file.read_bytes()
    view = json.loads(raw)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "view.json").write_bytes(raw)
    report = audit(view)
    (args.out / "audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "events",
                    "entered_calls",
                    "data_calls",
                    "data_calls_with_parent",
                    "declared_layers",
                )
            }
        )
    )
