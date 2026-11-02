"""Exercise a single permission-node recording through the actual Web controls."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".tmp/browserdeps"))
sys.path.insert(0, str(OUT))
from playwright.sync_api import sync_playwright
from http_matrix import Client

BASE = "http://127.0.0.1:8983"
TARGET = "policy:actor_is_recipient"

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    workflow = json.loads((OUT / "browser-flow.json").read_text(encoding="utf-8"))
    client = Client("cara")
    path = "/files/" + workflow["file_id"] + "/download"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe", args=["--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width": 1540, "height": 1100})
        page.goto(BASE + "/graph")
        page.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy")
        page.locator("#analysis-view").select_option("permission")
        page.wait_for_function("!graphDebug.layoutBusy")
        page.locator("#node-search").fill(TARGET)
        page.locator("#node-search").press("Enter")
        page.wait_for_function("id=>graphDebug.graph.byId.has(id)", arg=TARGET)
        page.locator("#node-search").fill("")
        page.locator('#semantic [data-node-id="' + TARGET + '"]').dispatch_event("click")
        page.locator("#capture-mode").select_option("focused")
        page.locator("#record-start").click()
        page.wait_for_function("!document.querySelector('#record-stop').disabled")
        listing = page.request.get(BASE + "/api/recordings").json()
        save("focused-start.json", listing)
        ident = listing["active"]["id"]
        assert listing["active"]["capture"]["roots"] == [TARGET]
        assert "http_request" not in listing["active"]["capture"]["nodes"]
        status, content = client.request(path)
        assert status == 200 and len(content) == workflow["download_bytes"]
        page.locator("#record-stop").click()
        page.wait_for_function("graphDebug.timeline?.source==='saved'")
        page.wait_for_function("id=>Array.from(document.querySelector('#record-list').options).some(o=>o.value===id)", arg=ident)
        page.locator("#record-list").select_option(ident)
        page.wait_for_function("graphDebug.timeline?.source==='saved' && graphDebug.timeline?.geometry")
        page.locator(".trace-scope").select_option("all")
        page.locator(".trace-maximize").click()
        page.locator(".trace-fit").click()
        page.wait_for_function("!graphDebug.timeline.zooming")
        recording = page.request.get(BASE + "/api/recordings/" + ident).json()
        save("focused-recording.json", recording)
        timeline = page.evaluate("graphDebug.timeline")
        save("focused-timeline.json", timeline)
        page.screenshot(path=str(OUT / "focused-single-rule.png"))
        (OUT / "focused-dom.html").write_text(page.content(), encoding="utf-8")
        all_events = {event["id"]: event for event in [*recording["context"].get("events", []), *recording["events"]]}
        selected = [event for event in recording["events"] if event["node"] == TARGET]
        assert selected
        owners = [{"event": event["id"], "entity": event["entity"], "parent_call_id": event.get("parent_call_id"),
                   "parent_event_id": event.get("parent_event_id"), "parent_entry_available": event.get("parent_event_id") in all_events or
                   any(item["phase"] == "enter" and item["call_id"] == event.get("parent_call_id") for item in all_events.values())}
                  for event in selected]
        boundaries = [event for event in all_events.values() if event.get("context_only")]
        assert all(item["parent_entry_available"] for item in owners), owners
        assert boundaries and {event["node"] for event in boundaries} >= {"http_request", "access_file"}
        assert all(not event.get(key) for event in boundaries for key in ("inputs", "outputs", "basis", "dependencies"))
        ordinary = [event for event in recording["events"] if not event.get("context_only")]
        assert len(ordinary) == len(selected) == 1 and ordinary[0]["node"] == TARGET
        page.locator("#replay-grain").select_option("events")
        page.wait_for_function("document.querySelector('#replay-events').options.length === 3")
        assert not recording.get("ownership_gaps")
        assert all(gap == "Pre-recording context retains only the latest 2000 events." for gap in recording["gaps"])
        save("focused-boundary-audit.json", {"valid": True, "ordinary_steps": len(ordinary),
            "boundaries": boundaries, "owners": owners, "raw_events": len(recording["events"]),
            "replay_options": page.locator("#replay-events option").count(),
            "snapshot_steps": 2,
            "reported_context_limits": recording["gaps"],
            "limitations": "Only selected rule values and witnessed enclosing boundaries were collected; unselected values remain uncollected."})
        before = page.request.get(BASE + "/api/view").json()
        status, _ = client.request(path)
        assert status == 200
        deadline = time.monotonic() + 15
        while True:
            after = page.request.get(BASE + "/api/view").json()
            new_events = after["events"][len(before["events"]):]
            if {"http_request", "access_file", "db_file", TARGET} <= {event["node"] for event in new_events} and after["health"]["producer"]["pending"] == 0:
                break
            assert time.monotonic() < deadline, "Live API did not receive restored capture"
            time.sleep(.05)
        fresh = after["events"][len(before["events"]):]
        assert {"http_request", "access_file", "db_file", TARGET} <= {event["node"] for event in fresh}
        save("focused-capture-result.json", {"transport": "Real browser recording controls and actual HTTP download", "recording_id": ident,
            "requested_roots": [TARGET], "actual_capture": recording["capture"], "events": len(recording["events"]),
            "selected_point_ownership": owners, "timeline_invocations": timeline.get("invocationGroups"),
            "timeline_unassigned": timeline.get("unassignedObservations"), "gaps": recording["gaps"],
            "timeline_health_text": page.locator(".trace-health").inner_text(),
            "timeline_health_title": page.locator(".trace-health").get_attribute("title"),
            "normal_capture_restored": True, "restored_nodes": sorted({event["node"] for event in fresh}),
            "builder_count_test": "Separate in-process application test required; external HTTP alone cannot count builders."})
        browser.close()

if __name__ == "__main__":
    main()
