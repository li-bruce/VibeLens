"""Export checked view/replay plans for the Pages conversation-control examples."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.control.selection import build_plan, validate_evidence


def build(artifact_path=None):
    """Select original case identities with the same controller used by a project."""
    source = artifact_path or ROOT / "docs/site/case-data/v1.json"
    artifact = json.loads(Path(source).read_text(encoding="utf-8"))
    story = artifact["story"]
    result = {"case": 1, "locales": {}}
    for language, labels in {
        "en": ["File sharing", "Download permission", "Download replay"],
        "zh-CN": ["文件共享", "下载权限", "下载链路回放"],
    }.items():
        specs = {
            "business": {
                "action": "view",
                "label": labels[0],
                "anchors": story["control_anchors"]["business"],
                "depth": 0,
                "direction": "both",
                "nodes": ["business"],
                "edges": ["flow", "data", "guard"],
                "layout": "layered",
            },
            "details": {
                "action": "view",
                "label": labels[1],
                "anchors": story["control_anchors"]["details"],
                "depth": 0,
                "nodes": ["business", "decision", "data", "function"],
                "edges": ["call", "flow", "guard", "data", "maps"],
                "layout": "layered",
            },
        }
        specs["replay"] = {
            **specs["details"],
            "action": "replay",
            "label": labels[2],
            "anchors": [story["inspection_node"]],
            "depth": 1,
            "loop": True,
        }
        plans = {}
        for key, spec in specs.items():
            plan = build_plan(artifact["view"], spec, artifact["recording"])
            validate_evidence(plan, artifact["view"], artifact["recording"])
            plans[key] = plan
        result["locales"][language] = plans
    target = ROOT / "docs/site/control-plans.json"
    target.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return result


if __name__ == "__main__":
    build()
    print("Built checked conversation-control plans from the recorded project")
