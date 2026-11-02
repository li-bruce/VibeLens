"""Inspect real saved recording controls without synthesizing any runtime event."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".tmp/browserdeps"))
from playwright.sync_api import sync_playwright

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe", args=["--enable-unsafe-swiftshader"])
    page = browser.new_page(viewport={"width": 1540, "height": 1100})
    page.goto("http://127.0.0.1:8983/graph")
    page.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy")
    listing = page.request.get("http://127.0.0.1:8983/api/recordings").json()
    save("recordings-current.json", listing)
    rid = "5ad97257db954dd0b2c85cadb0f9059d"
    page.wait_for_function("id => Array.from(document.querySelector('#record-list').options).some(o=>o.value===id)", arg=rid)
    page.locator("#record-list").select_option(rid)
    page.wait_for_function("graphDebug.timeline?.source === 'saved' && graphDebug.timeline?.geometry")
    page.locator("#replay-grain").select_option("events")
    page.locator(".trace-scope").select_option("all")
    page.locator(".trace-maximize").click()
    page.screenshot(path=str(OUT / "timeline-probe.png"))
    save("viewer-state.json", page.evaluate("({keys:Object.keys(graphDebug),timeline:graphDebug.timeline,options:Array.from(document.querySelectorAll('#analysis-view option')).map(o=>({value:o.value,text:o.textContent})),recordValue:document.querySelector('#record-list').value})"))
    (OUT / "viewer-probe-dom.html").write_text(page.content(), encoding="utf-8")
    recording = page.request.get("http://127.0.0.1:8983/api/recordings/" + rid).json()
    assert recording["id"] == rid and recording["status"] == "stopped" and not recording["gaps"]
    save("actual-recording-recovered.json", recording)
    save("browser-recording-receipt.json", {"valid": True, "id": rid, "events": len(recording["events"]), "gaps": recording["gaps"],
        "selected_in_browser": page.locator("#record-list").input_value(), "note": "The initial automation sampled the dropdown before its asynchronous options refresh; retained invalid-ID response is not recording evidence."})
    print(json.dumps({"record": rid, "events": len(recording["events"]), "trace": page.evaluate("({groups:graphDebug.timeline.groups,rows:graphDebug.timeline.rows.length})")}))
    browser.close()
