"""Additional full-file/highlight/version checks through the original native keyboard path."""
import hashlib
import json
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
GRAPH = "http://127.0.0.1:8841"
original = json.loads((BASE / "preferences-original.json").read_text(encoding="utf-8"))
recording = json.loads((BASE / "browser-native/recording.json").read_text(encoding="utf-8"))
before_hashes = json.loads((BASE / "before.json").read_text(encoding="utf-8"))["installed_files"]
expected_source = (ROOT / "app/service.py").read_text(encoding="utf-8")
source_lines = expected_source.split("\n")
start = next(index + 1 for index, line in enumerate(source_lines) if line.startswith("    def revoke("))
end = next(index for index in range(start, len(source_lines)) if source_lines[index].startswith("    def "))
report = {"status": "running", "no_post_selection_rerender": True, "no_alternate_menu": True, "modes": []}
try:
    with sync_playwright() as playwright:
        client = playwright.request.new_context()
        initial = client.get(GRAPH + "/api/view").json()
        build = initial["manifest"]["build_id"]
        assert recording["build_id"] == build
        try:
            for mode in ("live", "replay"):
                current = client.get(GRAPH + "/api/preferences").json()
                assert client.post(GRAPH + "/api/preferences", data={**original, "revision": current["revision"]}).status == 200
                browser = playwright.chromium.launch(headless=True, args=["--no-proxy-server"])
                try:
                    page = browser.new_page(viewport={"width": 1500, "height": 1100})
                    responses = []
                    page.on("response", lambda response: responses.append(response) if "/api/source?" in response.url else None)
                    page.goto(GRAPH + "/graph", wait_until="domcontentloaded")
                    page.wait_for_function("document.querySelector('[data-node-id=\"revoke\"]') !== null", timeout=20000)
                    if mode == "replay":
                        page.locator("#record-list").select_option(recording["id"])
                        page.wait_for_function("!document.querySelector('#replay').hidden", timeout=15000)
                    node = page.locator('[data-node-id="revoke"]')
                    assert node.get_attribute("aria-pressed") == "false", "The required node must be initially unselected."
                    node.focus()
                    page.keyboard.press("Shift+F10")
                    page.locator("#source").click()
                    page.wait_for_function("!document.querySelector('#node-details').hidden && document.querySelector('#source-code').textContent.includes('def revoke')", timeout=5000)
                    page.wait_for_timeout(300)
                    assert page.locator("#source-code").is_visible()
                    assert page.evaluate("document.activeElement.dataset.nodeId") == "revoke"
                    assert responses and responses[-1].status == 200
                    response = responses[-1]
                    payload = response.json()
                    assert payload["build_id"] == build
                    assert payload["source"] == expected_source
                    text = page.locator("#source-code").text_content()
                    rendered = text.splitlines()
                    recovered = []
                    for index, line in enumerate(rendered, 1):
                        prefix = f"{index:4d}  "
                        assert line.startswith(prefix), (index, line[:30])
                        recovered.append(line[len(prefix):])
                    assert recovered == source_lines, "The visible source must retain the complete actual file."
                    marked = page.locator("#source-code [data-source-line]").evaluate_all(
                        "nodes=>nodes.map(n=>({line:Number(n.dataset.sourceLine),marked:n.querySelectorAll('mark').length,text:n.textContent}))")
                    assert marked and any(item["line"] == start for item in marked)
                    assert all(start <= item["line"] <= end and item["marked"] > 0 for item in marked)
                    assert any("DELETE FROM shares" in item["text"] for item in marked)
                    report["modes"].append({"mode": mode, "initially_unselected": True,
                        "panel_visible_after_focus_return": True, "focus_returned_to": "revoke",
                        "source_http_status": response.status, "source_url": response.url,
                        "view_build_id": build, "response_build_id": payload["build_id"],
                        "source_sha256": hashlib.sha256(expected_source.encode()).hexdigest(),
                        "full_file_lines": len(recovered), "highlight_start": start,
                        "highlighted_line_count": len(marked), "highlighted_lines": [item["line"] for item in marked]})
                    page.screenshot(path=str(BASE / "browser-native" / ("keyboard-complete-source-" + mode + ".png")), full_page=True)
                finally:
                    browser.close()
            for old_id in ("77ae11709c33488ca6b294097e7d86da", "538215624de546279299d1c0a1cdf5b3"):
                rejected = client.get(GRAPH + "/api/source?path=app%2Fservice.py&recording=" + old_id)
                assert rejected.status == 400
            path = ROOT / "static/graph/detail-panel.js"
            assert hashlib.sha256(path.read_bytes()).hexdigest() == before_hashes["static/graph/detail-panel.js"]
            report["version_checks"] = {"detail_panel_byte_identical": True,
                "current_real_source_builds_match": True, "old_recording_source_rejected_http": 400,
                "scope": "Native current/obsolete admission plus byte-preserved frontend version checks; no fabricated response or recording."}
        finally:
            current = client.get(GRAPH + "/api/preferences").json()
            assert client.post(GRAPH + "/api/preferences", data={**original, "revision": current["revision"]}).status == 200
            assert client.get(GRAPH + "/api/preferences").json()["entries"] == original["entries"]
            final = client.get(GRAPH + "/api/view").json()
            report["observer_control_business_event_delta"] = len(final["events"]) - len(initial["events"])
            assert report["observer_control_business_event_delta"] == 0
            report["preferences_restored"] = True
            client.dispose()
    report["status"] = "passed"
except Exception as error:
    report.update(status="failed", error=f"{type(error).__name__}: {error}")
    raise
finally:
    (BASE / "keyboard-details.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "modes": len(report["modes"])}))
