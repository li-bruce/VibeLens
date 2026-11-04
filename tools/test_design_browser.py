"""Open a source-free concept draft in the real design server and shared viewer.

The default fixture is the shipped unconfirmed v2 design. An explicit discovery
file can reproduce a trial failure; it is copied into an isolated project and
never edited. No application implementation or runtime facts are supplied.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/vibelens"


def visible_screen_bounds(page):
    """Measure rendered glyph and region extents after the real camera transform."""
    return page.evaluate(
        """() => {
            const {displayGraph, presentation, camera} = graphDebug;
            const viewport = document.querySelector('#viewport').getBoundingClientRect();
            const objects = [
                ...displayGraph.boxes.filter(box => presentation.glyphs.has(box.id))
                    .map(box => ({...box, shape: 'glyph'})),
                ...displayGraph.regions.filter(region => presentation.regions.has(region.id))
                    .map(region => ({...region, shape: 'region'})),
            ].map(box => ({
                id: box.id,
                shape: box.shape,
                left: box.x * camera.scale + camera.pan.x,
                right: (box.x + box.w) * camera.scale + camera.pan.x,
                top: box.y * camera.scale + camera.pan.y,
                bottom: (box.y + box.h) * camera.scale + camera.pan.y,
            }));
            return {width: viewport.width, height: viewport.height, camera, objects};
        }"""
    )


def main():
    """Retain both failed startup and successful interactions as reviewable evidence."""
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--discovery", type=Path, default=SKILL / "assets/discovery.concepts.example.json"
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(
            os.environ.get("BO_DESIGN_BROWSER_EVIDENCE", ROOT / ".validation/design-browser")
        ),
    )
    parser.add_argument("--browser", default=os.environ.get("BO_BROWSER_EXECUTABLE"))
    args = parser.parse_args()
    output = args.out.resolve()
    project = output / "project"
    project.mkdir(parents=True, exist_ok=True)
    raw = args.discovery.read_bytes()
    target = project / "discovery.json"
    target.write_bytes(raw)
    errors, checks = [], []
    result = {
        "passed": False,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "checks": checks,
        "errors": errors,
        "geometry": {},
    }
    browser = page = None
    with (output / "server.stderr").open("w", encoding="utf-8") as server_log:
        server = subprocess.Popen(
            [
                sys.executable,
                "-B",
                "-X",
                "utf8",
                str(SKILL / "scripts/bo_web.py"),
                "serve",
                "--root",
                str(project),
                "--port",
                "0",
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=server_log,
            text=True,
            encoding="utf-8",
        )
        try:
            line = server.stdout.readline()
            (output / "server.stdout").write_text(line, encoding="utf-8")
            match = re.search(r"http://127\.0\.0\.1:\d+/graph", line)
            if not match:
                raise RuntimeError("Design server did not publish its local graph URL")
            url = match.group()
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True,
                    executable_path=args.browser,
                    args=["--enable-unsafe-swiftshader"],
                )
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on(
                    "console",
                    lambda message: (
                        errors.append(message.text) if message.type == "error" else None
                    ),
                )
                try:
                    page.goto(url + "?lang=zh-CN")
                    page.wait_for_function(
                        "window.graphDebug?.view?.stage === 'design' && "
                        "graphDebug.graph?.boxes?.length > 0 && !graphDebug.layoutBusy"
                    )
                    envelope = page.request.get(url.replace("/graph", "/api/view")).json()
                    assert "presentation" not in envelope["model"]
                    assert envelope["events"] == []
                    assert envelope["machine"] == {
                        "configurations": [],
                        "current": None,
                        "journal": [],
                    }
                    assert envelope["manifest"]["bindings"] == {}
                    assert (
                        page.locator("#project-title").inner_text()
                        == envelope["model"]["project_id"]
                    )
                    assert page.locator(".record-bar").is_hidden()
                    assert page.locator("#program-link").is_hidden()
                    checks.append(
                        "source-free draft loads without fabricated runtime or presentation metadata"
                    )
                    for preset, layer in (
                        ("business", "business"),
                        ("states", "state"),
                        ("rules", "rules"),
                    ):
                        page.select_option("#analysis-view", preset)
                        page.click("#expand")
                        page.click("#arrange")
                        page.wait_for_function("!graphDebug.layoutBusy")
                        page.click("#fit")
                        page.evaluate(
                            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
                        )
                        assert page.evaluate(
                            "layer => graphDebug.graph.boxes.some(box => box.node.layer === layer)",
                            layer,
                        )
                        assert page.evaluate("graphDebug.presentation.edges.length > 0")
                        page.screenshot(path=str(output / (preset + ".png")))
                        geometry = visible_screen_bounds(page)
                        result["geometry"][preset] = geometry
                        assert geometry["objects"], preset + " has no rendered geometry"
                        for item in geometry["objects"]:
                            assert (
                                item["left"] >= -1
                                and item["top"] >= -1
                                and item["right"] <= geometry["width"] + 1
                                and item["bottom"] <= geometry["height"] + 1
                            ), f"{preset}: Fit clipped {item} in {geometry['width']}x{geometry['height']}"
                        checks.append(preset + " preset displays and fits declared concepts")
                    assert not errors, errors
                    assert target.read_bytes() == raw
                    assert args.discovery.read_bytes() == raw
                    checks.append("viewing preserves the draft and original confirmation content")
                    result["passed"] = True
                finally:
                    if page:
                        page.screenshot(path=str(output / "final.png"))
                    if browser:
                        browser.close()
        except Exception as error:
            result["failure"] = str(error)
        finally:
            server.terminate()
            server.wait(timeout=10)
            (output / "result.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "checks": len(checks),
                "errors": len(errors),
                "evidence": str(output),
            }
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
