"""Inspect actual rendered presets without changing the user's saved preferences."""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

parser = argparse.ArgumentParser()
parser.add_argument("--out", type=Path, required=True)
parser.add_argument("--browser", required=True)
args = parser.parse_args()
args.out.mkdir(exist_ok=False)
base = "http://127.0.0.1:50958"
presets = ["business", "states", "permission", "api", "functions", "project",
           "code", "data-operations", "database"]
with sync_playwright() as driver:
    browser = driver.chromium.launch(headless=True, executable_path=args.browser)
    page = browser.new_page(viewport={"width": 1520, "height": 1060})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    preferences = page.request.get(base + "/api/preferences").json()
    def private_preferences(route):
        global preferences
        if route.request.method == "POST":
            preferences = {**route.request.post_data_json, "revision": preferences["revision"] + 1}
        route.fulfill(json=preferences)
    page.route("**/api/preferences", private_preferences)
    try:
        page.goto(base + "/graph?lang=zh-CN")
        page.wait_for_function("typeof graphDebug!=='undefined' && graphDebug.displayGraph")
        page.locator("#record-list").select_option("")
        results = []
        for preset in presets:
            page.locator("#analysis-view").select_option(preset)
            page.wait_for_function("graphDebug.displayGraph.boxes.length>0 && graphDebug.presentation.glyphs.size>0")
            if preset in ("project", "database"):
                page.locator("#expand").click()
                page.wait_for_function("graphDebug.displayGraph.boxes.length>1")
            if page.locator("#layered-toggle").get_attribute("aria-pressed") == "true":
                page.locator("#layered-toggle").click()
            page.locator("#arrange").click()
            page.wait_for_function("!graphDebug.layoutBusy")
            expect(page.locator("#empty")).to_be_hidden()
            counts = page.evaluate("({boxes:graphDebug.displayGraph.boxes.length,edges:graphDebug.displayGraph.edges.length,types:[...new Set(graphDebug.displayGraph.boxes.map(b=>b.type))],visible:graphDebug.layers.visible})")
            assert counts["boxes"] > 0, (preset, counts)
            # A preset's original relations must survive its node/type filter.
            assert counts["edges"] > 0, (preset, counts)
            results.append({"preset": preset, **counts})
            page.screenshot(path=str(args.out / (preset + ".png")))
        assert not errors, errors
        result = {"passed": True, "presets": results, "page_errors": errors,
                  "preferences_isolated": True, "basis": "Actual installed viewer, live project source and public UI controls"}
        (args.out / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps({"passed": True, "counts": {p["preset"]:[p["boxes"],p["edges"]] for p in results}}))
    except BaseException as error:
        page.screenshot(path=str(args.out / "failure.png"))
        (args.out / "failure.json").write_text(json.dumps({"error":str(error),"page_errors":errors},indent=2),encoding="utf-8")
        raise
    finally:
        browser.close()
