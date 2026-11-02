"""Run the real browser workflow and retain an actual application recording."""
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".tmp/browserdeps"))
sys.path.insert(0, str(OUT))
from playwright.sync_api import sync_playwright
from http_matrix import run as matrix

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

def main():
    os.environ["TEMP"] = os.environ["TMP"] = str(OUT / ".tmp")
    fixture = OUT / "fresh-browser-upload-20261101-02-current.txt"
    fixture.write_bytes(b"Fresh 2026-11-01 round 02: actual browser upload, colleague approval, directed sharing and download.\n")
    checks, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, downloads_path=str(OUT / "browser-downloads"), executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe",
            args=["--enable-unsafe-swiftshader"])
        graph = browser.new_page(viewport={"width": 1540, "height": 1100})
        graph.on("pageerror", lambda error: errors.append(str(error)))
        graph.goto("http://127.0.0.1:8983/graph")
        graph.wait_for_load_state("domcontentloaded")
        graph.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy")
        graph.screenshot(path=str(OUT / "graph-initial.png"))
        save("graph-initial-debug.json", graph.evaluate("({zoom:document.querySelector('#zoom').textContent, timeline:graphDebug.timeline, build:graphDebug.view.manifest?.build_id})"))
        if graph.request.get("http://127.0.0.1:8983/api/recordings").json().get("active"):
            graph.wait_for_function("!document.querySelector('#record-stop').disabled")
            graph.locator("#record-stop").click()
            graph.wait_for_function("graphDebug.timeline?.source === 'saved'")
            save("failed-attempt-recording-stop.json", graph.request.get("http://127.0.0.1:8983/api/recordings").json())
        graph.locator("#record-list").select_option("")
        graph.wait_for_function("!document.querySelector('#record-start').disabled")
        graph.locator("#record-start").click()
        graph.locator("#record-stop").wait_for(state="visible")
        pages = {}
        for actor in ("alice", "ben", "cara", "dan"):
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.goto("http://127.0.0.1:8982/")
            page.wait_for_load_state("networkidle")
            page.locator('[name="username"]').select_option(actor)
            page.locator('[name="password"]').fill("bands-8972-trial")
            page.get_by_role("button", name="登录文件柜").click()
            page.wait_for_load_state("networkidle")
            pages[actor] = page
        a, b, c, d = [pages[actor] for actor in ("alice", "ben", "cara", "dan")]
        a.locator('[name="file"]').set_input_files(str(fixture))
        a.locator('[name="reviewer_id"]').select_option("ben")
        a.get_by_role("button", name="上传并送审").click()
        a.wait_for_load_state("networkidle")
        card = a.locator("article").filter(has_text=fixture.name)
        card.wait_for()
        file_id = card.locator('a[href$="/download"]').get_attribute("href").split("/")[2]
        a.screenshot(path=str(OUT / "app-uploaded.png"), full_page=True)
        checks.append("alice uploads and assigns ben")
        b.reload()
        bcard = b.locator("article").filter(has_text=fixture.name)
        bcard.get_by_role("button", name="通过审核", exact=True).click()
        b.wait_for_load_state("networkidle")
        b.screenshot(path=str(OUT / "app-approved.png"), full_page=True)
        checks.append("assigned ben approves through actual form")
        c.reload()
        assert c.locator("article").filter(has_text=fixture.name).count() == 0
        a.reload()
        card = a.locator("article").filter(has_text=fixture.name)
        card.locator('[name="recipient_id"]').select_option("cara")
        card.get_by_role("button", name="定向分享").click()
        a.wait_for_load_state("networkidle")
        a.screenshot(path=str(OUT / "app-shared.png"), full_page=True)
        c.reload()
        recipient = c.locator("article").filter(has_text=fixture.name)
        assert "仅查看和下载" in recipient.inner_text()
        assert recipient.locator('form').count() == 0
        with c.expect_download() as event:
            recipient.get_by_role("link", name="下载文件 ↓").click()
        target = OUT / "downloaded-browser-file.txt"
        event.value.save_as(str(target))
        assert fixture.read_bytes() == target.read_bytes()
        c.screenshot(path=str(OUT / "app-recipient.png"), full_page=True)
        d.reload()
        assert d.locator("article").filter(has_text=fixture.name).count() == 0
        checks.extend(["cara cannot see the unshared approved file", "alice shares to cara", "cara downloads identical bytes and cannot forward", "dan sees no file"])
        result = matrix()
        graph.locator("#record-stop").click()
        graph.wait_for_function("graphDebug.timeline?.source === 'saved'")
        graph.wait_for_function("document.querySelector('#record-list').value.length > 0")
        recording_id = graph.locator("#record-list").input_value()
        recording = graph.request.get("http://127.0.0.1:8983/api/recordings/" + recording_id).json()
        assert recording.get("status") == "stopped" and recording.get("events") and not recording.get("gaps")
        view = graph.request.get("http://127.0.0.1:8983/api/view").json()
        save("actual-recording.json", recording)
        save("live-after-flow.json", view)
        graph.screenshot(path=str(OUT / "graph-recorded.png"))
        save("browser-flow.json", {"valid": True, "checks": checks, "file_id": file_id,
            "download_bytes": target.stat().st_size, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "recording_id": recording_id, "recording_events": len(recording.get("events", [])),
            "gaps": recording.get("gaps"), "errors": errors, "http_matrix": result["valid"]})
        assert not errors
        browser.close()

if __name__ == "__main__":
    try:
        main()
        print("Real browser workflow and threaded HTTP matrix passed")
    except BaseException:
        import time
        (OUT / ("browser-flow-failure-" + str(time.time_ns()) + ".txt")).write_text(traceback.format_exc(), encoding="utf-8")
        raise
