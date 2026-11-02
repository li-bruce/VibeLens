"""Resolve real invocation entries using explicit references, never timestamps."""
from collections import Counter
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent

def main():
    recording = json.loads((OUT / "actual-recording.json").read_text(encoding="utf-8"))
    events = recording["events"]
    context = recording.get("context", {}).get("events", [])
    by_id = {event["id"]: event for event in [*context, *events]}
    entries = {event["call_id"]: event for event in by_id.values() if event["phase"] == "enter"}
    checks, points, roots = [], [], {}
    for event in events:
        assert event.get("kind", "probe") == "probe"
        parent_id = event.get("parent_event_id")
        if parent_id:
            parent = by_id[parent_id]
            assert parent["phase"] == "enter" and parent["call_id"] == event["parent_call_id"]
            assert all(parent[key] == event[key] for key in ("project_id", "build_id", "run_id", "producer_id"))
            assert parent["seq"] < event["seq"]
        elif event["phase"] != "enter":
            assert event["call_id"] in entries, ("internal fact without owner", event)
            parent = entries[event["call_id"]]
        else:
            parent = event
        trail, root = set(), parent
        while root.get("parent_event_id"):
            assert root["id"] not in trail
            trail.add(root["id"])
            root = by_id[root["parent_event_id"]]
            assert root["phase"] == "enter"
        assert root["node"] == "http_request" and root["phase"] == "enter", root
        roots[root["id"]] = root
        item = {"event": event["id"], "node": event["node"], "entity": event["entity"],
                "attempt": event["attempt"], "parent_event_id": parent_id,
                "parent_node": parent["node"], "root": root["id"], "request": root["inputs"]}
        checks.append(item)
        if event["node"].startswith("policy:") or event["node"] == "authorize_file" or event["phase"] == "change":
            points.append(item)
            if event.get("inputs", {}).get("bo_basis"):
                assert event["inputs"]["bo_basis"].startswith(event["entity"] + ":")
    assert points and any(value["entity"] != "application" for value in points)
    payload = {"valid": True, "events": len(events), "context_events": len(context),
               "actual_http_roots": len(roots), "point_observations": len(points),
               "root_nodes": dict(Counter(value["node"] for value in roots.values())),
               "checks": checks, "point_checks": points,
               "root_event_ids": sorted(roots), "events_unchanged": True}
    (OUT / "general-ownership-audit.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in payload.items() if key not in {"checks", "point_checks", "root_event_ids"}}))

if __name__ == "__main__":
    main()
