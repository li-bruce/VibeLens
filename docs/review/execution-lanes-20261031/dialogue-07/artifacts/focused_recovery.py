"""Retain the original partial recording and independently check post-stop restoration."""
import json
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT))
from http_matrix import Client

def get():
    return json.load(urllib.request.urlopen("http://127.0.0.1:8983/api/view", timeout=30))

if __name__ == "__main__":
    recording = json.loads((OUT / "focused-recording.json").read_text(encoding="utf-8"))
    timeline = json.loads((OUT / "focused-timeline.json").read_text(encoding="utf-8"))
    flow = json.loads((OUT / "browser-flow.json").read_text(encoding="utf-8"))
    client = Client("cara")
    before = get()
    before_ids = {event["id"] for event in before["events"]}
    status, content = client.request("/files/" + flow["file_id"] + "/download")
    assert status == 200 and len(content) == flow["download_bytes"]
    deadline = time.monotonic() + 15
    while True:
        after = get()
        fresh = [event for event in after["events"] if event["id"] not in before_ids]
        if any(event["node"] == "http_request" and event["phase"] == "return" for event in fresh):
            break
        assert time.monotonic() < deadline, "Post-stop request did not drain"
        time.sleep(.1)
    restored = {event["node"] for event in fresh}
    assert {"http_request", "access_file", "db_file", "policy:actor_is_recipient"} <= restored
    all_events = {event["id"]: event for event in [*recording["context"].get("events", []), *recording["events"]]}
    points = [event for event in recording["events"] if event["node"] == "policy:actor_is_recipient"]
    owners = [{"event": event["id"], "entity": event["entity"], "parent_call_id": event.get("parent_call_id"),
        "parent_event_id": event.get("parent_event_id"), "parent_entry_available": event.get("parent_event_id") in all_events or
        any(item["phase"] == "enter" and item["call_id"] == event.get("parent_call_id") for item in all_events.values())}
        for event in points]
    result = {"recording_id": recording["id"], "status": "partial_boundary_unresolved", "capture": recording["capture"],
        "events": len(recording["events"]), "point_ownership": owners, "gaps": recording["gaps"],
        "timeline_invocations": timeline["invocationGroups"], "timeline_unassigned": timeline["unassignedObservations"],
        "truthful_ui_label": "Unassigned observations / 归属待确认", "screenshot": "focused-single-rule.png",
        "normal_capture_restored": True, "restored_event_count": len(fresh), "restored_nodes": sorted(restored),
        "producer_health_after": after["health"]["producer"],
        "driver_error": "Initial driver waited on frozen replay view instead of reading live API; original timeout retained."}
    (OUT / "focused-capture-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "focused-restoration-live.json").write_text(json.dumps(after, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
