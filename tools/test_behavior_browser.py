"""Inspect pinned behavior in the real design server using desktop Chromium.

This is an automated UI fixture, not a new conversation or business acceptance.
The server reads actual project artifacts; browser responses are never replaced.
"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback

from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "skills/vibelens/scripts")]
from test_native_behavior_integration import NativeIntegrationTests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if (out / "result.json").exists():
        raise FileExistsError("Use a fresh evidence directory")
    fixture = NativeIntegrationTests()
    fixture.setUp()
    checks, errors = [], []
    result = {
        "valid": False,
        "checks": checks,
        "errors": errors,
        "scope": "Automated desktop design fixture; no application execution",
    }
    with (out / "server.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(ROOT / "skills/vibelens/scripts/bo_web.py"),
                "serve",
                "--root",
                str(fixture.root),
                "--port",
                "0",
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=log,
            text=True,
            encoding="utf-8",
        )
        try:
            line = server.stdout.readline()
            match = re.search(r"http://127\.0\.0\.1:\d+/graph", line)
            if not match:
                raise RuntimeError("Design server did not start: " + line)
            with sync_playwright() as driver:
                browser = driver.chromium.launch(
                    headless=True,
                    executable_path=os.environ.get("BO_BROWSER_EXECUTABLE"),
                    args=["--enable-unsafe-swiftshader"],
                )
                try:
                    page = browser.new_page(viewport={"width": 1500, "height": 1000})
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    for locale in ("en", "zh-CN"):
                        page.goto(match.group() + "?lang=" + locale)
                        page.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy")
                        try:
                            page.wait_for_load_state("networkidle", timeout=2000)
                        except BrowserTimeout:
                            page.wait_for_function("graphDebug.view && !graphDebug.sourceBusy")
                        for mode in ("2D", "3D"):
                            if page.locator("#layered-toggle").inner_text() != mode:
                                page.click("#layered-toggle")
                            page.select_option("#analysis-view", "states")
                            page.click("#expand")
                            page.click("#arrange")
                            page.wait_for_function(
                                "!graphDebug.layoutBusy && !graphDebug.sourceBusy"
                            )
                            page.click("#fit")
                            if mode == "3D":
                                page.wait_for_function("graphDebug.spatial?.webgl")
                            page.wait_for_function(
                                "[...document.querySelectorAll('#semantic [data-node-id]')].some(e=>e.dataset.nodeId==='state:grant:active')"
                            )
                            page.locator("#semantic [data-node-id]").evaluate_all(
                                "elements=>elements.find(e=>e.dataset.nodeId==='state:grant:active').click()"
                            )
                            page.locator("#viewport").focus()
                            page.keyboard.press("Shift+F10")
                            page.click("#details")
                            page.wait_for_selector(".behavior-details")
                            label = "Behavior details" if locale == "en" else "行为定义"
                            assert label in page.locator(".behavior-details").inner_text()
                            target = page.locator('[data-behavior-id="variable/grant-status"]')
                            if not target.evaluate("element=>element.open"):
                                target.locator(":scope > summary").click()
                            assert (
                                "inactive" in target.inner_text()
                                and "active" in target.inner_text()
                            )
                            assert target.evaluate("element=>element.open")
                            target.locator(":scope > button").click()
                            assert "state:grant:active" in page.evaluate("graphDebug.selectedNodes")
                            # Trigger normal refresh and confirm detail expansion remains readable.
                            page.wait_for_timeout(1200)
                            assert target.evaluate("element=>element.open")
                            assert page.evaluate("graphDebug.view.events.length") == 0
                            page.screenshot(path=str(out / f"{locale}-{mode}.png"))
                            checks.append(
                                {
                                    "locale": locale,
                                    "mode": mode,
                                    "state_values": ["inactive", "active"],
                                    "retained_detail": True,
                                    "runtime_events": 0,
                                }
                            )
                            page.click("#close-detail")
                    assert not errors, errors
                    result["valid"] = True
                finally:
                    if not result["valid"] and "page" in locals():
                        page.screenshot(path=str(out / "failure.png"))
                    browser.close()
        except Exception as error:
            result["failure"] = str(error)
            result["traceback"] = traceback.format_exc()
        finally:
            server.terminate()
            server.wait(timeout=10)
            fixture.doCleanups()
            (out / "result.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
