"""Interpret authorized scripted requirements using the installed native inventory."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
inventory = json.loads((OUT / "inventory.json").read_text(encoding="utf-8-sig"))["result"]
nodes = {node["id"]: node for node in inventory["nodes"]}
main = ["login", "upload", "owned_file", "choose_recipient", "share", "received_list", "download"]
assert all(node in nodes for node in main + ["policy:network", "policy:access_allowed"])
assert nodes["policy:access_allowed"]["parent"] == "policy:network"
assert all(any(edge["from"] == left and edge["to"] == right and edge["type"] in {"flow", "data"}
               for edge in inventory["edges"]) for left, right in zip(main, main[1:]))
specs = {
    "main": {"action": "view", "label": "Scripted main business flow", "anchors": main,
             "depth": 1, "direction": "both", "nodes": ["business"],
             "edges": ["flow", "data", "guard"], "layout": "layered", "max_nodes": 80},
    "permission": {"action": "view", "label": "Scripted download permission", "anchors": ["download", "policy:access_allowed"],
                   "depth": 3, "direction": "backward", "nodes": ["business", "decision", "data", "function"],
                   "edges": ["guard", "data"], "layout": "layered", "max_nodes": 80},
}
specs["replay"] = {**specs["permission"], "action": "replay", "label": "Scripted permission replay", "loop": True}
for name, spec in specs.items():
    (OUT / (name + ".spec.json")).write_text(json.dumps(spec, indent=2), encoding="utf-8")
provenance = {
    "kind": "scripted user", "independent_human_confirmation": False,
    "authorization": "Current forwarded task explicitly authorizes isolated-project simulated control requirements.",
    "activation_input": "$vibelens /vibelens 只看主要业务流程",
    "activation_note": "Native scoped activation was required; the Skill was already explicitly adopted in this chat. This wrapper is scripted, not a new human confirmation.",
    "main_input": "/vibelens 只看主要业务流程",
    "permission_input": "/vibelens 查看下载权限的业务动作、规则和参数",
    "replay_input": "/vibelens 用本轮真实录制回放下载权限路径并循环",
    "replay_note": "Agent-authored technical check within the explicitly requested native recording-filter acceptance.",
    "interpretation": "Main anchors follow six real declared flow/data edges. Depth-one includes actual adjacent boundary nodes. Permission selection follows guard/data dependencies backwards to real parameters; it uses this project's access_allowed identity, not another example's read_allowed.",
    "project_id": inventory["project_id"], "model_revision": inventory["model_revision"],
    "privacy": "Local raw evidence only. Do not publish session tokens or private control/view config."
}
(OUT / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"actual_inventory_nodes": len(nodes), "main_declared_path_edges": 6, "specs": list(specs)}))
