"""Inspect an actual TLC counterexample in desktop Graph/logical Timeline.

Uses a source-free design server and imported exported trace, never substituted
HTTP responses or synthetic runtime events. Conversation acceptance is later.
"""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "skills/vibelens/scripts")]
from test_native_behavior_integration import NativeIntegrationTests
from test_tlc_runtime import finite_fixture
from test_behavior_contract import literal, variable, operation
from bo_observer.analysis.runner import run_profile
from bo_observer.project_artifacts import byte_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if (out / "result.json").exists():
        raise FileExistsError("Choose a fresh evidence folder")
    fixture = NativeIntegrationTests()
    fixture.setUp()
    snapshot = finite_fixture()
    snapshot["behavior"]["properties"][0].update(
        kind="state_invariant",
        action_refs=[],
        expression=operation("eq", variable(), literal("inactive", "status")),
    )
    fixture.project["model"].pop("behavior_bindings")
    for role, name, value in (
        ("behavior", "bo_stategraph/behavior.json", snapshot["behavior"]),
        ("discovery", "discovery.json", snapshot["behavior_discovery"]),
    ):
        raw = (json.dumps(value) + "\n").encode("utf-8")
        (fixture.root / name).write_bytes(raw)
        fixture.project["contracts"][role] = {
            "path": name,
            "schema": value["schema"],
            "sha256": byte_hash(raw),
        }
    fixture.write()
    analysis = run_profile(fixture.root, snapshot, "small")
    if analysis["status"] != "fail":
        raise AssertionError(analysis["results"])
    trace = fixture.root / analysis["directory"] / "property-0/logical-trace.json"
    import shutil

    shutil.copyfile(trace, out / "logical-trace.json")
    checks = []
    errors = []
    result = {
        "valid": False,
        "checks": checks,
        "errors": errors,
        "origin": "actual TLC design counterexample",
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
            url = re.search(r"http://127\.0\.0\.1:\d+/graph", line).group()
            with sync_playwright() as driver:
                browser = driver.chromium.launch(
                    headless=True,
                    executable_path=os.environ.get("BO_BROWSER_EXECUTABLE"),
                    args=["--enable-unsafe-swiftshader"],
                )
                page = browser.new_page(viewport={"width": 1500, "height": 1000})
                page.on("pageerror", lambda error: errors.append(str(error)))
                try:
                    for locale in ("en", "zh-CN"):
                        page.goto(url + "?lang=" + locale)
                        page.wait_for_function(
                            "window.graphDebug?.graph && !graphDebug.layoutBusy"
                        )
                        for mode in ("2D", "3D"):
                            if page.locator("#layered-toggle").inner_text() != mode:
                                page.click("#layered-toggle")
                            page.select_option("#analysis-view", "states")
                            page.click("#expand")
                            page.click("#fit")
                            page.locator("#analysis-trace-file").set_input_files(trace)
                            page.wait_for_selector(
                                "#analysis-trace-panel:not([hidden]) svg"
                            )
                            slider = page.locator(
                                "#analysis-trace-panel input[type=range]"
                            )
                            slider.fill("1")
                            slider.dispatch_event("input")
                            page.wait_for_function(
                                "graphDebug.selectedNodes.includes('state:grant:active')"
                            )
                            text = page.locator("#analysis-trace-panel").inner_text()
                            assert "inactive" in text and "active" in text, text
                            assert (
                                "模型反例"
                                if locale == "zh-CN"
                                else "Model counterexample"
                            ) in text
                            assert page.evaluate("graphDebug.view.events.length") == 0
                            before = page.evaluate("graphDebug.view.events.length")
                            svg = page.locator(
                                "#analysis-trace-panel svg"
                            ).bounding_box()
                            page.mouse.move(
                                svg["x"] + svg["width"] * 0.9, svg["y"] + 15
                            )
                            page.mouse.down()
                            page.mouse.move(
                                svg["x"] + svg["width"] * 0.12, svg["y"] + 15, steps=10
                            )
                            page.mouse.up()
                            assert slider.input_value() == "0"
                            assert (
                                page.evaluate("graphDebug.view.events.length") == before
                            )
                            slider.fill("1")
                            slider.dispatch_event("input")
                            page.screenshot(path=str(out / f"{locale}-{mode}.png"))
                            checks.append(
                                {
                                    "locale": locale,
                                    "mode": mode,
                                    "logical_drag": True,
                                    "runtime_events": before,
                                }
                            )
                            page.locator(".analysis-trace-header button").click()
                    assert not errors, errors
                    result["valid"] = True
                finally:
                    if not result["valid"]:
                        page.screenshot(path=str(out / "failure.png"))
                    browser.close()
        except Exception as error:
            result.update(failure=str(error), traceback=traceback.format_exc())
        finally:
            server.terminate()
            server.wait(timeout=10)
            fixture.doCleanups()
            (out / "result.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
    print(json.dumps(result, ensure_ascii=False))
    return int(not result["valid"])


if __name__ == "__main__":
    raise SystemExit(main())
