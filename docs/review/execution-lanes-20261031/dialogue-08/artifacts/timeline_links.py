"""Inspect actual lifecycle links across every scrollable row of the real recording."""
from collections import Counter
import json
from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
sys.path.insert(0,str(ROOT/".tmp/browserdeps"))
from playwright.sync_api import sync_playwright
BASE="http://127.0.0.1:8983"
RID=json.loads((OUT/"browser-flow.json").read_text(encoding="utf-8"))["recording_id"]
def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding="utf-8")
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",args=["--enable-unsafe-swiftshader"])
    page=browser.new_page(viewport={"width":1540,"height":1100})
    page.goto(BASE+"/graph");page.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy")
    before=page.request.get(BASE+"/api/view").json()
    page.locator("#record-list").select_option(RID)
    page.wait_for_function("graphDebug.timeline?.source==='saved' && graphDebug.timeline?.geometry")
    page.locator("#replay-grain").select_option("events")
    page.locator(".trace-scope").select_option("all")
    page.locator(".trace-depth").select_option("all")
    if page.evaluate("graphDebug.timeline.layerMode==='single'"):page.locator(".trace-single").click()
    if page.evaluate("graphDebug.timeline.rows.every(r=>r.layer==='business')"):page.locator(".trace-tracks").click()
    if "trace-maximized" not in (page.locator("#recording-timeline").get_attribute("class") or ""):page.locator(".trace-maximize").click()
    page.locator(".trace-fit").click();page.wait_for_function("!graphDebug.timeline.zooming")
    initial=page.evaluate("graphDebug.timeline");save("lifecycle-timeline-full.json",initial)
    routes={};samples=[]
    for i in range(30):
        value=page.evaluate("graphDebug.timeline")
        samples.append({"scroll":value["scroll"],"routes":len(value["routes"]),"flows":value.get("flows")})
        for route in value["routes"]:routes[route["key"]]=route
        canvas=page.locator("#recording-timeline canvas").bounding_box()
        page.mouse.move(canvas["x"]+canvas["width"]*.65,canvas["y"]+canvas["height"]*.65)
        page.mouse.wheel(0,420)
        page.wait_for_timeout(100)
        after=page.evaluate("graphDebug.timeline.scroll")
        if after==value["scroll"]:break
    rows=initial["rows"]
    vertical=[r for r in routes.values() if r["fromRow"]!=r["toRow"]]
    horizontal=[r for r in routes.values() if r["fromRow"]==r["toRow"]]
    assert vertical and horizontal
    kinds=Counter(r["type"] for r in routes.values())
    assert {"call","return"}<=set(kinds)
    lifecycles=initial["lifecycles"]
    assert any(l.get("terminal",{}).get("state")=="committed" for l in lifecycles)
    assert any(l.get("terminal",{}).get("state")=="exception" for l in lifecycles)
    assert not initial["unassignedObservations"]
    page.screenshot(path=str(OUT/"timeline-lifecycle-links.png"))
    live=page.request.get(BASE+"/api/view").json()
    assert [e["id"] for e in before["events"]]==[e["id"] for e in live["events"]]
    save("lifecycle-links.json",{"valid":True,"recording":RID,"build_id":live["manifest"]["build_id"],"rows":rows,
        "route_types":dict(kinds),"vertical_routes":len(vertical),"horizontal_routes":len(horizontal),
        "samples":samples,"routes":list(routes.values()),"lifecycle_count":len(lifecycles),
        "observer_events_unchanged":len(live["events"]),"boundary":"All scrollable rendered rows of this real recording; static source mapping has no fabricated execution lifetime."})
    browser.close()
