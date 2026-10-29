"""Test focus-restoration ordering through native UI only; observe, never patch handlers."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent
GRAPH = "http://127.0.0.1:8841"
original = json.loads((BASE / "preferences-original.json").read_text(encoding="utf-8"))
results = []
with sync_playwright() as playwright:
    client = playwright.request.new_context()
    initial_events = len(client.get(GRAPH + "/api/view").json()["events"])
    try:
        for refresh in (False, True):
            current = client.get(GRAPH + "/api/preferences").json()
            assert client.post(GRAPH + "/api/preferences", data={**original, "revision": current["revision"]}).status == 200
            browser = playwright.chromium.launch(headless=True, args=["--no-proxy-server"])
            page = browser.new_page(viewport={"width": 1500, "height": 1100})
            network = []
            page.on("response", lambda response: network.append({"url": response.url, "status": response.status,
                "response_build_id": response.json().get("build_id")}) if "/source?" in response.url else None)
            try:
                page.goto(GRAPH + "/graph", wait_until="domcontentloaded")
                page.wait_for_function("document.querySelector('[data-node-id=\"revoke\"]') !== null", timeout=20000)
                page.evaluate("""() => {
                    window.sourceFocusTrace=[];
                    const snap=(kind,target)=>sourceFocusTrace.push({at:performance.now(),kind,
                        target:target?.id||target?.dataset?.nodeId||target?.tagName,
                        active:document.activeElement?.id||document.activeElement?.dataset?.nodeId,
                        hidden:document.querySelector('#node-details').hidden,
                        selected:document.querySelector('[data-node-id][aria-pressed="true"]')?.dataset.nodeId});
                    for(const type of ['focusin','focusout','click'])
                        document.addEventListener(type,e=>snap(type,e.target),true);
                    new MutationObserver(()=>snap('panel-visibility',document.querySelector('#node-details')))
                        .observe(document.querySelector('#node-details'),{attributes:true,attributeFilter:['hidden']});
                }""")
                page.locator('[data-node-id="revoke"]').focus()
                if refresh:
                    page.locator("#analysis-details").click()
                page.locator('[data-node-id="revoke"]').focus()
                page.keyboard.press("Shift+F10")
                page.locator("#source").click()
                page.wait_for_timeout(1500)
                results.append({"native_semantic_rerender_after_selection": refresh,
                    "source_panel_visible": page.locator("#source-code").is_visible(),
                    "source_ready": "def revoke" in page.locator("#source-code").inner_text(),
                    "network": network, "trace": page.evaluate("sourceFocusTrace")})
                (BASE / "source-focus-probe.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            finally:
                browser.close()
    finally:
        current = client.get(GRAPH + "/api/preferences").json()
        assert client.post(GRAPH + "/api/preferences", data={**original, "revision": current["revision"]}).status == 200
        assert client.get(GRAPH + "/api/preferences").json()["entries"] == original["entries"]
        assert len(client.get(GRAPH + "/api/view").json()["events"]) == initial_events
        client.dispose()
print(json.dumps([{key: row[key] for key in ("native_semantic_rerender_after_selection", "source_panel_visible", "source_ready", "network")} for row in results]))
