"""Summarize retained real trial evidence without constructing runtime facts."""

from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/review/dialogue-acceptance-20261031"
view = json.loads((OUT / "application-v1-retest-02/actual-view-after.json").read_text(encoding="utf-8"))
model = view["model"]
nodes = {node["id"]: node for node in model["nodes"]}
events = view["events"]
observed = Counter(event["node"] for event in events)
code = view.get("code_structure", {})
report = {
    "kind": "Actual trial source/model and received events; structural declarations are not execution claims",
    "build_id": view["manifest"]["build_id"],
    "source_files": len(model["source_files"]),
    "layers": dict(Counter(node.get("layer", "unspecified") for node in nodes.values())),
    "cross_layer_relations": dict(Counter(
        nodes[edge["from"]].get("layer", "unspecified") + " -> " + nodes[edge["to"]].get("layer", "unspecified")
        for edge in model["edges"] if edge["from"] in nodes and edge["to"] in nodes)),
    "received_owners": dict(observed),
    "features": [{"id": feature["id"], "sources": feature["sources"],
                  "owners": feature["nodes"],
                  "received": {owner: observed[owner] for owner in feature["nodes"]}}
                 for feature in model["implementation"]["features"]],
    "static_code": {"roles": dict(Counter(node.get("code_role") for node in code.get("nodes", []))),
                    "relations": dict(Counter(edge.get("code_relation") for edge in code.get("edges", [])))},
    "exception_capture": [],
}
candidate = json.loads((OUT / "repair-candidate/runtime.json").read_text(encoding="utf-8"))
cached_code = Path(candidate["root"]) / ".stategraph/code-graph.json"
if cached_code.exists():
    code = json.loads(cached_code.read_text(encoding="utf-8"))
    report["static_code"] = {
        "roles": dict(Counter(node.get("code_role") for node in code["nodes"])),
        "relations": dict(Counter(edge.get("code_relation") for edge in code["edges"])),
        "endpoints": [node for node in code["nodes"] if node.get("code_role") == "endpoint"]
    }
records = Path(candidate["root"]) / "bo_stategraph/data/recordings"
for path in records.glob("*.json"):
    value = json.loads(path.read_text(encoding="utf-8"))
    if "events" not in value or value.get("status") == "recording":
        continue
    sample = {"id": value["id"], "status": value["status"], "events": len(value["events"]),
              "gaps": value["gaps"], "producer_settlement": value.get("producer_settlement"),
              "producer_before": value["context"]["health"].get("producer"),
              "producer_after": value["final"]["health"].get("producer")}
    report["exception_capture"].append(sample)
    (OUT / ("operations-v1-repair-03/settled-recording-" + value["id"] + ".json")).write_text(json.dumps(value, indent=2), encoding="utf-8")
(OUT / "layer-and-capture-audit-v1.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"layers": report["layers"], "static_code": report["static_code"],
                  "exception_capture": report["exception_capture"]}))
