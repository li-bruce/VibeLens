"""Diagnose the native source panel without patching source or injecting results."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = Path(__file__).resolve().parent
capture = json.loads((BASE / "browser-native/capture-report.json").read_text())
rows = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=["--no-proxy-server"])
    page = browser.new_page(viewport={"width": 1500, "height": 1100})
    network = []
    page.on("request", lambda request: network.append({"request": request.url}) if "/source?" in request.url else None)
    page.on("response", lambda response: network.append({"response": response.url, "status": response.status}) if "/source?" in response.url else None)
    try:
        page.goto("http://127.0.0.1:8841/graph", wait_until="domcontentloaded")
        page.wait_for_function("document.querySelector('[data-node-id=\"revoke\"]') !== null", timeout=20000)
        for mode in ("live", "recording"):
            if mode == "recording":
                page.locator("#record-list").select_option(capture["recording_id"])
                expect(page.locator("#replay")).to_be_visible()
            page.locator('[data-node-id="revoke"]').focus()
            page.locator("#selection-menu").click()
            page.locator("#source").click()
            page.wait_for_timeout(2500)
            rows.append({"mode": mode, "url": page.url,
                "title": page.locator("#detail-title").inner_text(),
                "content_prefix": page.locator("#source-code").inner_text()[:180],
                "location": page.locator("#source-code").get_attribute("data-location"),
                "network": list(network)})
            (BASE / "source-probe.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
            page.screenshot(path=str(BASE / "browser-native" / ("source-probe-" + mode + ".png")), full_page=True)
            if page.locator("#close-detail").is_visible():
                page.locator("#close-detail").click()
    finally:
        browser.close()
(BASE / "source-probe.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(rows, ensure_ascii=False))
