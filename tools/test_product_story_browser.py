"""Exercise the public story through actual controls and retain review screenshots.

The bundled recording is a teaching case with real execution evidence. This
checks its presentation and interaction, not a fresh application acceptance.
"""

import argparse
import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright


def run(base, output, browser_path):
    output.mkdir(parents=True, exist_ok=True)
    results, errors = [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=browser_path,
            args=["--enable-unsafe-swiftshader"],
        )
        try:
            for language in ("en", "zh-CN"):
                context = browser.new_context(viewport={"width": 1440, "height": 1000})
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"{base}/index.html?lang={language}", wait_until="networkidle")
                expect(page.locator("html")).to_have_attribute("lang", language)
                expect(page.locator("h1")).to_contain_text(
                    "See the logic" if language == "en" else "看懂 AI"
                )
                page.locator("#explore").scroll_into_view_if_needed()
                page.wait_for_function(
                    "document.querySelector('#layer-explorer').dataset.webgl === 'ready'"
                )
                for layer in ("entry", "structure", "symbols"):
                    page.locator(f'[data-layer="{layer}"]').click()
                    expect(page.locator("#layer-explorer")).to_have_attribute(
                        "data-selected-layer", layer
                    )
                page.screenshot(path=str(output / f"depth-{language}.png"))
                # Load the lazy 3D explainer before capturing the whole page.
                page.evaluate("scrollTo(0, 0)")
                page.screenshot(path=str(output / f"home-{language}.png"), full_page=True)
                page.locator("#language").click()
                expect(page.locator("html")).to_have_attribute(
                    "lang", "zh-CN" if language == "en" else "en"
                )
                results.append({"language": language, "home": "passed", "detail_tabs": 3})

                page.goto(f"{base}/demo.html?lang={language}", wait_until="networkidle")

                def scene(name):
                    page.locator(f"#{name}").scroll_into_view_if_needed()
                    page.wait_for_function(
                        "name => document.body.dataset.sceneReady === name", arg=name, timeout=45000
                    )
                    frame = page.locator("#case-graph").element_handle().content_frame()
                    frame.wait_for_function(
                        "window.graphDebug?.graph?.boxes.length && !graphDebug.layoutBusy"
                    )
                    return frame

                frame = scene("foundation")
                expect(page.locator("[data-case-scene]")).to_have_count(5)
                expect(page.locator("#case-conversation [data-speaker]")).to_have_count(1)
                for _ in range(3):
                    page.locator("#conversation-next").click()
                expect(page.locator('.conversation-flow[data-confirmed="false"]')).to_be_visible()
                page.screenshot(path=str(output / f"confirm-{language}.png"))
                page.locator("#conversation-next").click()
                expect(page.locator('.conversation-flow[data-confirmed="true"]')).to_be_visible()
                page.locator("#conversation-next").click()
                frame = scene("run")
                expect(page.locator("#case-application")).to_be_visible()
                frame.wait_for_function("graphDebug.view.replay?.event?.id")
                page.screenshot(path=str(output / f"run-{language}.png"))
                page.locator("#case-3d").click()
                frame.wait_for_function("graphDebug.spatial?.perspective && !graphDebug.layoutBusy")
                camera = frame.evaluate("graphDebug.spatial.camera.position")
                viewport = frame.locator(".spatial-canvas").bounding_box()
                # Use empty canvas near its corner. The middle of the graph can
                # contain a draggable node, which correctly moves instead of orbiting.
                x = viewport["x"] + viewport["width"] * 0.17
                y = max(0, viewport["y"]) + 135
                page.mouse.move(x, y)
                page.mouse.down()
                page.mouse.move(x + 90, y - 45, steps=14)
                page.mouse.up()
                frame.wait_for_function(
                    "old => JSON.stringify(graphDebug.spatial.camera.position) !== JSON.stringify(old)",
                    arg=camera,
                )
                page.screenshot(path=str(output / f"run-3d-{language}.png"))
                page.locator("#case-2d").click()
                frame.wait_for_function("!graphDebug.layers.enabled")
                frame = scene("drill")
                expect(frame.locator("#source-code")).to_contain_text(
                    "shares.c.recipient_id == actor"
                )
                expect(page.locator(".case-playback")).to_be_hidden()
                page.screenshot(path=str(output / f"inspect-{language}.png"))
                page.locator(".view-editor-trigger").click()
                page.locator('[data-watch="effects"]').check()
                page.wait_for_function("document.body.dataset.sceneReady === 'drill'")
                page.locator("#save-watch").click()
                page.wait_for_function("document.body.dataset.savedView")
                expect(page.locator("#view-editor")).to_be_hidden()
                saved = page.get_attribute("body", "data-saved-view")
                frame = scene("iterate")
                expect(page.locator('#case-conversation[data-mode="current"]')).to_be_visible()
                page.locator('[data-scene-action="case.repair"]').click()
                expect(frame.locator("#source-code")).to_contain_text(
                    "shares.c.recipient_id == recipient_id"
                )
                page.screenshot(path=str(output / f"repair-{language}.png"))
                frame = scene("verify")
                expect(page.locator("#case-check")).to_be_visible()
                page.locator('[data-app-action="download-after"]').click()
                page.wait_for_function(
                    "document.querySelector('#case-application').dataset.eventId"
                )
                page.screenshot(path=str(output / f"verify-{language}.png"))
                results[-1].update(demo="passed", saved_view=saved, scenes=5, camera_drag="passed")
                context.close()

            context = browser.new_context(
                viewport={"width": 390, "height": 844}, reduced_motion="reduce"
            )
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            for name in ("index", "demo"):
                page.goto(f"{base}/{name}.html?lang=zh-CN", wait_until="networkidle")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), name
                if name == "index":
                    page.locator("#explore").scroll_into_view_if_needed()
                    page.wait_for_function(
                        "document.querySelector('#layer-explorer').dataset.webgl === 'ready'"
                    )
                    page.evaluate("scrollTo(0, 0)")
                page.screenshot(path=str(output / f"mobile-{name}.png"), full_page=True)
            results.append(
                {"mobile_width": 390, "horizontal_overflow": False, "reduced_motion": True}
            )
            context.close()
            assert not errors, errors
        finally:
            browser.close()
            (output / "result.json").write_text(
                json.dumps({"results": results, "errors": errors}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url", help="Use an existing preview; otherwise serve owned site files locally"
    )
    parser.add_argument("--out", type=Path, default=Path(".validation/clarity-story/browser"))
    parser.add_argument("--browser", default=os.environ.get("BO_BROWSER_EXECUTABLE"))
    args = parser.parse_args()
    server = None
    try:
        if not args.url:

            class QuietHandler(SimpleHTTPRequestHandler):
                def log_message(self, *args):
                    pass

            server = ThreadingHTTPServer(
                ("127.0.0.1", 0), partial(QuietHandler, directory="docs/site")
            )
            Thread(target=server.serve_forever, daemon=True).start()
        url = args.url or f"http://127.0.0.1:{server.server_port}"
        run(url.rstrip("/"), args.out, args.browser)
    finally:
        if server:
            server.shutdown()
            server.server_close()
