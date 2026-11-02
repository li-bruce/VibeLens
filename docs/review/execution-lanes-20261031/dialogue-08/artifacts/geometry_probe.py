"""Read actual rendered geometry before writing pointer acceptance checks."""
import json
from pathlib import Path
import sys
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / ".tmp/browserdeps"))
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe", args=["--enable-unsafe-swiftshader"])
    page = browser.new_page(viewport={"width": 1540, "height": 1100})
    page.goto("http://127.0.0.1:8983/graph")
    page.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy")
    if page.locator("#replay-live").is_visible():
        page.locator("#replay-live").click()
    page.locator("#analysis-view").select_option("overview")
    page.wait_for_function("!graphDebug.layoutBusy")
    if page.locator("#legend-mode").inner_text() != "2D":
        page.locator("#layered-toggle").click()
    page.locator("#fit").click()
    page.wait_for_function("!graphDebug.layoutBusy")
    value = page.evaluate("""() => ({camera:graphDebug.camera, boxes:graphDebug.graph.boxes.slice(0,8).map(b=>({id:b.id,x:b.x,y:b.y,w:b.w,h:b.h,parent:b.node.parent,expanded:b.expanded})),
      regions:graphDebug.graph.regions, captions:graphDebug.planarCaptions, presentation:{glyphs:[...graphDebug.presentation.glyphs],regions:[...graphDebug.presentation.regions]},
      graphKeys:Object.keys(graphDebug.graph),canvas:[...document.querySelectorAll('#canvas-host canvas')].map(c=>({rect:c.getBoundingClientRect().toJSON(),style:c.getAttribute('style')}))})""")
    (OUT / "geometry-probe.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
    page.screenshot(path=str(OUT / "geometry-probe.png"))
    browser.close()
