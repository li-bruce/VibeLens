"""Inspect the existing trial with current adapters without changing trial files."""

import hashlib
import json
from pathlib import Path
import sys

REPOSITORY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPOSITORY / "skills/vibelens/scripts"))
from bo_observer.code_graph.service import CodeGraph
from bo_observer.graph.behavior_model import capture

trial = REPOSITORY.parent / "VibeLensTrials/otel-provenance-dialogue-20261101-04"
source = trial / "app/web.py"
before = hashlib.sha256(source.read_bytes()).hexdigest()
service = CodeGraph(trial, persist=False)
graph, model = service.refresh()
manifest = capture(trial, model)
result = {
    "trial": trial.name,
    "application_source_unchanged": hashlib.sha256(source.read_bytes()).hexdigest() == before,
    "application_source_sha256": before,
    "physical_endpoints": [
        {key: node.get(key) for key in ("id", "label", "api_role", "api", "source", "documentation")}
        for node in graph["nodes"]
        if node.get("code_role") == "endpoint"
    ],
    "authored_api_anchors": [
        {
            "id": node["id"],
            "authored_label": node["label"],
            "source": node["source"],
            "role": manifest["bindings"][node["id"]].get("api_role"),
            "selector": manifest["bindings"][node["id"]].get("telemetry_match"),
            "documentation_status": manifest["bindings"][node["id"]].get("documentation", {}).get("status"),
        }
        for node in model["nodes"]
        if node.get("layer") == "api"
    ],
    "source_documentation": service.documentation(),
    "parser_errors": graph["errors"],
}
output = Path(__file__).with_name("trial-analysis.json")
output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"output": str(output), "endpoints": len(result["physical_endpoints"]), "anchors": len(result["authored_api_anchors"]), "source_unchanged": result["application_source_unchanged"]}))
