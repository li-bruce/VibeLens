"""Retest the shared join against unchanged facts from two real HTTP reviews.

This is a focused selector regression, not complete application acceptance.
The original failed plan, native readers and raw events remain untouched.
"""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.workflow.mapping_contract import assess_context_fields


def main():
    folder = Path(__file__).resolve().parent / "dialogue-03-context-reproduction"
    native = json.loads((folder / "native-facts.json").read_text(encoding="utf-8"))
    events = json.loads((folder / "raw-events.json").read_text(encoding="utf-8"))
    original = json.loads((folder / "context-plan.json").read_text(encoding="utf-8"))
    field = {
        **original["context_fields"][0],
        "id": "both-native-reviewers",
        "actual": ["principal_before", "actor"],
        "each": {
            "collection": ["native_requests"],
            "actual_key": [["native_sdk", "trace_id"], ["native_sdk", "span_id"]],
            "mapped_key": [["trace", "trace_id"], ["trace", "span_id"]],
        },
    }
    plan = {**original, "context_fields": [field]}
    payload = {
        "runs": [
            {"case": "two_reviewers", "mode": "on", "events": events, "native_requests": native}
        ]
    }
    joined = assess_context_fields(payload, plan)
    wrong = deepcopy(payload)
    review = next(
        event
        for event in wrong["runs"][0]["events"]
        if event["node"] == "review_file" and event["phase"] == "enter"
    )
    review["provenance"]["actor"] = {"id": "wrong-principal", "kind": "user"}
    negative = assess_context_fields(wrong, plan)
    missing = deepcopy(payload)
    missing["runs"][0]["native_requests"].pop()
    absent = assess_context_fields(missing, plan)
    value = {
        "passed": joined["valid"]
        and joined["checks"] == 2
        and not negative["valid"]
        and not absent["valid"],
        "scope": "Focused selector only; complete application acceptance is separate.",
        "raw_event_count": len(events),
        "unchanged_input_hashes": {
            name: sha256((folder / name).read_bytes()).hexdigest()
            for name in ("raw-events.json", "native-facts.json", "context-plan.json")
        },
        "joined": joined,
        "wrong_principal_rejected": negative,
        "missing_native_record_rejected": absent,
    }
    (folder / "joined-plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    (folder / "joined-retest.json").write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": value["passed"],
                "checks": joined["checks"],
                "unchanged_raw_events": len(events),
            }
        )
    )
    raise SystemExit(not value["passed"])


if __name__ == "__main__":
    main()
