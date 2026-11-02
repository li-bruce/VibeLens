"""Audit a captured trial's layers against actual source and state-instance facts.

This report complements independent native tests. It does not infer business
correctness or turn static call possibilities into observed runtime calls.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.workflow.observation_requirements import LAYER_CHECKS, layer_of


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--projection", type=Path)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError("Layer audit evidence cannot be overwritten")
    recording = json.loads((args.capture / "recording.json").read_text(encoding="utf-8"))
    projection_path = args.projection or args.capture / "layer-projection.json"
    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    model = recording["context"]["model"]
    nodes = {node["id"]: node for node in model["nodes"]}
    # The on-demand source slice adds physical file/symbol/boundary nodes. Its
    # explicit omissions remain in the report; this is not a whole-AST claim.
    for node in projection["nodes"]:
        if node["id"] not in nodes:
            nodes[node["id"]] = node
    counts = Counter(layer_of(node) for node in nodes.values())
    event_counts = Counter(layer_of(nodes[e["node"]]) for e in recording["events"])
    missing_sources = [
        {"node": node["id"], "path": node["source"]["path"]}
        for node in nodes.values()
        if (node.get("source") or {}).get("path")
        and not (args.project / node["source"]["path"]).is_file()
        and node.get("code_role") not in {"directory", "boundary"}
    ]
    api_nodes = [node["id"] for node in nodes.values() if node.get("layer") == "api"]
    cfgs = recording["final"]["machine"]["configurations"]
    instances = [cfg.get("snapshot_instance") for cfg in cfgs]
    frames = recording["runtime_frames"]["frames"]
    state_values = {cfg["phase"] for frame in frames for cfg in frame["machine"]["configurations"]}
    state_nodes = {
        node.get("value", node.get("state")) for node in nodes.values() if layer_of(node) == "state"
    }
    missing_states = sorted(state_values - state_nodes)
    result = {
        "passed": not missing_sources
        and len(instances) > 1
        and all(instances)
        and len(instances) == len(set(instances))
        and all(counts[layer] > 0 for layer in LAYER_CHECKS)
        and bool(api_nodes)
        and bool(frames)
        and not missing_states,
        "layers": {
            layer: {
                "nodes": counts[layer],
                "events": event_counts[layer],
                "source_only": layer in {"project", "code", "data"},
            }
            for layer in LAYER_CHECKS
        },
        "api_runtime_nodes": api_nodes,
        "state_evidence": {
            "snapshot_frames": len(frames),
            "observed_values": sorted(state_values),
            "values_without_state_nodes": missing_states,
            "basis": "Exact native snapshots, rather than a second state-node probe.",
        },
        "missing_source_files": missing_sources,
        "state_instances": [
            {k: c.get(k) for k in ("snapshot_instance", "native_instance_id", "attempt", "phase")}
            for c in cfgs
        ],
        "source_projection": projection["code_summary"],
        "meaning": "Captured model plus explicitly bounded live source slice; structural layers do not fabricate runtime events.",
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "layers": result["layers"]}))
    raise SystemExit(not result["passed"])


if __name__ == "__main__":
    main()
