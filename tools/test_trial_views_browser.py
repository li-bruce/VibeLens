"""Inspect an existing trial's actual layer views through desktop Chrome.

This runner does not supply a fixture or replace HTTP responses. It changes only
viewer preferences. Use it after the project has finished its own checks, and
retain each run in a new evidence directory. Business/runtime checks are separate.
"""

import argparse
import json
import os
from pathlib import Path
import traceback

from playwright.sync_api import sync_playwright

PRESETS = {
    "business": "business",
    "states": "state",
    "rules": "rules",
    "api": "entry",
    "project": "structure",
    "code": "symbols",
    "database": "data",
}
READY = """() => window.graphDebug?.graph && !graphDebug.sourceBusy &&
    !graphDebug.layoutBusy && !graphDebug.geometryBusy"""


def settle(page):
    """Wait for source loading, layout and accessible camera geometry together."""
    page.wait_for_function(READY, timeout=60000)


def snapshot(page):
    """Read actual displayed identities without changing the graph or its facts."""
    return page.evaluate(
        """() => ({
        layers: graphDebug.layers.visible,
        shown: [...new Set([...graphDebug.presentation.glyphs,
            ...graphDebug.presentation.regions])].sort(),
        camera: graphDebug.camera,
        spatial_camera: graphDebug.spatial?.camera,
        expandable: graphDebug.displayGraph.boxes.find(box =>
            box.kids.length && graphDebug.presentation.glyphs.has(box.id))?.id
    })"""
    )


def check_caption_overlap(page):
    """Right-click a real icon covered by another caption, when the view has one.

    Use only isolated icon centers in this single-layer view. A genuinely
    overlapping nearer icon is not evidence of a wrong caption selection.
    """
    target = page.evaluate(
        """() => {
        const nodes = [...document.querySelectorAll('#semantic [data-node-id]')]
            .filter(e => e.dataset.representation === 'node')
            .map(e => ({id:e.dataset.nodeId,x:+e.dataset.screenX,y:+e.dataset.screenY}));
        return nodes.map(node => ({...node, caption:document.elementFromPoint(node.x,node.y)
            ?.closest('[data-spatial-label]')?.dataset.spatialLabel}))
            .find(node => node.caption && node.caption !== node.id &&
                nodes.every(other => other.id === node.id ||
                    Math.hypot(other.x-node.x,other.y-node.y) > 18)) || null;
    }"""
    )
    if not target:
        return {"exercised": False, "reason": "No separated icon covered by another caption"}
    page.mouse.click(target["x"], target["y"], button="right")
    selected = page.evaluate("graphDebug.selectedNodes")
    assert target["id"] in selected, {"caption_overlap": target, "selected": selected}
    page.keyboard.press("Escape")
    return {"exercised": True, "target": target, "selected": selected}


def check_region_caption(page, identity):
    """An expanded group's unobstructed caption opens that group's menu."""
    point = page.evaluate(
        """id => {
        const glyphs = [...document.querySelectorAll('#semantic [data-node-id]')]
            .filter(e=>e.dataset.representation !== 'circle');
        return [...document.querySelectorAll('[data-spatial-region]')]
            .filter(e=>e.dataset.spatialRegion === id)
            .map(e=>{const r=e.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2};})
            .find(p=>document.elementFromPoint(p.x,p.y)?.closest('[data-spatial-region]')
                ?.dataset.spatialRegion === id && glyphs.every(e=>
                    Math.hypot(+e.dataset.screenX-p.x,+e.dataset.screenY-p.y)>18)) || null;
    }""",
        identity,
    )
    if not point:
        return {"exercised": False, "reason": "No unobstructed region caption"}
    page.mouse.click(point["x"], point["y"], button="right")
    selected = page.evaluate("graphDebug.selectedNodes")
    assert identity in selected, {"region_caption": identity, "point": point, "selected": selected}
    page.keyboard.press("Escape")
    return {"exercised": True, "id": identity, "selected": selected}


def run(url, output, executable, presets):
    """Check selected layer presets and expansion with original server responses."""
    output.mkdir(parents=True, exist_ok=False)
    result = {"valid": False, "url": url, "checks": [], "errors": []}
    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch(
                headless=True,
                executable_path=executable,
                args=["--enable-unsafe-swiftshader"],
            )
            page = browser.new_page(viewport={"width": 1600, "height": 1050})
            page.on("pageerror", lambda error: result["errors"].append(str(error)))
            page.goto(url, wait_until="domcontentloaded")
            settle(page)
            assert page.evaluate("graphDebug.view.stage") != "design", "Native project required"
            for preset in presets:
                page.select_option("#analysis-view", preset)
                settle(page)
                page.click("#collapse")
                settle(page)
                modes = []
                for mode in ("2D", "3D"):
                    if page.locator("#layered-toggle").inner_text() != mode:
                        page.click("#layered-toggle")
                    settle(page)
                    page.click("#fit")
                    settle(page)
                    before = snapshot(page)
                    assert before["layers"] == [PRESETS[preset]], (
                        preset,
                        before["layers"],
                    )
                    assert before["shown"], preset + " has no visible application nodes"
                    overlap = check_caption_overlap(page) if mode == "3D" else None
                    page.screenshot(path=str(output / f"{preset}-{mode}.png"))
                    candidate = before.get("expandable")
                    region_menu = None
                    if candidate:
                        point = page.wait_for_function(
                            """id => {
                            const el = [...document.querySelectorAll('#semantic [data-node-id]')]
                                .find(node => node.dataset.nodeId === id);
                            const x = Number(el?.dataset.screenX), y = Number(el?.dataset.screenY);
                            return el && Number.isFinite(x) && Number.isFinite(y) ? {x,y} : false;
                        }""",
                            arg=candidate,
                        ).json_value()
                        page.mouse.dblclick(point["x"], point["y"])
                        settle(page)
                        opened = page.evaluate(
                            """id => ({
                            open: graphDebug.graph.byId.get(id)?.open,
                            region: graphDebug.presentation.regions.has(id),
                            camera: graphDebug.camera,
                            spatial_camera: graphDebug.spatial?.camera
                        })""",
                            candidate,
                        )
                        assert opened["open"] and opened["region"], (
                            preset,
                            mode,
                            candidate,
                        )
                        if mode == "3D":
                            for key in ("position", "target"):
                                assert all(
                                    abs(a - b) < 0.05
                                    for a, b in zip(
                                        opened["spatial_camera"][key],
                                        before["spatial_camera"][key],
                                    )
                                ), "Expansion moved the 3D camera"
                        else:
                            assert (
                                opened["camera"] == before["camera"]
                            ), "Expansion moved the viewport"
                        page.screenshot(path=str(output / f"{preset}-{mode}-expanded.png"))
                        if mode == "3D":
                            region_menu = check_region_caption(page, candidate)
                        page.click("#collapse")
                        settle(page)
                    modes.append(
                        {
                            "mode": mode,
                            "shown": before["shown"],
                            "expanded": candidate,
                            "caption_overlap": overlap,
                            "region_menu": region_menu,
                        }
                    )
                assert modes[0]["shown"] == modes[1]["shown"], "2D/3D display identity mismatch"
                result["checks"].append({"preset": preset, "modes": modes})
            assert not result["errors"], result["errors"]
            browser.close()
        result["valid"] = True
    except Exception as error:
        result.update(failure=str(error), traceback=traceback.format_exc())
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser", default=os.environ.get("BO_BROWSER_EXECUTABLE"))
    parser.add_argument("--views", nargs="+", choices=PRESETS, default=list(PRESETS))
    args = parser.parse_args()
    result = run(args.url, args.out, args.browser, args.views)
    print(json.dumps({key: value for key, value in result.items() if key != "checks"}))
    raise SystemExit(not result["valid"])
