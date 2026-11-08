"""Check real recording colors in Pixi draw calls and Three.js instance buffers.

The server serves canonical viewer assets and an unchanged saved recording.
Only view preferences can be written. Test probes observe render calls; UI
actions still use the normal selectors and handlers.
"""

import argparse
import json
import os
import subprocess
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
RECORDING = "docs/review/spatial-workspace/replay-fixture.json"
SERVER = """
import {serveRecording} from './tools/recording_browser_fixture.mjs';
const fixture = await serveRecording(process.argv[1]);
console.log(JSON.stringify({url: fixture.url, id: fixture.recording.id}));
process.stdin.once('data', async () => {
  await fixture.close();
  console.log(JSON.stringify({writes: fixture.writes, requests: fixture.requests.length}));
});
"""

# Instrument the genuine graphics implementations, without replacing model data
# or injecting artificial runtime events. Capture only while inspecting a step.
PROBE = """async () => {
  const {SpatialRenderer} = await import('/spatial-renderer.js');
  const T = await import('/spatial-three.vendor.js');
  const probe = window.edgeColorProbe = {capture:false, planar:new Map(), spatial:[]};
  const polygons = new WeakMap();
  const poly = PIXI.Graphics.prototype.poly;
  PIXI.Graphics.prototype.poly = function(points, ...args) {
    polygons.set(this, points);
    return poly.call(this, points, ...args);
  };
  const fill = PIXI.Graphics.prototype.fill;
  PIXI.Graphics.prototype.fill = function(style) {
    const points = polygons.get(this);
    // The same Graphics also paints node pulses. Consume only the immediately
    // preceding polygon, not a later circle that happens to reuse this object.
    polygons.delete(this);
    if (probe.capture && Array.isArray(points) && points.length === 14) {
      const sample = probe.planar.get(this) || {colors:new Set(), poses:new Set()};
      sample.colors.add(typeof style === 'number' ? style : style?.color);
      sample.poses.add(points.join(','));
      probe.planar.set(this, sample);
    }
    return fill.call(this, style);
  };
  const draw = SpatialRenderer.prototype.drawEdges;
  SpatialRenderer.prototype.drawEdges = function(...args) {
    draw.apply(this, args);
    probe.renderer = this;
  };
  const update = SpatialRenderer.prototype.updateParticles;
  SpatialRenderer.prototype.updateParticles = function(now) {
    update.call(this, now);
    if (!probe.capture || !this.animation || !this.particles?.visible) return;
    const ids = this.animation.ids.filter(id => this.curves.has(id));
    const colors = ids.map((id, i) => {
      const color = new T.Color(); this.particles.getColorAt(i, color);
      return {id, color:color.getHex(), reverse:!!this.animation.transfers.get(id)?.reverse};
    });
    if (probe.spatial.length < 90) probe.spatial.push(colors);
  };
  probe.reset = () => {probe.planar.clear();probe.spatial=[];probe.capture=true;};
  probe.result = () => {
    probe.capture=false;
    return {
      planar:[...probe.planar.values()].filter(s => s.poses.size > 1)
        .map(s => ({colors:[...s.colors], poses:s.poses.size})),
      spatial:probe.spatial,
    };
  };
  probe.lines = () => {
    const renderer=probe.renderer;
    const attribute=renderer?.lines?.geometry.attributes.instanceColorStart;
    const profile=renderer?.lines?.geometry.attributes.boStrokeProfile;
    if (!attribute) return [];
    return renderer.edgeSegments.filter(item => !item.edge.guide && item.end > item.start)
      .map(item => ({id:item.edge.id, color:new T.Color().setRGB(
        attribute.getX(item.start),attribute.getY(item.start),attribute.getZ(item.start)).getHex(),
        width:profile?.getX(item.start), mode:profile?.getY(item.start),
        segments:attribute.count, profiles:profile?.count}));
  };
}"""

STATIC_COLORS = """async mode => {
  const {layerOf} = await import('/graph-layers.js');
  const {layerPalette} = await import('/layer-style.js');
  const {visualType} = await import('/graph-classification.js');
  const {relationStyle} = await import('/layout.js');
  const {strokeProfile} = await import('/relation-strokes.js');
  const ports = mode === '2D' ? graphDebug.planarPorts : graphDebug.spatial.edgePorts;
  const paths = new Map(ports.map(path => [path.id, path]));
  const semantic = new Map([...document.querySelectorAll('[data-edge-id]')]
    .map(el => [el.dataset.edgeId, {...el.dataset}]));
  return graphDebug.presentation.edges.filter(edge => paths.has(edge.id)).map(edge => {
    const from=layerOf(graphDebug.graph.byId.get(edge.from).node);
    const to=layerOf(graphDebug.graph.byId.get(edge.to).node);
    const sameType=visualType(graphDebug.graph.byId.get(edge.from).node)===visualType(graphDebug.graph.byId.get(edge.to).node);
    const style=relationStyle(edge,graphDebug.graph.byId), profile=strokeProfile(style);
    return {id:edge.id, from, to, expected:from===to ? layerPalette[from] : 0x6f7d8d,
      color:paths.get(edge.id).color, semantic:semantic.get(edge.id),
      sameType, stroke:style.stroke, dash:style.dash, width:profile.width*style.width, mode:profile.mode};
  });
}"""


def settled(page):
    """Wait for workers and accepted routes instead of sleeping through rendering."""
    page.wait_for_function("window.graphDebug?.graph && !graphDebug.layoutBusy", timeout=30000)


def check_static(page, mode):
    """Read rendered path colors and, in 3D, the actual GPU line-color buffer."""
    rows = page.evaluate(STATIC_COLORS, mode)
    assert rows, f"No rendered paths in {mode}"
    for row in rows:
        assert row["color"] == row["expected"], row
        assert row["semantic"]["color"] == f'#{row["expected"]:06x}', row
        assert row["semantic"]["stroke"] == ("solid" if row["sameType"] else "dashed"), row
        assert bool(row["dash"]) is not row["sameType"], row
        assert row["semantic"]["strokeProfile"] == row["stroke"], row
    if mode == "3D":
        expected = {row["id"]: row for row in rows}
        for line in page.evaluate("edgeColorProbe.lines()"):
            row = expected[line["id"]]
            assert line["color"] == row["expected"], line
            assert line["mode"] == row["mode"], line
            assert abs(line["width"] - row["width"]) < 1e-5, line
            assert line["profiles"] == line["segments"], line
    return rows


def check_step(page, mode, index):
    """Select one recorded event and observe multiple real animation frames."""
    epoch = page.locator("#renderer").get_attribute("data-animation-epoch") or "0"
    page.select_option("#replay-events", str(index))
    page.wait_for_function(
        "epoch => Number(document.querySelector('#renderer').dataset.animationEpoch)>epoch"
        " && document.querySelector('#renderer').dataset.animationActive === 'true'"
        " && JSON.parse(document.querySelector('#renderer').dataset.animatedEdges || '[]').length",
        arg=int(epoch),
    )
    # A previous paused step may still be looping while selection is applied.
    # Capture only the newly selected animation, never those earlier frames.
    page.evaluate("edgeColorProbe.reset()")
    try:
        page.wait_for_function(
            "[...edgeColorProbe.planar.values()].some(s=>s.poses.size>3)"
            if mode == "2D"
            else "edgeColorProbe.spatial.length>3"
        )
    except PlaywrightTimeoutError as error:
        # Preserve the actual renderer state before the browser is closed. This
        # distinguishes missing paths, mode changes and stopped animation clocks
        # from a slow draw call without accepting fewer frames or guessed colors.
        details = page.evaluate(
            """() => ({
              renderer: {...document.querySelector('#renderer').dataset},
              spatial: graphDebug.layers.enabled,
              hidden: document.hidden,
              layoutBusy: graphDebug.layoutBusy,
              geometryBusy: graphDebug.geometryBusy,
              sourceBusy: graphDebug.sourceBusy,
              replay: graphDebug.view.replay?.index,
              capture: edgeColorProbe.capture,
              planar: [...edgeColorProbe.planar.values()].map(sample => ({
                colors:[...sample.colors], poses:sample.poses.size
              })),
              spatialFrames: edgeColorProbe.spatial.length,
              transfers: graphDebug.transferPoints,
              routes: graphDebug.planarPorts.map(route=>route.id)
            })"""
        )
        raise AssertionError(
            f"Missing moving-arrow frames in {mode}, step {index}: " + json.dumps(details)
        ) from error
    painted = page.evaluate("edgeColorProbe.result()")
    ids = page.locator("#renderer").evaluate("el=>JSON.parse(el.dataset.animatedEdges)")
    rows = page.evaluate(STATIC_COLORS, mode)
    expected = {row["id"]: row["expected"] for row in rows if row["id"] in ids}
    assert expected, {"mode": mode, "index": index, "ids": ids}
    if mode == "2D":
        actual = {color for sample in painted["planar"] for color in sample["colors"]}
        assert actual == set(expected.values()), {"actual": actual, "expected": expected}
    else:
        for frame in painted["spatial"]:
            assert {item["id"] for item in frame} == set(expected), frame
            for arrow in frame:
                assert arrow["color"] == expected[arrow["id"]], arrow
    return {"event_index": index, "edge_colors": expected, "draws": painted}


def main():
    """Keep screenshots and reports, including failures, in an explicit output path."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=".validation/edge-colors")
    parser.add_argument("--browser", default=os.environ.get("BO_BROWSER_EXECUTABLE"))
    args = parser.parse_args()
    output = Path(args.out).resolve()
    output.mkdir(parents=True, exist_ok=True)
    recording = json.loads((ROOT / RECORDING).read_text(encoding="utf-8"))
    process = subprocess.Popen(
        ["node", "--input-type=module", "-e", SERVER, RECORDING],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    errors, results = [], {"recording": RECORDING, "modes": {}}
    try:
        server = json.loads(process.stdout.readline())
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True, executable_path=args.browser, args=["--enable-unsafe-swiftshader"]
            )
            try:
                page = browser.new_page(viewport={"width": 1600, "height": 1000})
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on(
                    "console",
                    lambda message: (
                        errors.append(message.text)
                        if message.type == "error"
                        and any(
                            word in message.text
                            for word in ("Shader Error", "VALIDATE_STATUS", "THREE.WebGLProgram")
                        )
                        else None
                    ),
                )
                # The live viewer polls every 400 ms, so networkidle never settles.
                # Wait for its graph and workers explicitly after loading the DOM.
                page.goto(server["url"] + "?lang=zh-CN", wait_until="domcontentloaded")
                settled(page)
                page.evaluate(PROBE)
                page.select_option("#record-list", server["id"])
                page.select_option("#replay-grain", "events")
                page.select_option("#analysis-view", "states")
                events = page.evaluate(
                    """async id => {const {timeline}=await import('/recording.js');
                    const recording=await (await fetch('/api/recordings/'+id)).json();
                    const items=timeline(recording);
                    const enter=recording.events.find(event=>event.node==='db.read' && event.phase==='enter');
                    const returned=recording.events.find(event=>event.call_id===enter.call_id && event.phase==='return');
                    return {state:items.findIndex(item=>item.id===recording.runtime_frames.frames[1].event_id),
                      database:[enter,returned].map(event=>items.findIndex(item=>item.id===event.id))};}""",
                    server["id"],
                )
                index = events["state"]
                assert index >= 0
                assert all(index >= 0 for index in events["database"])
                for mode in ("2D", "3D"):
                    if page.locator("#layered-toggle").inner_text() != mode:
                        page.click("#layered-toggle")
                    settled(page)
                    static = check_static(page, mode)
                    transfer = check_step(page, mode, index)
                    page.screenshot(path=str(output / f"state-transfer-{mode}.png"))
                    results["modes"][mode] = {"state_edges": static, "transfer": transfer}
                # Expand the real graph to exercise cross-layer links too, then
                # switch renderers without changing the underlying graph facts.
                ruler = page.locator("#layer-controls canvas").bounding_box()
                page.mouse.click(ruler["x"] + ruler["width"] - 15, ruler["y"] + 18)
                settled(page)
                page.click("#expand")
                page.keyboard.press("Escape")
                settled(page)
                for mode in ("3D", "2D"):
                    if page.locator("#layered-toggle").inner_text() != mode:
                        page.click("#layered-toggle")
                    settled(page)
                    rows = check_static(page, mode)
                    assert any(row["from"] == row["to"] for row in rows)
                    assert any(row["from"] != row["to"] for row in rows)
                    results["modes"][mode]["expanded_edges"] = rows
                    # Resolved data transfer is witnessed at return, not merely
                    # by entering a query. Keep that observation rule intact.
                    transfer = check_step(page, mode, events["database"][1])
                    assert 0x6F7D8D in transfer["edge_colors"].values()
                    results["modes"][mode]["database_transfer"] = transfer
                    page.screenshot(path=str(output / f"expanded-{mode}.png"))
                assert page.locator(".edge-color-key").inner_text() == "同层随层色 · 跨层灰色"
                assert page.locator("[data-legend-types]").inner_text() == "不同类型节点"
                page.goto(server["url"] + "?lang=en", wait_until="domcontentloaded")
                settled(page)
                assert (
                    page.locator(".edge-color-key").inner_text() == "Layer color · Cross-layer gray"
                )
                assert page.locator("[data-legend-types]").inner_text() == "Different node types"
                assert not errors, errors
            finally:
                browser.close()
        stdout, stderr = process.communicate("stop\n", timeout=20)
        server_result = json.loads(stdout.strip())
        assert not server_result["writes"], server_result
        assert process.returncode == 0, stderr
        assert json.loads((ROOT / RECORDING).read_text(encoding="utf-8")) == recording
        results.update(valid=True, errors=errors, server=server_result)
        (output / "result.json").write_text(
            json.dumps(results, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        print(
            "PASS: 2D/3D rendered lines, real moving arrows, folded/expanded views and bilingual legend."
        )
    except Exception as error:
        results.update(valid=False, error=str(error), errors=errors)
        (output / "failure.json").write_text(
            json.dumps(results, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        raise
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
