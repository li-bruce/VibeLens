"""Record live/replay source responses and UI readiness through two native menus."""
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = Path(__file__).resolve().parent
OUT = BASE / "browser-native"
GRAPH = "http://127.0.0.1:8841"
recording = json.loads((OUT / "recording.json").read_text(encoding="utf-8"))
original = json.loads((BASE / "preferences-original.json").read_text(encoding="utf-8"))
rows = []
with sync_playwright() as playwright:
    client = playwright.request.new_context()
    before = client.get(GRAPH + "/api/view").json()
    try:
        for mode in ("live", "replay"):
            for menu in ("keyboard", "visible-actions"):
                browser = playwright.chromium.launch(headless=True, args=["--no-proxy-server"])
                network = []
                try:
                    page = browser.new_page(viewport={"width": 1500, "height": 1100})
                    def response_seen(response):
                        if "/source?" not in response.url:
                            return
                        item = {"url": response.url, "status": response.status}
                        if response.ok:
                            data = response.json()
                            item.update(response_build_id=data.get("build_id"),
                                        code_revision=data.get("code_revision"),
                                        source_sha256=hashlib.sha256(data.get("source", "").encode()).hexdigest())
                        network.append(item)
                    page.on("response", response_seen)
                    page.goto(GRAPH + "/graph", wait_until="domcontentloaded")
                    page.wait_for_function("document.querySelector('[data-node-id=\"revoke\"]') !== null", timeout=20000)
                    if mode == "replay":
                        page.locator("#record-list").select_option(recording["id"])
                        expect(page.locator("#replay")).to_be_visible()
                    page.locator('[data-node-id="revoke"]').focus()
                    if menu == "keyboard":
                        page.keyboard.press("Shift+F10")
                    else:
                        page.locator("#selection-menu").click()
                    page.locator("#source").click()
                    page.wait_for_timeout(2500)
                    rows.append({"mode": mode, "menu": menu, "recording_id": recording["id"] if mode == "replay" else None,
                        "view_build_id": recording["build_id"] if mode == "replay" else before["manifest"]["build_id"],
                        "recording_manifest_build_id": recording["context"]["manifest"]["build_id"] if mode == "replay" else None,
                        "source_panel_visible": page.locator("#source-code").is_visible(),
                        "source_ready": "def revoke" in page.locator("#source-code").inner_text(),
                        "source_location": page.locator("#source-code").get_attribute("data-location"),
                        "detail_title": page.locator("#detail-title").inner_text(), "network": network})
                    (BASE / "source-matrix.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
                    page.screenshot(path=str(OUT / f"source-{mode}-{menu}.png"), full_page=True)
                finally:
                    browser.close()
    finally:
        current = client.get(GRAPH + "/api/preferences").json()
        response = client.post(GRAPH + "/api/preferences", data={**original, "revision": current["revision"]})
        assert response.status == 200
        assert client.get(GRAPH + "/api/preferences").json()["entries"] == original["entries"]
        after = client.get(GRAPH + "/api/view").json()
        assert len(after["events"]) == len(before["events"])
        client.dispose()
print(json.dumps(rows, ensure_ascii=False))
