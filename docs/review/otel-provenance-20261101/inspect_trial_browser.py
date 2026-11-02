"""Read actual rendered controls in a separate browser without changing trial source."""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / "independent-browser-01"


def main():
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as driver:
        browser = driver.chromium.launch(
            headless=True,
            executable_path="C:/Users/Lvi_P/AppData/Local/ms-playwright/chromium-1234/chrome-win64/chrome.exe",
        )
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            page.goto("http://127.0.0.1:50294/")
            page.wait_for_load_state("networkidle")
            result = {
                "title": page.title(),
                "forms": page.locator("form").evaluate_all(
                    """forms => forms.map(form => ({
                        action: form.getAttribute('action'), text: form.innerText,
                        controls: [...form.elements].map(el => ({
                            tag: el.tagName, name: el.name, type: el.type, id: el.id,
                            labels: [...(el.labels || [])].map(label => label.innerText)
                        }))
                    }))"""
                ),
                "buttons": page.get_by_role("button").all_text_contents(),
            }
            page.screenshot(path=str(OUT / "00-login.png"), full_page=True)
            (OUT / "controls.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            print(json.dumps(result, ensure_ascii=False))
        finally:
            browser.close()


if __name__ == "__main__":
    main()
