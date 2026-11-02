"""Keep an actual browser in old replay while the application loads a new build."""
import hashlib
import json
from pathlib import Path
import sys
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / ".tmp/browserdeps"))
from playwright.sync_api import sync_playwright
BASE = "http://127.0.0.1:8983"
RID = json.loads((OUT / "browser-flow.json").read_text(encoding="utf-8"))["recording_id"]
def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2), encoding="utf-8")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe", args=["--enable-unsafe-swiftshader"])
    page = browser.new_page(viewport={"width": 1540, "height": 1100})
    page.goto(BASE + "/graph")
    page.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy")
    page.locator("#record-list").select_option(RID)
    page.wait_for_function("graphDebug.timeline?.source==='saved'")
    before = page.request.get(BASE + "/api/view").json()
    raw = ROOT / "bo_stategraph/data/recordings" / (RID + ".json")
    original = hashlib.sha256(raw.read_bytes()).hexdigest()
    save("reload-ready.json", {"old_build": before["manifest"]["build_id"], "recording": RID, "raw_sha256": original})
    page.wait_for_function("build=>graphDebug.view.manifest.build_id!==build && !document.body.classList.contains('is-replay')", arg=before["manifest"]["build_id"], timeout=600000)
    page.wait_for_function("id=>!Array.from(document.querySelector('#record-list').options).some(o=>o.value===id)", arg=RID)
    after = page.request.get(BASE + "/api/view").json()
    status = page.request.get(BASE + "/api/recordings/" + RID).status
    assert status == 404 and hashlib.sha256(raw.read_bytes()).hexdigest() == original
    page.screenshot(path=str(OUT / "actual-reload-invalidated-old-replay.png"))
    save("graph-reload.json", {"valid": True, "old_build": before["manifest"]["build_id"], "new_build": after["manifest"]["build_id"],
        "old_recording": RID, "old_api_status": status, "old_private_bytes_preserved": True,
        "replay_left": True, "old_option_removed": True,
        "method": "Same real browser remained open in replay while normal source rebuild and owned native producer/service restart loaded the current graph."})
    browser.close()
