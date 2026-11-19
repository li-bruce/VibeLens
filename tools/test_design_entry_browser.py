"""Check readable first-design views and locale names through the real Web server.

Each language uses a clean project cloned from a source-free definition. Personal
view restoration is exercised through UI controls; no runtime facts are generated.
"""

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def available_port():
    """Ask the host for a free loopback port for this isolated server."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def wait_server(process, url):
    """Wait for an actual HTTP response, failing early if the server exits."""
    for _ in range(150):
        if process.poll() is not None:
            raise RuntimeError("Design server exited before responding")
        try:
            with urllib.request.urlopen(url + "/api/view", timeout=1) as response:
                return json.load(response)
        except OSError:
            time.sleep(0.2)
    raise TimeoutError("Design server did not respond")


def run(source, output, executable):
    """Retain screenshots and exact failures for both locales and saved views."""
    output.mkdir(parents=True, exist_ok=False)
    result = {"valid": False, "checks": [], "errors": [], "runtime_events": 0}
    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch(
                headless=True, executable_path=executable, args=["--enable-unsafe-swiftshader"]
            )
            for locale in ("en", "zh-CN"):
                with tempfile.TemporaryDirectory(dir=ROOT / ".validation") as folder:
                    project = Path(folder)
                    shutil.copyfile(source / "discovery.json", project / "discovery.json")
                    config = project / "bo_stategraph/config"
                    config.mkdir(parents=True)
                    for name in ("semantic-names.json", "interface.json"):
                        original = source / "bo_stategraph/config" / name
                        if original.is_file():
                            shutil.copyfile(original, config / name)
                    url = f"http://127.0.0.1:{available_port()}"
                    with (output / (locale + "-server.log")).open("w", encoding="utf-8") as log:
                        process = subprocess.Popen(
                            [
                                sys.executable,
                                str(ROOT / "skills/vibelens/scripts/bo_web.py"),
                                "serve",
                                "--root",
                                str(project),
                                "--port",
                                url.rsplit(":", 1)[1],
                            ],
                            cwd=ROOT,
                            stdout=log,
                            stderr=log,
                        )
                        try:
                            view = wait_server(process, url)
                            assert view["stage"] == "design" and view["events"] == []
                            context = browser.new_context(viewport={"width": 1600, "height": 1050})
                            page = context.new_page()
                            page.on("pageerror", lambda error: result["errors"].append(str(error)))
                            page.goto(url + "/graph?lang=" + locale, wait_until="domcontentloaded")
                            page.wait_for_function(
                                "window.graphDebug?.graph && !graphDebug.layoutBusy"
                            )
                            assert page.input_value("#analysis-view") == "business"
                            for mode in ("2D", "3D"):
                                if page.locator("#layered-toggle").inner_text() != mode:
                                    page.click("#layered-toggle")
                                page.wait_for_function(
                                    "!graphDebug.layoutBusy && !graphDebug.geometryBusy"
                                )
                                page.click("#fit")
                                page.wait_for_function(
                                    "!graphDebug.layoutBusy && !graphDebug.geometryBusy"
                                )
                                page.screenshot(path=str(output / f"{locale}-{mode}-business.png"))
                            page.select_option("#analysis-view", "states")
                            page.wait_for_function("!graphDebug.layoutBusy")
                            # Flush the actual preference debounce before reloading the page.
                            page.wait_for_timeout(800)
                            page.reload(wait_until="domcontentloaded")
                            page.wait_for_function(
                                "window.graphDebug?.graph && !graphDebug.layoutBusy"
                            )
                            assert page.input_value("#analysis-view") == "states"
                            assert page.evaluate("graphDebug.view.events.length") == 0
                            page.screenshot(path=str(output / f"{locale}-restored-state-view.png"))
                            result["checks"].append(
                                {
                                    "locale": locale,
                                    "initial": "business",
                                    "restored": "states",
                                    "modes": ["2D", "3D"],
                                }
                            )
                            context.close()
                        finally:
                            process.terminate()
                            process.wait(timeout=10)
            browser.close()
        assert not result["errors"], result["errors"]
        result["valid"] = True
    except Exception as error:
        result.update(failure=str(error), traceback=traceback.format_exc())
    (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser", default=os.environ.get("BO_BROWSER_EXECUTABLE"))
    args = parser.parse_args()
    outcome = run(args.project, args.out, args.browser)
    print(json.dumps(outcome))
    raise SystemExit(not outcome["valid"])
