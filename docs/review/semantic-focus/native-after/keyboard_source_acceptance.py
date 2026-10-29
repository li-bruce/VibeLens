"""Strict native keyboard source-path acceptance; no rerender or visible-menu bypass."""
from datetime import datetime, timezone
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent
GRAPH = "http://127.0.0.1:8841"
original = json.loads((BASE / "preferences-original.json").read_text(encoding="utf-8"))
report = {"status": "running", "requirement": "Newly select revoke -> Shift+F10 -> Source remains visible with real source text.",
          "no_rerender_after_selection": True, "no_alternate_menu": True,
          "started_at": datetime.now(timezone.utc).isoformat(), "network": []}
output = BASE / "keyboard-source-acceptance.json"
try:
    with sync_playwright() as playwright:
        client = playwright.request.new_context()
        before = client.get(GRAPH + "/api/view").json()
        report["view_build_id"] = before["manifest"]["build_id"]
        current = client.get(GRAPH + "/api/preferences").json()
        assert client.post(GRAPH + "/api/preferences", data={**original, "revision": current["revision"]}).status == 200
        browser = playwright.chromium.launch(headless=True, args=["--no-proxy-server"])
        try:
            page = browser.new_page(viewport={"width": 1500, "height": 1100})
            def response_seen(response):
                if "/source?" in response.url:
                    data = response.json() if response.ok else {}
                    report["network"].append({"url": response.url, "status": response.status,
                                                "response_build_id": data.get("build_id")})
            page.on("response", response_seen)
            page.goto(GRAPH + "/graph", wait_until="domcontentloaded")
            page.wait_for_function("document.querySelector('[data-node-id=\"revoke\"]') !== null", timeout=20000)
            page.evaluate("""() => {
                window.keyboardSourceTrace=[];
                const node=document.querySelector('[data-node-id="revoke"]');
                const panel=document.querySelector('#node-details');
                const snap=(kind,target,old=null)=>keyboardSourceTrace.push({at:performance.now(),kind,
                    target:target?.id||target?.dataset?.nodeId,old,
                    active:document.activeElement?.id||document.activeElement?.dataset?.nodeId,
                    panel_hidden:panel.hidden,selected:node.getAttribute('aria-pressed')});
                for(const type of ['focusin','focusout','click'])
                    document.addEventListener(type,e=>snap(type,e.target),true);
                new MutationObserver(items=>items.forEach(m=>snap(m.attributeName,m.target,m.oldValue)))
                    .observe(node,{attributes:true,attributeFilter:['aria-pressed'],attributeOldValue:true});
                new MutationObserver(items=>items.forEach(m=>snap('panel-hidden',m.target,m.oldValue)))
                    .observe(panel,{attributes:true,attributeFilter:['hidden'],attributeOldValue:true});
            }""")
            page.locator('[data-node-id="revoke"]').focus()
            page.keyboard.press("Shift+F10")
            page.locator("#source").click()
            try:
                page.wait_for_function("!document.querySelector('#source-code').hidden && !document.querySelector('#node-details').hidden && document.querySelector('#source-code').textContent.includes('def revoke')", timeout=5000)
            finally:
                report["source_panel_visible"] = page.locator("#source-code").is_visible()
                report["source_ready"] = "def revoke" in page.locator("#source-code").inner_text()
                report["trace"] = page.evaluate("keyboardSourceTrace")
                page.screenshot(path=str(BASE / "browser-native/strict-keyboard-source.png"), full_page=True)
            assert report["source_panel_visible"] and report["source_ready"]
            report["status"] = "passed"
        finally:
            browser.close()
            current = client.get(GRAPH + "/api/preferences").json()
            assert client.post(GRAPH + "/api/preferences", data={**original, "revision": current["revision"]}).status == 200
            report["preferences_restored"] = client.get(GRAPH + "/api/preferences").json()["entries"] == original["entries"]
            after = client.get(GRAPH + "/api/view").json()
            report["observer_control_business_event_delta"] = len(after["events"]) - len(before["events"])
            assert report["preferences_restored"] and report["observer_control_business_event_delta"] == 0
            client.dispose()
except Exception as error:
    report.update(status="failed", error=f"{type(error).__name__}: {error}")
    raise
finally:
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report.get(key) for key in ("status", "source_panel_visible", "source_ready", "view_build_id")}))
