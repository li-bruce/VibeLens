"""Read the native viewer's real controls before writing the focused acceptance."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

OUT = Path(__file__).resolve().parent
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=["--no-proxy-server"])
    page = browser.new_page(viewport={"width": 1450, "height": 1050})
    original = page.request.get("http://127.0.0.1:8841/api/preferences").json()
    target = OUT / "preferences-original.json"
    if not target.exists():
        target.write_text(json.dumps(original, ensure_ascii=False, indent=2), encoding="utf-8")
    page.goto("http://127.0.0.1:8841/graph", wait_until="domcontentloaded")
    expect(page.locator("#canvas-host canvas")).to_be_visible(timeout=20000)
    page.wait_for_function("document.querySelector('#semantic').children.length > 0", timeout=20000)
    controls = page.evaluate("""() => [...document.querySelectorAll('button,select')]
        .filter(e => e.offsetWidth && e.offsetHeight).map(e => ({id:e.id,
        label:e.getAttribute('aria-label') || e.textContent.trim().slice(0,80),
        options:e.tagName==='SELECT'?[...e.options].map(o=>({value:o.value,text:o.text})):null}))""")
    report = {"controls": controls, "semantic_nodes": page.locator("[data-node-id]").count(),
              "semantic_edges": page.locator("[data-edge-id]").count(),
              "preference_entries": len(original["entries"])}
    (OUT / "viewer-controls.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    browser.close()
