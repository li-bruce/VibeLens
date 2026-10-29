"""Record an actual stale-page download under the supplied controlled fault."""

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "red-browser"
URL, GRAPH = "http://127.0.0.1:8852", "http://127.0.0.1:8853"


def main():
    OUT.mkdir(exist_ok=True)
    steps, screenshots, errors = [], [], []

    def step(name, details=None):
        steps.append({"order": len(steps) + 1, "name": name, "time_unix": time.time(), "details": details})
        (OUT / "steps.json").write_text(json.dumps(steps, ensure_ascii=False, indent=2), encoding="utf-8")

    def screenshot(page, name):
        path = OUT / (name + ".png")
        page.screenshot(path=str(path), full_page=True)
        screenshots.append({"file": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

    def facts(file_id):
        with closing(sqlite3.connect(ROOT / "data/sharing.sqlite3")) as connection:
            row = connection.execute("SELECT owner_id,state,revision,sha256 FROM files WHERE id=?", (file_id,)).fetchone()
            grants = connection.execute("SELECT recipient_id FROM shares WHERE file_id=? ORDER BY recipient_id", (file_id,)).fetchall()
        return {"owner_id": row[0], "state": row[1], "revision": row[2], "sha256": row[3], "recipients": [item[0] for item in grants]}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        contexts = [browser.new_context(viewport={"width": 1440, "height": 1080}, accept_downloads=True) for _ in range(3)]
        owner, recipient, graph = [context.new_page() for context in contexts]
        for page in [owner, recipient, graph]:
            page.on("pageerror", lambda value: errors.append(str(value)))
        graph.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        health = graph.request.get(GRAPH + "/api/bo/health").json()
        assert health["binding"]["status"] == "current"
        start = graph.request.post(GRAPH + "/api/recordings/start", data={"label": "Controlled red diagnosis"})
        assert start.ok, start.text()
        step("recording_started", {"build_id": health["build_id"]})

        def login(page, name):
            page.goto(URL + "/login")
            page.locator("#username").select_option(name)
            page.locator("#password").fill("file-demo-2026")
            page.get_by_role("button", name="登录，进入文件列表").click()
            page.get_by_role("heading", name="文件，在这里交接。").wait_for()

        login(owner, "linzhou")
        filename = f"controlled-red-{time.time_ns()}.txt"
        content = b"Controlled red stale-page fixture.\n"
        owner.locator("#file").set_input_files({"name": filename, "mimeType": "text/plain", "buffer": content})
        owner.get_by_role("button", name="上传文件 ↑").click()
        own_row = owner.get_by_role("row").filter(has=owner.get_by_text(filename, exact=True))
        download_url = own_row.get_by_role("link", name="下载 ↓").get_attribute("href")
        file_id = download_url.split("/")[2]
        own_row.get_by_role("combobox").select_option("xuning")
        own_row.get_by_role("button", name="共享", exact=True).click()
        owner.get_by_role("status").wait_for()
        login(recipient, "xuning")
        stale_row = recipient.get_by_role("row").filter(has=recipient.get_by_text(filename, exact=True))
        with recipient.expect_download() as downloaded:
            stale_row.get_by_role("link", name="下载文件 ↓").click()
        downloaded.value.save_as(str(OUT / "recipient-before.txt"))
        assert (OUT / "recipient-before.txt").read_bytes() == content
        screenshot(recipient, "01-original-recipient-page")
        stale_hash = hashlib.sha256(recipient.content().encode()).hexdigest()
        stale_page_url = recipient.url
        before = facts(file_id)
        step("shared_file_downloaded_before_revoke", before)
        own_row.get_by_role("button", name="取消共享给许宁", exact=True).click()
        owner.get_by_role("status").wait_for()
        assert "共享已取消" in owner.get_by_role("status").inner_text()
        screenshot(owner, "02-success-notice-but-grant-remains")
        after = facts(file_id)
        assert recipient.url == stale_page_url and hashlib.sha256(recipient.content().encode()).hexdigest() == stale_hash
        with recipient.expect_response(lambda response: response.url == URL + download_url) as response:
            with recipient.expect_download() as downloaded:
                stale_row.get_by_role("link", name="下载文件 ↓").click()
        downloaded.value.save_as(str(OUT / "recipient-after.txt"))
        assert response.value.status == 200 and (OUT / "recipient-after.txt").read_bytes() == content
        screenshot(recipient, "03-stale-page-still-downloads")
        step("controlled_failure_reproduced", {"expected": 403, "actual": response.value.status, "page_unchanged": True, "database_after": after})
        with owner.expect_download() as downloaded:
            own_row.get_by_role("link", name="下载 ↓").click()
        downloaded.value.save_as(str(OUT / "owner-after.txt"))
        assert (OUT / "owner-after.txt").read_bytes() == content
        deadline = time.monotonic() + 120
        while True:
            view = graph.request.get(GRAPH + "/api/view").json()
            events = [event for event in view["events"] if event.get("node") == "revoke" and event.get("entity") == file_id]
            owner_seen = any(event.get("node") == "download" and event.get("entity") == file_id and event.get("inputs", {}).get("actor") == "linzhou" for event in view["events"])
            if events and owner_seen:
                break
            assert time.monotonic() < deadline, "controlled_red_runtime_capture_timeout"
            time.sleep(0.15)
        frames = [frame for frame in view["runtime_frames"]["frames"] if frame.get("authority", {}).get("entity") == file_id]
        assert [frame["authority"]["state"] for frame in frames] == ["private", "shared", "shared"]
        assert events[-1]["outputs"]["removed"] is False and events[-1]["outputs"]["grant_count"] == 1
        assert view["health"]["errors"] == view["health"]["dropped"] == 0
        stopped = graph.request.post(GRAPH + "/api/recordings/stop", data={})
        assert stopped.ok
        recording = stopped.json()
        assert not recording["gaps"]
        (OUT / "recording-stop.json").write_text(json.dumps(recording, ensure_ascii=False, indent=2), encoding="utf-8")
        replay = contexts[2].new_page()
        replay.set_viewport_size({"width": 1920, "height": 1440})
        replay.on("pageerror", lambda value: errors.append(str(value)))
        replay.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        replay.goto(GRAPH + "/graph")
        replay.wait_for_function("build => !document.querySelector('#connection').textContent.includes('暂时无法连接') && document.querySelector('#binding').textContent.includes(build)", arg=health["build_id"][:8], timeout=75000)
        replay.locator(f'#record-list option[value="{recording["id"]}"]').wait_for(state="attached", timeout=75000)
        replay.locator("#record-list").select_option(recording["id"])
        replay.locator("#replay").wait_for(state="visible")
        replay.locator("#replay-events option").filter(has_text="Revoke recipient access").first.wait_for(state="attached", timeout=75000)
        options = replay.locator("#replay-events option").evaluate_all("items => items.map(item => ({value:item.value,label:item.textContent}))")
        selected = next(item for item in options if "Revoke recipient access" in item["label"])
        replay.locator("#replay-events").select_option(selected["value"])
        screenshot(replay, "04-actual-red-revoke-replay")
        assert not errors, errors
        step("actual_failure_recording_replayed", {"recording_id": recording["id"], "events": recording["events"]})
        report = {"controlled_fault": True, "reproduction_confirmed": True, "business_expectation_passed": False,
                  "build_id": health["build_id"], "file_id": file_id, "expected_stale_download_status": 403,
                  "actual_stale_download_status": response.value.status, "before": before, "after": after,
                  "actual_states": ["private", "shared", "shared"], "recording": recording, "screenshots": screenshots, "steps": steps, "console_or_page_errors": errors}
        (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"controlled_failure_reproduced": True, "stale_download_status": 200, "recording_id": recording["id"], "events": recording["events"]}))
        browser.close()


if __name__ == "__main__":
    main()
