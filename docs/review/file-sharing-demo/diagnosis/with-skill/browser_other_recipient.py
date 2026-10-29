"""Verify recipient isolation and re-sharing using real UI actions and graph facts."""

from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "green-other-recipient"
URL, GRAPH = "http://127.0.0.1:8852", "http://127.0.0.1:8853"


def main():
    OUT.mkdir(exist_ok=True)
    steps, screenshots, errors = [], [], []

    def step(name, details=None):
        steps.append({"name": name, "time_unix": time.time(), "details": details})
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
        contexts = [browser.new_context(viewport={"width": 1440, "height": 1080}, accept_downloads=True) for _ in range(4)]
        owner, removed, retained, graph = [context.new_page() for context in contexts]
        for page in [owner, removed, retained, graph]:
            page.on("pageerror", lambda error: errors.append(str(error)))
        graph.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        health = graph.request.get(GRAPH + "/api/bo/health").json()
        assert health["binding"]["status"] == "current"
        started = graph.request.post(GRAPH + "/api/recordings/start", data={"label": "Recipient isolation and re-sharing"})
        assert started.ok, started.text()

        def login(page, username):
            page.goto(URL + "/login")
            page.locator("#username").select_option(username)
            page.locator("#password").fill("file-demo-2026")
            page.get_by_role("button", name="登录，进入文件列表").click()
            page.get_by_role("heading", name="文件，在这里交接。").wait_for()

        login(owner, "linzhou")
        filename = f"recipient-isolation-{time.time_ns()}.txt"
        content = b"Other recipients and re-sharing remain valid.\n"
        owner.locator("#file").set_input_files({"name": filename, "mimeType": "text/plain", "buffer": content})
        owner.get_by_role("button", name="上传文件 ↑").click()
        owned_row = owner.get_by_role("row").filter(has=owner.get_by_text(filename, exact=True))
        href = owned_row.get_by_role("link", name="下载 ↓").get_attribute("href")
        file_id = href.split("/")[2]
        for recipient in ["xuning", "zhoulan"]:
            owned_row.get_by_role("combobox").select_option(recipient)
            owned_row.get_by_role("button", name="共享", exact=True).click()
            owner.get_by_role("status").wait_for()
        login(removed, "xuning")
        login(retained, "zhoulan")

        def download(page, label, output):
            row = page.get_by_role("row").filter(has=page.get_by_text(filename, exact=True))
            with page.expect_download() as result:
                row.get_by_role("link", name=label).click()
            result.value.save_as(str(OUT / output))
            assert (OUT / output).read_bytes() == content

        download(removed, "下载文件 ↓", "before-xuning.txt")
        screenshot(removed, "01-xuning-before-revoke")
        old_hash = hashlib.sha256(removed.content().encode()).hexdigest()
        before = facts(file_id)
        assert before["recipients"] == ["xuning", "zhoulan"]
        owned_row.get_by_role("button", name="取消共享给许宁", exact=True).click()
        owner.get_by_role("status").wait_for()
        after = facts(file_id)
        assert after["recipients"] == ["zhoulan"] and after["state"] == "shared"
        assert hashlib.sha256(removed.content().encode()).hexdigest() == old_hash
        old_row = removed.get_by_role("row").filter(has=removed.get_by_text(filename, exact=True))
        with removed.expect_response(lambda response: response.url == URL + href) as response:
            old_row.get_by_role("link", name="下载文件 ↓").click()
        assert response.value.status == 403
        removed.get_by_role("heading", name="你没有操作这个文件的权限。", exact=True).wait_for()
        screenshot(removed, "02-only-xuning-denied")
        download(retained, "下载文件 ↓", "zhoulan-retained.txt")
        download(owner, "下载 ↓", "owner-retained.txt")
        screenshot(owner, "03-zhoulan-grant-retained")
        step("revoke_only_selected_recipient", {"before": before, "after": after, "xuning_status": 403, "zhoulan_download_matches": True, "owner_download_matches": True})
        owned_row.get_by_role("combobox").select_option("xuning")
        owned_row.get_by_role("button", name="共享", exact=True).click()
        owner.get_by_role("status").wait_for()
        removed.goto(URL + "/")
        download(removed, "下载文件 ↓", "xuning-reshared.txt")
        reshared = facts(file_id)
        assert reshared["recipients"] == ["xuning", "zhoulan"]
        screenshot(removed, "04-xuning-download-restored")
        step("reshare_restores_recipient_access", {"after": reshared, "download_matches": True})
        deadline = time.monotonic() + 120
        while True:
            view = graph.request.get(GRAPH + "/api/view").json()
            final_shares = [event for event in view["events"] if event.get("node") == "share" and event.get("entity") == file_id and event.get("revision") == reshared["revision"]]
            final_share = final_shares[-1] if final_shares else None
            last_download = final_share and any(event.get("node") == "download" and event.get("entity") == file_id and event.get("inputs", {}).get("actor") == "xuning" and event.get("seq", 0) > final_share["seq"] for event in view["events"])
            fresh_read = any(event.get("node") == "policy:read_allowed" and event.get("outputs", {}).get("value") is True and event.get("inputs", {}).get("bo_basis", "").startswith(file_id + ":" + str(reshared["revision"]) + ":") for event in view["events"])
            if last_download and final_share and fresh_read:
                break
            assert time.monotonic() < deadline, "recipient_isolation_runtime_timeout"
            time.sleep(0.15)
        revoke = next(event for event in view["events"] if event.get("node") == "revoke" and event.get("entity") == file_id)
        assert revoke["outputs"]["removed"] is True and revoke["outputs"]["grant_count"] == 1 and revoke["outputs"]["state"] == "shared"
        policy_decisions = []
        for decision in view["events"]:
            basis = decision.get("inputs", {}).get("bo_basis", "")
            if decision.get("node") != "policy:read_allowed" or not basis.startswith(file_id + ":"):
                continue
            check_id = decision["inputs"]["bo_check"]
            actor = next(event["outputs"]["value"] for event in view["events"] if event.get("node") == "policy:fact_actor" and event.get("inputs", {}).get("bo_check") == check_id)
            policy_decisions.append({"actor": actor, "revision": int(basis.split(":")[1]), "allowed": decision["outputs"]["value"], "check_id": check_id, "event_id": decision["id"]})
        witnessed = {(item["actor"], item["revision"], item["allowed"]) for item in policy_decisions}
        assert {("xuning", after["revision"], False), ("zhoulan", after["revision"], True), ("linzhou", after["revision"], True), ("xuning", reshared["revision"], True)} <= witnessed
        assert view["health"]["errors"] == view["health"]["dropped"] == 0
        stopped = graph.request.post(GRAPH + "/api/recordings/stop", data={})
        assert stopped.ok
        recording = stopped.json()
        assert not recording["gaps"]
        (OUT / "recording-stop.json").write_text(json.dumps(recording, ensure_ascii=False, indent=2), encoding="utf-8")
        replay = contexts[3].new_page()
        replay.set_viewport_size({"width": 1920, "height": 1440})
        replay.on("pageerror", lambda error: errors.append(str(error)))
        replay.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
        replay.goto(GRAPH + "/graph")
        replay.wait_for_function("build => !document.querySelector('#connection').textContent.includes('暂时无法连接') && document.querySelector('#binding').textContent.includes(build)", arg=health["build_id"][:8], timeout=75000)
        replay.locator(f'#record-list option[value="{recording["id"]}"]').wait_for(state="attached", timeout=75000)
        replay.locator("#record-list").select_option(recording["id"])
        replay.locator("#replay-events option").filter(has_text="Revoke recipient access").first.wait_for(state="attached", timeout=75000)
        selected = replay.locator("#replay-events option").filter(has_text="Revoke recipient access").first.get_attribute("value")
        replay.locator("#replay-events").select_option(selected)
        screenshot(replay, "05-legitimate-shared-to-shared-replay")
        assert not errors, errors
        report = {"valid": True, "build_id": health["build_id"], "file_id": file_id, "before": before, "after_revoke": after, "after_reshare": reshared,
                  "checks": {"selected_recipient_stale_download_denied": True, "other_recipient_retained": True, "owner_retained": True, "reshare_restores_download": True, "shared_state_matches_remaining_grant": True, "real_recording_replayed": True},
                  "recording": recording, "policy_decisions": policy_decisions, "steps": steps, "screenshots": screenshots, "console_or_page_errors": errors}
        (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"valid": True, "other_recipient_retained": True, "reshare_restored": True, "recording_events": recording["events"]}))
        browser.close()


if __name__ == "__main__":
    main()
