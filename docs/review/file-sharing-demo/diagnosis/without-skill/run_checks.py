"""Preserve controlled-fault evidence without changing the existing tests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import traceback
import zipfile
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from app import create_server
from browser_check import run_flow, sign_in
from browser_check_v2 import revocation_flow
from playwright.sync_api import expect, sync_playwright

SAMPLE_NAME = "controlled-revocation.txt"
SAMPLE_BYTES = b"Controlled diagnosis sample: authorization follows the selected recipient.\n"
EXECUTABLE = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def stamp():
    return datetime.now(timezone(timedelta(hours=8))).isoformat()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def source_files():
    return sorted([ROOT / "app.py", ROOT / "README.md", *list((ROOT / "static").glob("*")), *list((ROOT / "tests").glob("*.py"))])


def capture():
    before = EVIDENCE / "before"
    before.mkdir(exist_ok=False)
    manifest = {str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in source_files() if path.is_file()}
    with zipfile.ZipFile(before / "faulty-source.zip", "x", zipfile.ZIP_DEFLATED) as archive:
        for name in manifest:
            archive.write(ROOT / name, name)
    shutil.copyfile(ROOT / "app.py", before / "app.py")
    shutil.copyfile(ROOT / "review" / "diagnosis-red-tests.json", before / "provided-red-tests.json")
    shutil.copyfile(ROOT / "review" / "baseline-tests.log", before / "provided-baseline-tests.log")
    save(before / "manifest.json", {"timestamp": stamp(), "context": "user-supplied controlled fault; not a naturally discovered defect", "sha256": manifest})
    print(json.dumps({"captured_files": len(manifest), "directory": str(before)}))


def http_tests(phase):
    output = EVIDENCE / phase
    output.mkdir(exist_ok=True)
    process = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                             env={**os.environ, "PYTHONUTF8": "1"})
    result = {"timestamp": stamp(), "command": "python -m unittest discover -s tests -p test_*.py -v",
              "exit_code": process.returncode, "stdout": process.stdout, "stderr": process.stderr}
    save(output / "http-tests.json", result)
    (output / "http-tests.log").write_text(process.stdout + process.stderr, encoding="utf-8")
    print(json.dumps({"phase": phase, "http_exit_code": process.returncode, "summary": process.stderr.splitlines()[-5:]}))
    return process.returncode


def snapshot(database, file_id):
    with closing(sqlite3.connect(database)) as db:
        return {"file": dict(zip(("id", "owner_id", "name", "size", "storage_key"),
                                db.execute("SELECT id, owner_id, name, size, storage_key FROM files WHERE id = ?", (file_id,)).fetchone())),
                "shares": [dict(zip(("file_id", "recipient_id"), row)) for row in db.execute(
                    "SELECT file_id, recipient_id FROM shares WHERE file_id = ? ORDER BY recipient_id", (file_id,))]}


def witness(base_url, database, temporary_root, directory, result):
    images = directory / "screenshots"
    downloads = directory / "downloads"
    images.mkdir(parents=True, exist_ok=True)
    downloads.mkdir(exist_ok=True)
    result.update({"checks": [], "browser_errors": []})

    def check(name, actual, expected):
        result["checks"].append({"name": name, "actual": actual, "expected": expected, "passed": actual == expected})

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=EXECUTABLE, headless=True,
                                            downloads_path=str(temporary_root / "downloads"))
        result["browser"] = browser.version
        contexts = []

        def page_for(username):
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
            contexts.append(context)
            page = context.new_page()
            page.on("pageerror", lambda error: result["browser_errors"].append(str(error)))
            sign_in(page, base_url, username)
            return page

        def downloaded(page, row, filename):
            with page.expect_download() as event:
                row.get_by_role("button", name=f"Download {SAMPLE_NAME}", exact=True).click()
            target = downloads / filename
            event.value.save_as(target)
            check(f"Bytes in {filename}", target.read_bytes().hex(), SAMPLE_BYTES.hex())
            return hashlib.sha256(target.read_bytes()).hexdigest()

        try:
            owner = page_for("linzhou")
            owner.locator("#file-input").set_input_files({"name": SAMPLE_NAME, "mimeType": "text/plain", "buffer": SAMPLE_BYTES})
            with owner.expect_response(lambda response: response.url.endswith("/api/files") and response.request.method == "POST") as uploaded:
                owner.get_by_role("button", name="Upload file").click()
            check("Upload status", uploaded.value.status, 201)
            file_id = uploaded.value.json()["id"]
            result["file_id"] = file_id
            owner_row = owner.locator(f'tr[data-file-id="{file_id}"]')
            for name in ("许宁", "周岚"):
                owner_row.get_by_role("combobox").select_option(label=name)
                with owner.expect_response(lambda response: response.url.endswith(f"/api/files/{file_id}/shares")) as shared:
                    owner_row.get_by_role("button", name="Share", exact=True).click()
                check(f"Share with {name}", shared.value.status, 200)
                expect(owner_row).to_contain_text(f"{name} · View & download")

            recipient = page_for("xuning")
            recipient.get_by_role("tab", name="Shared with me", exact=False).click()
            recipient_row = recipient.locator(f'tr[data-file-id="{file_id}"]')
            expect(recipient_row).to_be_visible()
            result["before_download_sha256"] = downloaded(recipient, recipient_row, "recipient-before-cancel.txt")
            other = page_for("zhoulan")
            other.get_by_role("tab", name="Shared with me", exact=False).click()
            other_row = other.locator(f'tr[data-file-id="{file_id}"]')
            expect(other_row).to_be_visible()
            owner.screenshot(path=str(images / "owner-before-cancel.png"), full_page=True)
            recipient.screenshot(path=str(images / "recipient-before-cancel.png"), full_page=True)
            result["database_before_cancel"] = snapshot(database, file_id)

            original_document = recipient.evaluate("performance.timeOrigin")
            requests = []
            events = []
            recipient.on("request", lambda request: requests.append({"method": request.method, "url": request.url}))
            recipient.on("download", lambda event: events.append(event))
            with owner.expect_response(lambda response: response.url.endswith(f"/api/files/{file_id}/revoke")) as canceled:
                owner_row.get_by_role("button", name=f"Cancel sharing with 许宁 for {SAMPLE_NAME}", exact=True).click()
            result["cancel_response"] = {"status": canceled.value.status, "body": canceled.value.json()}
            check("Cancel response status", canceled.value.status, 200)
            expect(owner.locator("#notice")).to_contain_text("Sharing with 许宁 was canceled.")
            result["owner_success_message"] = owner.locator("#notice").inner_text()
            result["database_after_cancel"] = snapshot(database, file_id)
            owner.screenshot(path=str(images / "owner-cancel-result.png"), full_page=True)
            check("Recipient document is unchanged during cancellation", recipient.evaluate("performance.timeOrigin"), original_document)
            check("Recipient makes no requests during cancellation", list(requests), [])
            check("Old file row remains visible", recipient_row.is_visible(), True)
            download_url = f"{base_url}/api/files/{file_id}/download"
            with recipient.expect_response(lambda response: response.url == download_url) as stale:
                recipient_row.get_by_role("button", name=f"Download {SAMPLE_NAME}", exact=True).click()
            stale_status = stale.value.status
            message = "You do not have access to this file." if stale_status == 403 else f"Downloaded {SAMPLE_NAME}"
            expect(recipient.locator("#notice")).to_have_text(message)
            recipient.screenshot(path=str(images / "recipient-stale-download-result.png"), full_page=True)
            for index, event in enumerate(events):
                event.save_as(downloads / f"unexpected-after-cancel-{index}.txt")
            check("Stale-page download must be rejected", stale_status, 403)
            check("Stale-page download must not create a download event", len(events), 0)
            check("Recipient still uses the original document", recipient.evaluate("performance.timeOrigin"), original_document)
            check("Only the download request occurs before the stale-page result", list(requests), [{"method": "GET", "url": download_url}])
            result["stale_page"] = {"http_status": stale_status, "same_document": recipient.evaluate("performance.timeOrigin") == original_document,
                                    "requests_through_download": list(requests), "download_events": len(events), "message": message}
            rows_after = result["database_after_cancel"]["shares"]
            check("Only Xu Ning's grant is removed", rows_after, [{"file_id": file_id, "recipient_id": 3}])

            result["owner_after_cancel_sha256"] = downloaded(owner, owner_row, "owner-after-cancel.txt")
            result["other_recipient_sha256"] = downloaded(other, other_row, "other-recipient-after-cancel.txt")
            owner.screenshot(path=str(images / "owner-still-downloads.png"), full_page=True)
            other.screenshot(path=str(images / "other-recipient-still-downloads.png"), full_page=True)
            with recipient.expect_response(lambda response: response.url.endswith("/api/files") and response.request.method == "GET"):
                recipient.get_by_role("button", name="Refresh").click()
            expected_visible = any(row["recipient_id"] == 2 for row in rows_after)
            if expected_visible:
                expect(recipient_row).to_be_visible()
            else:
                expect(recipient_row).to_have_count(0)
            check("Canceled file disappears after refresh", recipient_row.count(), 0)

            options = owner_row.get_by_role("combobox").all_text_contents() if owner_row.get_by_role("combobox").count() else []
            if any("许宁" in option for option in options):
                owner_row.get_by_role("combobox").select_option(label="许宁")
                with owner.expect_response(lambda response: response.url.endswith(f"/api/files/{file_id}/shares")) as regranted:
                    owner_row.get_by_role("button", name="Share", exact=True).click()
                check("Reshare through original UI", regranted.value.status, 200)
                result["reshare_method"] = "owner UI"
            else:
                session = owner.context.request.get(f"{base_url}/api/session").json()
                regranted = owner.context.request.post(f"{base_url}/api/files/{file_id}/shares",
                    headers={"X-CSRF-Token": session["csrf_token"]}, data={"recipient_id": 2})
                check("Original share API still responds", regranted.status, 200)
                result["reshare_method"] = "API duplicate grant; faulty cancellation left recipient already authorized"
            recipient.get_by_role("button", name="Refresh").click()
            expect(recipient_row).to_be_visible()
            result["reshared_download_sha256"] = downloaded(recipient, recipient_row, "recipient-after-reshare.txt")
            recipient.screenshot(path=str(images / "recipient-after-reshare.png"), full_page=True)
            check("No JavaScript exceptions", result["browser_errors"], [])
            result["passed"] = all(check["passed"] for check in result["checks"])
            assert result["passed"], "Independent cancellation expectations failed; see recorded actual and expected values."
        finally:
            for context in contexts:
                context.close()
            browser.close()


def browser_checks(phase, port):
    directory = EVIDENCE / phase
    directory.mkdir(exist_ok=True)
    temporary_root = directory / "browser-runtime"
    temporary_root.mkdir(exist_ok=False)
    os.environ["TEMP"] = str(temporary_root)
    os.environ["TMP"] = str(temporary_root)
    database_dir = directory / "browser-data"
    server = create_server(database_dir, port=port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    result = {"phase": phase, "context": "controlled fault diagnosis", "timestamp": stamp(), "base_url": base_url,
              "app_sha256": hashlib.sha256((ROOT / "app.py").read_bytes()).hexdigest(), "headless": True}
    try:
        witness(base_url, server.database, temporary_root, directory / "witness", result)
        if phase == "green":
            result["original_regression"] = {"status": "running"}
            run_flow(base_url, EXECUTABLE, temporary_root, directory / "original-regression", result["original_regression"])
            result["original_revocation"] = {"status": "running"}
            revocation_flow(base_url, EXECUTABLE, temporary_root, directory / "original-revocation", result["original_revocation"])
        result["status"] = "passed"
        return 0
    except Exception as error:
        result.update({"status": "failed", "error": str(error), "traceback": traceback.format_exc()})
        return 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        result["finished_at"] = stamp()
        result["server_stopped"] = True
        save(directory / "browser-result.json", result)
        print(json.dumps({"phase": phase, "browser_status": result["status"], "checks": len(result.get("checks", [])),
                          "failed": [item["name"] for item in result.get("checks", []) if not item["passed"]]}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("capture", "http", "browser"))
    parser.add_argument("--phase", choices=("red", "green"))
    parser.add_argument("--port", type=int, default=8854)
    args = parser.parse_args()
    if args.action == "capture":
        capture()
        return
    if args.phase is None:
        parser.error("Select a phase for HTTP or browser checks.")
    sys.exit(http_tests(args.phase) if args.action == "http" else browser_checks(args.phase, args.port))


if __name__ == "__main__":
    main()
