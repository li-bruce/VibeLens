"""Native browser interaction checks against this project's fresh real recording."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".tmp/browserdeps"))
from playwright.sync_api import sync_playwright

RID = "5ad97257db954dd0b2c85cadb0f9059d"
BASE = "http://127.0.0.1:8983"
CHECKS, ERRORS = [], []

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

def trace(page):
    return page.evaluate("graphDebug.timeline")

def stable(page):
    page.wait_for_function("!graphDebug.layoutBusy")

def cursor(page):
    t = trace(page)
    assert page.locator("#replay-position").get_attribute("data-event-id") == t["eventId"]
    assert page.locator("#recording-timeline").get_attribute("data-event-id") == t["eventId"]
    assert page.evaluate("graphDebug.view.replay.index") == t["raw"]
    assert json.loads(page.locator("#recording-timeline").get_attribute("data-graph-transfers")) == t["transfers"]
    return t

def open_recording(page):
    page.wait_for_function("id=>Array.from(document.querySelector('#record-list').options).some(o=>o.value===id)", arg=RID)
    page.locator("#record-list").select_option(RID)
    page.wait_for_function("graphDebug.timeline?.source==='saved' && graphDebug.timeline?.geometry")
    page.locator("#replay-grain").select_option("events")
    page.locator(".trace-scope").select_option("all")

def pick(page, node):
    selector = '#semantic [data-node-id="' + node + '"]'
    if page.locator(selector).count() == 0:
        page.locator("#node-search").fill(node)
        page.locator("#node-search").press("Enter")
        page.wait_for_function("id=>graphDebug.graph.byId.has(id)", arg=node)
        page.locator("#node-search").fill("")
    page.locator(selector).dispatch_event("click")

def menu(page, command):
    page.locator("#selection-menu").click()
    page.locator(command).click()

def timeline_checks(page):
    open_recording(page)
    page.locator(".trace-maximize").click()
    page.locator(".trace-fit").click()
    page.wait_for_function("!graphDebug.timeline.zooming")
    initial = trace(page)
    groups = {}
    for row in initial["rows"]:
        groups.setdefault(row["group"], []).append(row["layer"])
    assert all(layers[0] == "business" and len(layers) == len(set(layers)) for layers in groups.values())
    assert initial["groups"] == len(groups) > 1
    recording = json.loads((OUT / "actual-recording-recovered.json").read_text(encoding="utf-8"))
    http_roots = {event["id"] for event in recording["events"] if event["node"] == "http_request" and event["phase"] == "enter"}
    calls = [item for item in initial["executions"] if item["root"] in http_roots]
    overlapping = [(a, b) for index, a in enumerate(calls) for b in calls[index + 1:] if a["start"] < b["end"] and b["start"] < a["end"]]
    assert overlapping and all(a["lane"] != b["lane"] for a, b in overlapping)
    life = [item for item in initial["lifecycles"] if item["node"] in {"db_transaction", "db_metadata", "db_users"}]
    assert life and all(not item["unfinished"] for item in life)
    assert any(item.get("terminal", {}).get("state") == "committed" for item in life)
    assert any(item.get("terminal", {}).get("state") == "exception" for item in life)
    CHECKS.append({"case": "one row per layer in every execution group", "groups": len(groups), "rows": len(initial["rows"]), "overlapping_http_pairs_in_separate_lanes": len(overlapping), "data_lifecycles_closed": len(life)})
    canvas = page.locator("#recording-timeline canvas")
    box = canvas.bounding_box()
    page.mouse.click(box["x"] + 50, box["y"] + initial["geometry"]["top"] + 14)
    page.wait_for_function("count=>graphDebug.timeline.rows.length<count", arg=len(initial["rows"]))
    folded = trace(page)
    first = next(iter(groups))
    assert [row["layer"] for row in folded["rows"] if row["group"] == first] == ["business"]
    assert all([row["layer"] for row in folded["rows"] if row["group"] == group] == layers for group, layers in groups.items() if group != first)
    page.screenshot(path=str(OUT / "timeline-one-group-collapsed.png"))
    page.mouse.click(box["x"] + 50, box["y"] + initial["geometry"]["top"] + 14)
    page.wait_for_function("count=>graphDebug.timeline.rows.length===count", arg=len(initial["rows"]))
    page.locator(".trace-tracks").click()
    page.wait_for_function("graphDebug.timeline.rows.every(r=>r.layer==='business')")
    page.locator(".trace-tracks").click()
    page.wait_for_function("count=>graphDebug.timeline.rows.length===count", arg=len(initial["rows"]))
    page.locator(".trace-depth").select_option("operations")
    assert all(row["layer"] in {"business", "state", "rules", "api", "execution", "operations"} for row in trace(page)["rows"])
    page.locator(".trace-single").click()
    assert all(row["layer"] == "operations" for row in trace(page)["rows"])
    page.locator(".trace-single").click()
    page.locator(".trace-depth").select_option("all")
    CHECKS.append({"case": "single group and all-group collapse, depth and single-layer controls", "valid": True})

    width = initial["window"]["end"] - initial["window"]["start"]
    page.locator(".trace-zoom-in").click()
    page.wait_for_function("width=>!graphDebug.timeline.zooming && graphDebug.timeline.window.end-graphDebug.timeline.window.start<width", arg=width)
    before_wheel = trace(page)["window"]
    page.mouse.move(box["x"] + initial["geometry"]["left"] + initial["geometry"]["plot"] * .5, box["y"] + 37)
    page.keyboard.down("Control")
    page.mouse.wheel(0, -180)
    page.keyboard.up("Control")
    page.wait_for_function("w=>graphDebug.timeline.window.end-graphDebug.timeline.window.start<w", arg=before_wheel["end"] - before_wheel["start"])
    page.locator(".trace-fit").click()
    page.wait_for_function("!graphDebug.timeline.zooming")
    t = trace(page)
    page.keyboard.down("Shift")
    page.mouse.move(box["x"] + t["geometry"]["left"] + t["geometry"]["plot"] * .15, box["y"] + 38)
    page.mouse.down()
    page.mouse.move(box["x"] + t["geometry"]["left"] + t["geometry"]["plot"] * .7, box["y"] + 38, steps=15)
    page.mouse.up()
    page.keyboard.up("Shift")
    assert trace(page)["range"]
    page.locator(".trace-loop").click()
    assert page.locator("#replay-loop").is_checked()
    page.locator(".trace-clear").click()
    assert not page.locator("#replay-loop").is_checked()
    page.locator(".trace-zoom-in").click()
    page.wait_for_function("!graphDebug.timeline.zooming")
    t = trace(page)
    old_start = t["window"]["start"]
    page.mouse.move(box["x"] + t["geometry"]["left"] + t["geometry"]["plot"] * .5, box["y"] + 12)
    page.mouse.down()
    page.mouse.move(box["x"] + t["geometry"]["left"] + t["geometry"]["plot"] * .6, box["y"] + 12, steps=10)
    page.mouse.up()
    page.wait_for_function("x=>graphDebug.timeline.window.start!==x", arg=old_start)
    CHECKS.append({"case": "toolbar and Ctrl-wheel zoom, Shift interval, loop and overview pan", "valid": True})
    page.locator(".trace-fit").click()
    page.wait_for_function("!graphDebug.timeline.zooming")
    t = trace(page)
    point = next(point for point in t["points"] if point["time"] > t["window"]["start"] + 3000)
    x = box["x"] + t["geometry"]["left"] + (point["time"] - t["window"]["start"]) / (t["window"]["end"] - t["window"]["start"]) * t["geometry"]["plot"]
    page.mouse.move(x - 2, box["y"] + 37)
    page.mouse.down()
    page.mouse.move(x, box["y"] + 37, steps=5)
    page.mouse.up()
    cursor(page)
    current = trace(page)["raw"]
    canvas.press("ArrowRight")
    page.wait_for_function("raw=>graphDebug.timeline.raw!==raw", arg=current)
    cursor(page)
    page.locator(".trace-inspect").click()
    payload = json.loads(page.locator(".trace-payload").inner_text())
    assert payload["id"] == trace(page)["eventId"]
    page.locator(".trace-inspect").click()
    page.locator(".trace-maximize").click()

    for mode in ("2D", "3D"):
        if page.locator("#legend-mode").inner_text() != mode:
            page.locator("#layered-toggle").click()
        stable(page)
        if mode == "3D":
            page.wait_for_function("graphDebug.spatial?.perspective && !graphDebug.layoutBusy")
            save("spatial-actual.json", page.evaluate("graphDebug.spatial"))
        page.locator("#replay-events").select_option(str(point["raw"]))
        t = cursor(page)
        page.locator("#replay-next").click()
        cursor(page)
        page.locator("#replay-prev").click()
        cursor(page)
        page.locator("#replay-speed").select_option("300")
        before = trace(page)["raw"]
        page.locator("#replay-play").click()
        page.wait_for_function("raw=>graphDebug.timeline.raw!==raw", arg=before)
        page.locator("#replay-play").click()
        cursor(page)
        page.screenshot(path=str(OUT / ("graph-timeline-" + mode.lower() + ".png")))
        CHECKS.append({"case": "graph/timeline seek, keyboard, play, pause and steps", "mode": mode, "event_id": t["eventId"]})
    if page.locator("#legend-mode").inner_text() != "2D":
        page.locator("#layered-toggle").click()
    page.locator("#replay-steps-toggle").click()
    step = page.locator("#replay-step-list input[data-event-id]").nth(5)
    sid = step.get_attribute("data-event-id")
    step.uncheck()
    assert sid not in [point["id"] for point in trace(page)["points"]]
    step.check()
    page.locator("#replay-steps-toggle").click()
    with page.expect_download() as exported:
        page.locator("#replay-export").click()
    export_path = OUT / "recording-browser-export.json"
    exported.value.save_as(str(export_path))
    value = json.loads(export_path.read_text(encoding="utf-8"))
    assert value["id"] == RID and value["events"] == recording["events"]
    CHECKS.append({"case": "skip/include and actual recording export preserves raw events", "valid": True})

def source_preferences(page):
    page.locator("#replay-live").click()
    page.wait_for_function("!document.body.classList.contains('is-replay')")
    page.locator("#analysis-view").select_option("overview")
    stable(page)
    pick(page, "upload_file")
    menu(page, "#source")
    page.locator("#source-code").wait_for(state="visible")
    code = page.locator("#source-code").inner_text()
    assert "class FileService" in code and "def visible_files" in code and "def upload" in code
    marks = page.locator("#source-code mark").all_text_contents()
    assert marks and "upload" in " ".join(marks)
    page.screenshot(path=str(OUT / "complete-source-highlight.png"))
    CHECKS.append({"case": "complete source file and exact authored function highlight", "marks": marks[:3]})
    page.locator("#close-detail").click()
    # Expand the actual source parameter node for token-level selection.
    menu(page, "#node-expand")
    stable(page)
    candidates = page.locator('#semantic [data-node-id]').evaluate_all("els=>els.map(e=>e.dataset.nodeId).filter(id=>id.startsWith('param:') && id.includes('upload'))")
    if candidates:
        pick(page, candidates[0])
        menu(page, "#source")
        page.locator("#source-code mark").first.wait_for()
        token = page.locator("#source-code mark").all_text_contents()
        save("source-parameter-highlight.json", {"node": candidates[0], "marks": token})
        assert token
        page.locator("#close-detail").click()
        CHECKS.append({"case": "bound source parameter token highlight", "node": candidates[0], "marks": token})
    else:
        CHECKS.append({"case": "bound source parameter token highlight", "status": "not_run", "reason": "No visible lexical parameter at this expansion; capture fields retain source-owner context."})
    pick(page, "upload_file")
    menu(page, "#annotate")
    prior = {"label": page.locator("#node-name").input_value(), "note": page.locator("#node-note").input_value(), "core": page.locator("#node-core").is_checked()}
    page.locator("#node-name").fill("Upload review check")
    page.locator("#node-note").fill("Fresh browser acceptance note; synthetic trial only.")
    page.locator("#node-core").check()
    page.locator('#annotation-form button[type="submit"]').click()
    page.locator("#viewport").focus()
    page.locator("#viewport").press("ArrowRight")
    page.locator("#viewport").press("p")
    before = page.evaluate("({x:graphDebug.graph.byId.get('upload_file').x,y:graphDebug.graph.byId.get('upload_file').y})")
    pick(page, "sign_out")
    page.locator("#viewport").press("Delete")
    assert page.locator('#semantic [data-node-id="sign_out"]').count() == 0
    page.locator("#filter-toggle").click()
    filter_node = page.locator('#filter-nodes input[value="resource"]')
    if filter_node.count():
        filter_node.uncheck()
    page.locator("#close-filters").click()
    page.wait_for_function("document.querySelector('#layout-status').textContent.includes('已保存') || document.querySelector('#layout-status').textContent.toLowerCase().includes('saved')")
    save("preferences-mutated.json", json.loads((ROOT / "bo_stategraph/config/views/local.json").read_text(encoding="utf-8")))
    page.reload()
    page.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy")
    assert page.locator('#semantic [data-node-id="sign_out"]').count() == 0
    pick(page, "upload_file")
    after = page.evaluate("({x:graphDebug.graph.byId.get('upload_file').x,y:graphDebug.graph.byId.get('upload_file').y})")
    assert before == after
    menu(page, "#annotate")
    assert page.locator("#node-name").input_value() == "Upload review check"
    assert page.locator("#node-note").input_value() == "Fresh browser acceptance note; synthetic trial only."
    assert page.locator("#node-core").is_checked()
    page.screenshot(path=str(OUT / "preferences-restored-on-reload.png"))
    page.locator("#node-name").fill(prior["label"])
    page.locator("#node-note").fill(prior["note"])
    page.locator("#node-core").set_checked(prior["core"])
    page.locator('#annotation-form button[type="submit"]').click()
    page.locator("#show-all").click()
    page.wait_for_function("graphDebug.graph.byId.has('sign_out')")
    CHECKS.append({"case": "name/note/core, position, individual hide and reload retention; all-elements restore", "before": before, "after": after, "valid": True})
    for preset in ("project", "api", "code", "database", "data-operations", "states", "business"):
        page.locator("#analysis-view").select_option(preset)
        stable(page)
        page.screenshot(path=str(OUT / ("view-" + preset + ".png")))
        CHECKS.append({"case": "actual projection selectable", "view": preset, "visible_nodes": page.locator('#semantic [data-node-id]').count()})
    page.locator("#analysis-view").select_option("overview")

def main():
    recording_bytes = (OUT / "actual-recording-recovered.json").read_bytes()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe", args=["--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width": 1540, "height": 1100})
        page.on("pageerror", lambda error: ERRORS.append(str(error)))
        page.goto(BASE + "/graph")
        page.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy")
        before = page.request.get(BASE + "/api/view").json()["events"]
        save("preferences-before-viewer-checks.json", json.loads((ROOT / "bo_stategraph/config/views/local.json").read_text(encoding="utf-8")))
        for name, operation in (("timeline", timeline_checks), ("source-and-preferences", source_preferences)):
            try:
                operation(page)
            except BaseException:
                ERRORS.append({"stage": name, "traceback": traceback.format_exc()})
                page.screenshot(path=str(OUT / ("failure-" + name + ".png")))
                save("failure-" + name + "-timeline.json", trace(page))
                (OUT / ("failure-" + name + "-dom.html")).write_text(page.content(), encoding="utf-8")
        after = page.request.get(BASE + "/api/view").json()["events"]
        assert [event["id"] for event in before] == [event["id"] for event in after]
        assert hashlib.sha256(recording_bytes).digest() == hashlib.sha256((OUT / "actual-recording-recovered.json").read_bytes()).digest()
        CHECKS.append({"case": "observer views, layout, source, playback and export create zero business events", "before": len(before), "after": len(after)})
        save("viewer-checks.json", {"valid": not ERRORS, "checks": CHECKS, "errors": ERRORS, "recording_id": RID})
        browser.close()
    assert not ERRORS, "See viewer-checks.json and retained screenshots"

if __name__ == "__main__":
    main()
    print("Real recording interaction checks passed")
