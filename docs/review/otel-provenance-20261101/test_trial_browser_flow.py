"""Review, share and download the actual browser-uploaded file; read its raw trace."""

from hashlib import sha256
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from test_trial_browser_upload import login

UPLOAD_ROOT = Path(__file__).resolve().parent / "independent-browser-01"
OUT = Path(__file__).resolve().parent / "independent-browser-02"
APP = "http://127.0.0.1:50294"
GRAPH = "http://127.0.0.1:53754/graph?lang=zh-CN"


def card(page, filename):
    return page.locator("article.file-row").filter(
        has=page.get_by_role("heading", name=filename, exact=True)
    )


def main():
    OUT.mkdir(exist_ok=True)
    if (OUT / "flow-result.json").exists():
        raise FileExistsError("Preserve the completed flow result")
    upload = json.loads((UPLOAD_ROOT / "upload-result.json").read_text(encoding="utf-8"))
    filename = upload["filename"]
    statuses, errors, checks = [], [], []
    with sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True, executable_path="C:/Users/Lvi_P/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe")
        try:
            def new_page():
                page = browser.new_page(viewport={"width": 1440, "height": 960}, accept_downloads=True)
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("response", lambda response: statuses.append({"url": response.url, "status": response.status}) if "/command/" in response.url else None)
                return page

            owner, admin, recipient = new_page(), new_page(), new_page()
            login(owner, "member1")
            own_card = card(owner, filename)
            detail = own_card.get_by_role("link", name="文件信息", exact=True).get_attribute("href")
            identity = detail.rsplit("/", 1)[1]
            download_url = APP + "/api/files/" + identity + "/download"
            login(recipient, "member2")
            denied = recipient.goto(download_url)
            assert denied.status == 403
            checks.append("Recipient download before review/shared activation returns actual HTTP 403")
            login(admin, "admin1")
            # The rendered review form is in the review panel, outside the file card.
            review_form = admin.locator('form[action="/command/review"]').filter(
                has=admin.locator(f'input[name="file_id"][value="{identity}"]')
            )
            review_form.get_by_role("button", name="通过", exact=True).click()
            expect(card(admin, filename)).to_contain_text("审核结果待投递", timeout=2500)
            admin.screenshot(path=str(OUT / "03-review-waiting.png"), full_page=True)
            expect(card(admin, filename)).to_contain_text("审核通过", timeout=15000)
            checks.append("Browser review enters notice wait and actual background delivery activates approval")
            owner.reload(wait_until="networkidle")
            own_card.get_by_role("combobox").select_option(label="Member Two")
            own_card.get_by_role("button", name="共享", exact=True).click()
            expect(own_card).to_contain_text("共享消息待投递", timeout=2500)
            owner.screenshot(path=str(OUT / "04-share-waiting.png"), full_page=True)
            denied = recipient.goto(download_url)
            assert denied.status == 403
            expect(own_card).to_contain_text("共享已生效", timeout=15000)
            checks.append("Browser sharing waits for committed notice; recipient is denied while waiting")
            recipient.goto(APP)
            recipient.wait_for_load_state("networkidle")
            recipient_card = card(recipient, filename)
            expect(recipient_card).to_be_visible()
            assert recipient_card.get_by_role("button", name="共享", exact=True).count() == 0
            with recipient.expect_download() as pending:
                recipient_card.get_by_role("link", name="下载", exact=True).click()
            downloaded = pending.value
            destination = OUT / "recipient-download.txt"
            downloaded.save_as(str(destination))
            assert destination.read_bytes() == (UPLOAD_ROOT / filename).read_bytes()
            recipient.screenshot(path=str(OUT / "05-recipient-download.png"), full_page=True)
            checks.append("Recipient clicks the actual download link, receives byte-identical content and has no re-share button")
            graph = new_page()
            graph.goto(GRAPH)
            graph.wait_for_function("typeof graphDebug !== 'undefined' && graphDebug.view?.events")
            observed = graph.evaluate("""file => {
                const all=graphDebug.view.events;
                const relevant=e=>e.inputs?.file_id===file||e.outputs?.file_id===file||e.provenance?.objects?.some(o=>o.type==='File'&&o.id===file);
                const traces=new Set(all.filter(relevant).map(e=>e.trace?.trace_id).filter(Boolean));
                const events=all.filter(e=>traces.has(e.trace?.trace_id));
                const api=[...graphDebug.graph.all.values()].filter(n=>n.layer==='api').map(n=>({id:n.id,label:n.label}));
                return {events,api_nodes:api,api_events:events.filter(e=>api.some(n=>n.id===e.node))};
            }""", identity)
            (OUT / "flow-events.json").write_text(json.dumps(observed, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            result = {"passed": not errors, "file_id": identity, "filename": filename,
                      "checks": checks, "download_sha256": sha256(destination.read_bytes()).hexdigest(),
                      "command_responses": statuses, "page_errors": errors,
                      "related_raw_events": len(observed["events"]),
                      "related_api_events": len(observed["api_events"]),
                      "scope": "Independent real browser flow and read-only graph inspection; no project-source edits and no recording-control changes."}
            (OUT / "flow-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            assert not errors
            print(json.dumps(result, ensure_ascii=False))
        except BaseException:
            for index, page in enumerate(browser.contexts):
                for offset, opened in enumerate(page.pages):
                    opened.screenshot(path=str(OUT / f"failure-{index}-{offset}.png"), full_page=True)
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    main()
