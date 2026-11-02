"""Real file-input upload; inspect the actual review form before acting on it."""

from hashlib import sha256
import json
from pathlib import Path
import time
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "independent-browser-01"


def login(page, username):
    page.goto("http://127.0.0.1:50294/")
    page.wait_for_load_state("networkidle")
    page.get_by_label("账号", exact=True).fill(username)
    page.get_by_label("密码", exact=True).fill("Trial2026!")
    page.get_by_role("button", name="登录", exact=True).click()
    page.wait_for_load_state("networkidle")


def controls(page):
    return page.locator("form").evaluate_all("""forms => forms.map(form => ({
        action: form.getAttribute('action'), text: form.innerText,
        controls: [...form.elements].map(el => ({tag: el.tagName, name: el.name,
            type: el.type, labels: [...(el.labels || [])].map(label => label.innerText)}))
    }))""")


def main():
    result_path = OUT / "upload-result.json"
    if result_path.exists():
        raise FileExistsError("Preserve the actual upload result")
    filename = f"independent-browser-{int(time.time())}.txt"
    payload = b"Actual browser file input, review, sharing and download.\n"
    fixture = OUT / filename
    fixture.write_bytes(payload)
    errors = []
    with sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True, executable_path="C:/Users/Lvi_P/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe")
        try:
            owner = browser.new_page(viewport={"width": 1440, "height": 960})
            owner.on("pageerror", lambda error: errors.append(str(error)))
            login(owner, "member1")
            owner.locator('input[type="file"]').set_input_files(str(fixture))
            selected = owner.locator('input[type="file"]').evaluate("el => el.files[0].name")
            assert selected == filename
            owner.get_by_role("button", name="上传并提交审核", exact=True).click()
            owner.wait_for_load_state("networkidle")
            owner.get_by_role("heading", name=filename, exact=True).wait_for()
            owner.screenshot(path=str(OUT / "01-file-uploaded.png"), full_page=True)
            containers = owner.get_by_role("heading", name=filename, exact=True).evaluate("el => {const rows=[]; for(let p=el;p&&rows.length<4;p=p.parentElement) rows.push({tag:p.tagName,cls:p.className});return rows}")
            owner_links = owner.get_by_role("link", name="文件信息", exact=True).evaluate_all("links => links.map(el => ({href:el.getAttribute('href'),name:el.parentElement.innerText}))")
            admin = browser.new_page(viewport={"width": 1440, "height": 960})
            login(admin, "admin1")
            admin.screenshot(path=str(OUT / "02-review-form.png"), full_page=True)
            result = {"passed": True, "filename": filename, "payload_sha256": sha256(payload).hexdigest(),
                      "file_input_selected": selected, "owner_containers": containers,
                      "owner_links": owner_links, "admin_forms": controls(admin),
                      "page_errors": errors, "scope": "Actual rendered file input and page submit; no API upload substitute or project-source edit."}
            result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
            assert not errors
            print(json.dumps(result, ensure_ascii=False))
        finally:
            browser.close()


if __name__ == "__main__":
    main()
