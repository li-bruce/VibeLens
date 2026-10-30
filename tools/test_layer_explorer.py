"""Verify bilingual layer explanations, WebGL selection, orbit and mobile layout."""

import argparse
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading

ROOT = Path(__file__).resolve().parents[1]
LAYER_ORDER = [
    "business",
    "state",
    "rules",
    "api",
    "execution",
    "operations",
    "project",
    "code",
    "data",
]


def main():
    from functools import partial
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", required=True)
    parser.add_argument("--out", default=".validation/layer-explorer")
    args = parser.parse_args()
    output = (ROOT / args.out).resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "temp").mkdir(exist_ok=True)
    os.environ["TMP"] = os.environ["TEMP"] = str(output / "temp")
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=ROOT / "docs/site")
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    checks, errors = [], []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True, executable_path=args.browser, args=["--enable-unsafe-swiftshader"]
            )
            page = browser.new_page(viewport={"width": 1500, "height": 1050})
            page.on("pageerror", lambda error: errors.append(str(error)))
            for language in ["en", "zh-CN"]:
                page.goto(
                    f"http://127.0.0.1:{server.server_port}/index.html?lang={language}#explore"
                )
                host = page.locator("#layer-explorer")
                host.scroll_into_view_if_needed()
                page.wait_for_function(
                    "document.querySelector('#layer-explorer').dataset.webgl === 'ready'"
                )
                tabs = host.get_by_role("tab")
                assert tabs.count() == 9
                order = tabs.evaluate_all("tabs => tabs.map(tab => tab.dataset.layer)")
                assert order == LAYER_ORDER, order
                descriptions = []
                for index in range(9):
                    tabs.nth(index).click()
                    assert tabs.nth(index).get_attribute("aria-selected") == "true"
                    descriptions.append(host.locator("h3").inner_text())
                    assert host.locator("[data-layer-body]").inner_text()
                assert len(set(descriptions)) == 9
                tabs.nth(0).click()
                tabs.nth(0).press("End")
                assert tabs.nth(8).get_attribute("aria-selected") == "true"
                canvas = host.locator("canvas")
                before = canvas.screenshot()
                bounds = canvas.bounding_box()
                page.mouse.move(
                    bounds["x"] + bounds["width"] * 0.55, bounds["y"] + bounds["height"] * 0.45
                )
                page.mouse.down()
                page.mouse.move(
                    bounds["x"] + bounds["width"] * 0.78,
                    bounds["y"] + bounds["height"] * 0.30,
                    steps=16,
                )
                page.mouse.up()
                page.wait_for_timeout(300)
                assert (
                    hashlib.sha256(before).digest() != hashlib.sha256(canvas.screenshot()).digest()
                )
                host.locator("[data-layer-reset]").click()
                tabs.nth(2).click()
                page.wait_for_timeout(300)
                page.screenshot(path=str(output / f"layers-{language}.png"))
                page.set_viewport_size({"width": 390, "height": 844})
                host.scroll_into_view_if_needed()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
                page.screenshot(path=str(output / f"mobile-{language}.png"))
                page.emulate_media(reduced_motion="reduce")
                tabs.nth(1).click()
                assert tabs.nth(1).get_attribute("aria-selected") == "true"
                page.emulate_media(reduced_motion="no-preference")
                page.set_viewport_size({"width": 1500, "height": 1050})
                checks.append(
                    {
                        "locale": language,
                        "layers": 9,
                        "order": order,
                        "keyboard": True,
                        "real_webgl_orbit": True,
                        "mobile": True,
                        "reduced_motion": True,
                    }
                )
            browser.close()
        assert not errors, errors
    finally:
        server.shutdown()
        thread.join(3)
        server.server_close()
        (output / "result.json").write_text(
            json.dumps(
                {"passed": len(checks) == 2 and not errors, "checks": checks, "errors": errors},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    print("PASS: nine bilingual layers, actual WebGL orbit, keyboard, mobile and reduced motion")


if __name__ == "__main__":
    main()
