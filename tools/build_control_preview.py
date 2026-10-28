"""Export checked view/replay plans for the Pages conversation-control examples."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.control.selection import build_plan, validate_evidence


def build():
    """Select original case identities with the same controller used by a project."""
    artifact = json.loads((ROOT / "docs/site/case-data/v1.json").read_text(encoding="utf-8"))
    result = {"case": 1, "locales": {}}
    for language, labels in {
        "en": ["Upload and approval", "Approval and parameters", "Approval replay"],
        "zh-CN": ["上传与审核", "审核与参数", "审核链路回放"],
    }.items():
        specs = {
            "business": {
                "action": "view",
                "label": labels[0],
                "anchors": ["upload", "publish"],
                "depth": 0,
                "direction": "forward",
                "nodes": ["business"],
                "edges": ["flow"],
                "layout": "layered",
            },
            "details": {
                "action": "view",
                "label": labels[1],
                "anchors": ["publish", "review-policy"],
                "depth": 0,
                "nodes": ["business", "decision", "data", "function"],
                "edges": ["call", "flow", "guard", "data"],
                "layout": "layered",
            },
        }
        specs["replay"] = {
            **specs["details"],
            "action": "replay",
            "label": labels[2],
            "anchors": ["review-policy"],
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
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return result


if __name__ == "__main__":
    build()
    print("Built checked conversation-control plans from the recorded project")
