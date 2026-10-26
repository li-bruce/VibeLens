"""Verify exported case data against its source build and native data contracts."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))

from bo_observer.data.sync import runtime_errors
from bo_observer.graph.behavior_model import check
from bo_observer.protocol import validate_event
from bo_observer.code_graph.service import CodeGraph


def verify(root, artifact):
    """Check original evidence; never regenerate an export during verification."""
    project = json.loads((root / "bo_stategraph/project.json").read_text(encoding="utf-8"))
    view = artifact["view"]
    assert check(root, project["model"], view["manifest"])["status"] == "current"
    for event in view["events"]:
        # The collector adds stream identity and replaces seq with receipt order.
        # Validate the original native envelope, retaining its producer sequence.
        native = {
            key: value for key, value in event.items() if key not in {"stream_id", "source_seq"}
        }
        native["seq"] = event["source_seq"]
        validate_event(native, project, view["manifest"]["build_id"])
    errors = runtime_errors(
        root,
        {"runs": [{"case": "replacement-review", "mode": "on", "events": view["events"]}]},
        project["model"],
    )
    assert not errors, json.dumps(errors, indent=2)
    assert CodeGraph(root).view(limit=1500, depth=3)["revision"] == artifact["code"]["revision"]
    for name, text in artifact["sources"].items():
        assert (root / name).read_text(encoding="utf-8") == text, name
    assert artifact["recording"]["gaps"] == []
    assert len({event["id"] for event in view["events"]}) == len(view["events"])
    assert (
        artifact["recording"]["events"] == view["events"]
    ), "The exported interval must retain the full scenario"
    return {
        "passed": True,
        "build_id": view["manifest"]["build_id"],
        "data_contract": "passed",
        "source_binding": "passed",
        "recording_gaps": 0,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    arguments = parser.parse_args()
    print(
        json.dumps(
            verify(arguments.root, json.loads(arguments.artifact.read_text(encoding="utf-8")))
        )
    )
