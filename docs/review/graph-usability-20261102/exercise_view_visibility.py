"""Check actual rendered project views against preserved narrow legacy visibility."""

import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "skills/vibelens/assets/stategraph-viewer"
parser = argparse.ArgumentParser()
parser.add_argument("--out", type=Path, required=True)
parser.add_argument("--browser", required=True)
parser.add_argument("--candidate", action="store_true")
args = parser.parse_args()
args.out.mkdir(exist_ok=False)
BASE = "http://127.0.0.1:50958"
recording = json.loads((ROOT / "docs/review/graph-usability-20261102/native-busy-browser-09/result.json").read_text(encoding="utf-8"))["recording"]

with sync_playwright() as driver:
    browser = driver.chromium.launch(headless=True, executable_path=args.browser)
    page = browser.new_page(viewport={"width": 1520, "height": 1060})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    preferences = page.request.get(BASE + "/api/preferences").json()
    def private_view(route):
        global preferences
        if route.request.method == "POST":
            preferences = {**route.request.post_data_json, "revision": preferences["revision"] + 1}
        route.fulfill(json=preferences)
    page.route("**/api/preferences", private_view)
    if args.candidate:
        def asset(filename):
            def serve(route):
                route.fulfill(path=ASSETS / filename)
            return serve
        for name in ("viewer.js", "graph-layers.js"):
            page.route("**/" + name, asset(name))
    try:
        page.goto(BASE + "/graph?lang=zh-CN")
        page.wait_for_function("typeof graphDebug!=='undefined' && graphDebug.displayGraph")
        before = page.evaluate("graphDebug.layers")
        page.locator("#record-list").select_option(recording)
        page.wait_for_function("graphDebug.timeline?.source==='saved'")
        page.locator("#analysis-view").select_option("project")
        page.wait_for_function("graphDebug.displayGraph?.boxes.some(b=>b.node.code_role==='directory') && graphDebug.presentation?.glyphs.size>0")
        expect(page.locator("#empty")).to_be_hidden()
        if page.locator("#layered-toggle").get_attribute("aria-pressed") == "true":
            page.locator("#layered-toggle").click()
        page.locator("#expand").click()
        page.wait_for_function("graphDebug.displayGraph.boxes.some(b=>b.node.code_role==='file')")
        page.wait_for_function("graphDebug.presentation.glyphs.size>1 && graphDebug.displayGraph.edges.length>0")
        page.locator("#arrange").click()
        page.wait_for_function("!graphDebug.layoutBusy")
        page.locator("#fit").click()
        page.screenshot(path=str(args.out / "project-2d.png"))
        counts = page.evaluate("({boxes:graphDebug.displayGraph.boxes.length,files:graphDebug.displayGraph.boxes.filter(b=>b.node.code_role==='file').length,edges:graphDebug.displayGraph.edges.length,glyphs:graphDebug.presentation.glyphs.size,regions:graphDebug.presentation.regions.size})")
        # The canvas keyboard path is the same control used by sighted users.
        ruler = page.locator("#layer-controls canvas")
        ruler.focus()
        for _ in range(before["order"].index("project")):
            ruler.press("ArrowDown")
        def hidden_project_saved(response):
            if not response.url.endswith("/api/preferences") or response.request.method != "POST":
                return False
            entries = response.request.post_data_json.get("entries", {})
            for key, raw in entries.items():
                if key.endswith(":analysis"):
                    visibility = json.loads(raw).get("layerVisibility", {}).get("project")
                    if isinstance(visibility, list) and "project" not in visibility:
                        return True
            return False
        with page.expect_response(hidden_project_saved):
            ruler.press("Space")
        page.wait_for_function("!graphDebug.layers.visible.includes('project')")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_function("typeof graphDebug!=='undefined' && graphDebug.displayGraph && graphDebug.layers?.visible")
        expect(page.locator("#analysis-view")).to_have_value("project")
        assert "project" not in page.evaluate("graphDebug.layers.visible"), "Hidden layer returned after reload"
        ruler = page.locator("#layer-controls canvas")
        ruler.focus()
        for _ in range(before["order"].index("project")):
            ruler.press("ArrowDown")
        page.locator("#analysis-view").select_option("overview")
        page.wait_for_function("graphDebug.layers.visible.length===4")
        restored = page.evaluate("graphDebug.layers")
        assert restored["visible"] == before["visible"]
        page.locator("#analysis-view").select_option("project")
        page.wait_for_function("!graphDebug.layers.visible.includes('project')")
        ruler.focus()
        ruler.press("Space")
        page.wait_for_function("graphDebug.displayGraph.boxes.some(b=>b.node.code_role==='directory')")
        page.locator("#layered-toggle").click()
        page.wait_for_function("graphDebug.spatial?.perspective && !graphDebug.layoutBusy")
        page.locator("#fit").click()
        page.screenshot(path=str(args.out / "project-3d.png"))
        assert not errors, errors
        result = {"passed": True, "candidate_assets": args.candidate, "rendered": counts,
                  "overview_visibility_preserved": restored["visible"],
                  "project_visibility_independent": True, "visibility_survives_reload": True, "page_errors": errors}
        (args.out / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result))
    except BaseException as error:
        page.screenshot(path=str(args.out / "failure.png"))
        (args.out / "failure.json").write_text(json.dumps({"error": str(error), "page_errors": errors,
             "state": page.evaluate("({layers:graphDebug.layers,raw:graphDebug.graph?.boxes.length,visible:graphDebug.displayGraph?.boxes.length})")}, indent=2), encoding="utf-8")
        raise
    finally:
        browser.close()
