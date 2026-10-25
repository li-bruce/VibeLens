/** Real viewer acceptance: perspective camera, 3D drag, source provenance and replay. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
const { chromium } = createRequire(import.meta.url)("playwright");
const root = fileURLToPath(new URL("../", import.meta.url));
const output = path.resolve(process.env.BO_BROWSER_EVIDENCE || "docs/review/spatial-graph/browser");
await mkdir(output, { recursive: true });
const port = process.env.BO_BROWSER_PORT || "8890",
  base = `http://127.0.0.1:${port}`;
const server = spawn(
  process.env.BO_PYTHON ||
    path.join(root, process.platform === "win32" ? ".venv/Scripts/python.exe" : ".venv/bin/python"),
  ["-B", "-X", "utf8", "tools/database_demo.py", "--port", port],
  { cwd: root, windowsHide: true },
);
let logs = "",
  browser,
  page;
const errors = [],
  checks = {};
server.stdout.on("data", (d) => (logs += d));
server.stderr.on("data", (d) => (logs += d));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const request = async (route, body) => {
  const r = await fetch(
    base + route,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const value = await r.json();
  assert.ok(r.ok, JSON.stringify(value));
  return value;
};
async function pick(id) {
  await page
    .locator("#semantic [data-node-id]")
    .evaluateAll((items, id) => items.find((e) => e.dataset.nodeId === id).click(), id);
}
async function expand(id) {
  await pick(id);
  await page.click("#selection-menu");
  await page.click("#node-expand");
  await page.waitForTimeout(180);
}
async function isolateLayer(id) {
  await page.click("#layers-all");
  const ids = await page
    .locator("#layer-controls button[data-layer]")
    .evaluateAll((items) => items.map((e) => e.dataset.layer));
  for (const other of ids)
    if (other !== id) await page.click(`#layer-controls [data-layer="${other}"]`);
}
async function shot(name) {
  await page.screenshot({ path: path.join(output, name + ".png"), fullPage: true });
}
try {
  let ready = false;
  for (let i = 0; i < 90; i++) {
    try {
      await request("/api/bo/health");
      ready = true;
      break;
    } catch {
      if (server.exitCode !== null) throw Error(logs);
      await sleep(250);
    }
  }
  assert.ok(ready);
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(base + "/graph?lang=en");
  await page.waitForFunction(() => window.graphDebug?.graph?.boxes.length > 0);
  await page.waitForTimeout(400);
  await expand("publish");
  await expand("transaction");
  checks.quietCapture = await page.evaluate(() => {
    const g = graphDebug.graph;
    return {
      shown: g.boxes.filter((b) => b.node.event_node === "transaction").map((b) => b.node.field),
      all: [...g.all.values()].filter((n) => n.event_node === "transaction").length,
    };
  });
  assert.ok(checks.quietCapture.all > 10);
  assert.deepEqual(checks.quietCapture.shown.sort(), ["committed", "status"]);
  await pick("field:transaction:out:status");
  await page.click("#selection-menu");
  await page.click("#source");
  assert.match(await page.locator("#detail-rows").innerText(), /outputs.status/);
  assert.match(await page.locator("#detail-rows").innerText(), /collection owner/);
  assert.match(await page.locator("#source-code").innerText(), /\d+\s+def publish/);
  assert.equal(
    await page.locator("#source-code mark").count(),
    0,
    "Event fields must not highlight a function as a parameter",
  );
  await shot("capture-owner");
  await page.keyboard.press("Escape");
  await expand("save");
  assert.equal(
    await page.locator('#semantic [data-node-id="field:save:out:committed"]').count(),
    0,
  );
  await pick("field:save:out:status");
  await page.click("#selection-menu");
  await page.click("#source");
  assert.match(await page.locator("#source-code").innerText(), /def save_pictures/);
  assert.equal(await page.locator("#source-code mark").count(), 0);
  checks.operationFieldsAreNotSourceParameters = true;
  await shot("write-operation-source-context");
  await page.keyboard.press("Escape");
  await expand("save");
  await page.keyboard.press("Escape");
  checks.stateLinks = await page.evaluate(() =>
    graphDebug.graph.rawEdges
      .filter((e) => e.id.startsWith("publication-"))
      .map((e) => [e.from, e.to]),
  );
  assert.equal(checks.stateLinks.length, 2);
  await page.click("#fit");
  const before = await page.evaluate(() => graphDebug.graph.boxes.map((b) => [b.id, b.x, b.y]));
  await page.click("#layered-toggle");
  await page.waitForFunction(() => graphDebug.spatial?.perspective && !graphDebug.layoutBusy);
  await page.waitForTimeout(250);
  checks.initial3D = await page.evaluate(() => graphDebug.spatial);
  checks.routeGapGeometry = await page.evaluate(async () => {
    const { spatialScene } = await import("/routing-scene.js"),
      { spatialModel } = await import("/spatial-model.js");
    const scene = spatialScene(
      spatialModel(graphDebug.displayGraph, graphDebug.presentation),
      graphDebug.spatialPositions,
      graphDebug.spatial.volumes,
      "curve",
    );
    return scene.edges
      .filter((e) => graphDebug.spatial.routeSolver?.failures?.includes(e.id))
      .map((e) => ({
        edge: e,
        obstacles: scene.obstacles.filter((o) => o.level === e.a.level || o.level === e.b.level),
      }));
  });
  assert.ok(checks.initial3D.webgl);
  assert.ok(checks.initial3D.volumes.some((v) => v.projection));
  const delta = checks.initial3D.camera.position.map(
    (v, i) => v - checks.initial3D.camera.target[i],
  );
  assert.ok(
    delta[1] > 0 && Math.hypot(delta[0], delta[2]) / delta[1] < 0.001,
    "3D starts from above",
  );
  assert.equal(await page.locator("#legend-panel").getAttribute("data-mode"), "3D");
  assert.ok(
    (await page.locator('#legend-types img[data-mode="3D"][data-geometry="webgl"]').count()) > 0,
  );
  assert.equal(await page.locator("#layer-camera, #layer-only, #layout-panel").count(), 0);
  const arrangement = await page.evaluate(() => {
    const rect = (id) => document.querySelector(id).getBoundingClientRect().toJSON();
    return {
      breadcrumbs: rect("#hierarchy-path"),
      tools: rect(".view-tools"),
      legend: rect("#legend-panel"),
      drawer: rect("#layer-drawer"),
      width: innerWidth,
    };
  });
  assert.ok(
    Math.abs(arrangement.tools.x + arrangement.tools.width / 2 - arrangement.width / 2) < 2,
  );
  assert.ok(arrangement.breadcrumbs.y < arrangement.drawer.y);
  assert.ok(arrangement.legend.y < arrangement.tools.y);
  assert.ok(arrangement.legend.width < arrangement.legend.height);
  await page.click("#layers-toggle");
  assert.equal(await page.locator("#layers-toggle").getAttribute("aria-expanded"), "false");
  assert.ok((await page.locator("#layer-drawer").boundingBox()).width < 60);
  assert.equal(await page.locator(".layer-select:visible").count(), 0);
  assert.equal(await page.locator(".layer-eye:visible").count(), 8);
  await page.click("#layer-spacing-toggle");
  assert.equal(await page.locator("#layer-spacing-toggle").getAttribute("aria-expanded"), "true");
  assert.equal(await page.locator("#layers-toggle").getAttribute("aria-expanded"), "true");
  await page.locator("#layer-gap").fill("360");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  assert.equal(await page.locator("#layer-gap").inputValue(), "360");
  const planeFacts = await page.evaluate(() => {
    const ys = new Map();
    for (const el of document.querySelectorAll("#semantic [data-node-id]")) {
      const layer = el.dataset.plane;
      if (!ys.has(layer)) ys.set(layer, new Set());
      ys.get(layer).add(el.dataset.worldY);
    }
    return [...ys].map(([id, y]) => [id, [...y]]);
  });
  assert.ok(planeFacts.every(([, ys]) => ys.length === 1));
  const renderedPlanes = await page.evaluate(() => graphDebug.spatial.layerPlanes);
  for (const [layer, ys] of planeFacts)
    assert.equal(renderedPlanes.find((p) => p.id === layer)?.y, Number(ys[0]));
  assert.equal(renderedPlanes.length, planeFacts.length);
  checks.coplanarLayers = true;

  const rulerLabels = await page
    .locator(".layer-select")
    .evaluateAll((els) =>
      els.map((el) => ({ scroll: el.scrollWidth, width: el.clientWidth, height: el.clientHeight })),
    );
  assert.ok(
    rulerLabels.every((el) => el.scroll <= el.width && el.height >= 24),
    "Layer text is fully visible",
  );
  const orderBefore = await page.evaluate(() => graphDebug.layers.order);
  await page.locator('[data-layer-row="state"] .layer-select').focus();
  await page.keyboard.press("Alt+ArrowUp");
  assert.equal((await page.evaluate(() => graphDebug.layers.order))[1], "state");
  const gap = page.locator('[data-gap-after="state"]');
  await gap.focus();
  await page.keyboard.press("ArrowDown");
  assert.equal(await gap.getAttribute("aria-valuenow"), "380");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  const changedPlanes = await page.evaluate(() => ({
    layers: graphDebug.layers,
    points: graphDebug.spatialPositions,
  }));
  assert.equal(changedPlanes.points["state.published"].y - changedPlanes.points["publish"].y, 380);
  // Restore this test's uniform layout before checking its previous height invariants.
  await page.locator('[data-layer-row="state"] .layer-select').focus();
  await page.keyboard.press("Alt+ArrowDown");
  assert.deepEqual(await page.evaluate(() => graphDebug.layers.order), orderBefore);
  await page.locator("#layer-gap").fill("360");
  await page.dragAndDrop('[data-layer-row="state"] .layer-grip', '[data-layer-row="business"]');
  assert.equal((await page.evaluate(() => graphDebug.layers.order))[1], "state");
  const tick = await page.locator('[data-gap-after="state"]').boundingBox();
  await page.mouse.move(tick.x + 3, tick.y + tick.height / 2);
  await page.mouse.down();
  await page.mouse.move(tick.x + 3, tick.y + tick.height / 2 + 10, { steps: 3 });
  await page.mouse.up();
  assert.equal(await page.locator('[data-gap-after="state"]').getAttribute("aria-valuenow"), "440");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  const customLayers = await page.evaluate(() => graphDebug.layers);
  await page.waitForTimeout(300);
  await page.reload();
  await page.waitForFunction(() => graphDebug?.spatial?.perspective && !graphDebug.layoutBusy);
  assert.deepEqual(
    await page.evaluate(() => graphDebug.layers),
    customLayers,
    "Custom order and individual gaps survive reload",
  );
  await page.locator('[data-layer-row="state"] .layer-select').focus();
  await page.keyboard.press("Alt+ArrowDown");
  await page.locator("#layer-gap").fill("360");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  for (const style of ["straight", "orthogonal", "bus", "curve"]) {
    await page.selectOption("#edge-routing", style);
    await page.waitForTimeout(80);
    assert.equal(await page.evaluate(() => graphDebug.spatial.routing), style);
    const rimFacts = await page.evaluate(() => {
      const g = graphDebug,
        result = [];
      for (const edge of g.presentation.edges) {
        const ports = g.spatial.edgePorts.find((p) => p.id === edge.id);
        if (!ports) continue;
        for (const [id, flag, end] of [
          [edge.from, edge.sourceRegion, ports.start],
          [edge.to, edge.targetRegion, ports.end],
        ]) {
          const volume = g.spatial.volumes.find((v) => v.id === id && !v.projection);
          if (flag && volume)
            result.push({
              edge: edge.id,
              id,
              other: edge.from === id ? edge.to : edge.from,
              end,
              center: volume.center,
              members: volume.members,
              distance: Math.hypot(end.x - volume.center.x, end.z - volume.center.z),
              radius: volume.radius,
            });
        }
      }
      return result;
    });
    assert.ok(rimFacts.length > 0, "Exercise an actual expanded group edge");
    assert.ok(
      rimFacts.every((p) => Math.abs(p.distance - p.radius) < 0.00001),
      JSON.stringify({ style, rimFacts }),
    );
  }
  assert.ok((await page.locator(".region-label .node-badges[data-child-count]").count()) > 0);
  checks.rulerAndBoundaryRoutes = true;
  await shot("3d-top");
  const camera = await page.evaluate(() => graphDebug.spatial.camera.position);
  await page.mouse.move(1000, 650);
  await page.mouse.down();
  await page.mouse.move(1120, 700, { steps: 12 });
  await page.mouse.up();
  await page.waitForTimeout(350);
  assert.notDeepEqual(await page.evaluate(() => graphDebug.spatial.camera.position), camera);
  await isolateLayer("operations");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  assert.deepEqual(
    await page.evaluate(() => graphDebug.spatial.layerPlanes),
    renderedPlanes.filter((p) => p.id === "operations"),
    "A layer mask hides other planes without moving the remaining plane",
  );
  assert.ok(
    await page.evaluate(() =>
      [...document.querySelectorAll("#semantic [data-node-id]")].every(
        (e) => e.dataset.plane === "operations",
      ),
    ),
  );
  await page.click("#layers-all");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  await page.click("#layered-toggle");
  assert.equal(await page.locator("#legend-panel").getAttribute("data-mode"), "2D");
  await isolateLayer("state");
  assert.ok(
    await page.evaluate(() => graphDebug.displayGraph.boxes.every((b) => b.type === "state")),
  );
  await page.click("#layers-all");
  checks.sharedLayerControls = true;
  assert.deepEqual(
    await page.evaluate(() => graphDebug.graph.boxes.map((b) => [b.id, b.x, b.y])),
    before,
  );
  await page.click("#layered-toggle");
  await page.click("#top-view");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  await pick("load");
  await page
    .locator("#focus-selection")
    .click({ timeout: 300 })
    .catch(async () => {
      await page.click("#selection-menu");
      await page.click("#focus-selection");
    });
  await page.waitForTimeout(350);
  const original = await page.evaluate(() => graphDebug.spatialPositions.load);
  const pos = await page
    .locator('#semantic [data-node-id="load"]')
    .evaluate((e) => ({ x: +e.dataset.screenX, y: +e.dataset.screenY }));
  await page.mouse.move(pos.x, pos.y);
  await page.mouse.down();
  await page.mouse.move(pos.x + 45, pos.y + 25, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(350);
  const after = await page.evaluate(() => ({
    positions: graphDebug.spatialPositions,
    layers: graphDebug.layers,
  }));
  assert.notDeepEqual(after.positions.load, original, "Ray-picked node must move in world space");
  assert.deepEqual(
    await page.evaluate(() => graphDebug.graph.boxes.map((b) => [b.id, b.x, b.y])),
    before,
    "3D dragging must preserve 2D layout",
  );
  await page.reload();
  await page.waitForFunction(() => graphDebug?.spatial?.perspective && !graphDebug.layoutBusy);
  assert.equal(await page.locator("#layered-toggle").innerText(), "3D");
  const restored = await page.evaluate(() => graphDebug.spatialPositions.load);
  assert.ok(Math.abs(restored.x - after.positions.load.x) < 0.001);
  assert.ok(Math.abs(restored.z - after.positions.load.z) < 0.001);
  checks.roundTrip = true;
  await isolateLayer("operations");
  await page.click('#layer-controls [data-layer="state"]');
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  assert.deepEqual(await page.evaluate(() => graphDebug.layers.visible.slice().sort()), [
    "operations",
    "state",
  ]);
  await page.reload();
  await page.waitForFunction(() => graphDebug?.spatial?.perspective && !graphDebug.layoutBusy);
  assert.deepEqual(await page.evaluate(() => graphDebug.layers.visible.slice().sort()), [
    "operations",
    "state",
  ]);
  await page.click("#layered-toggle");
  assert.deepEqual(await page.evaluate(() => graphDebug.layers.visible.slice().sort()), [
    "operations",
    "state",
  ]);
  assert.equal(await page.locator("#legend-panel").getAttribute("data-mode"), "2D");
  await page.click("#show-all");
  assert.ok(
    (await page.locator('#layer-controls button[data-layer][aria-pressed="false"]').count()) === 0,
  );
  await page.click("#layered-toggle");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  checks.multiLayerPersistence = true;
  const beforeArrange = await page.evaluate(() => graphDebug.spatialPositions);
  await page.click("#arrange");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  await page.click("#undo-layout");
  assert.deepEqual(await page.evaluate(() => graphDebug.spatialPositions), beforeArrange);
  checks.spatialUndo = true;
  await isolateLayer("business");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  await page.waitForTimeout(250);
  const groupBefore = await page.evaluate(() => graphDebug.spatialPositions);
  const groupPoint = await page
    .locator('#semantic [data-node-id="publish"]')
    .evaluate((e) => ({ x: +e.dataset.screenX, y: +e.dataset.screenY }));
  checks.groupHit = await page.evaluate((p) => {
    const e = document.elementFromPoint(p.x, p.y);
    return {
      point: p,
      tag: e?.tagName,
      label: e?.closest("[data-spatial-label]")?.dataset.spatialLabel,
      text: e?.textContent?.slice(0, 80),
    };
  }, groupPoint);
  await page.mouse.move(groupPoint.x, groupPoint.y);
  await page.mouse.down();
  await page.mouse.move(groupPoint.x + 48, groupPoint.y + 16, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(200);
  const groupAfter = await page.evaluate(() => graphDebug.spatialPositions);
  const dx = groupAfter.publish.x - groupBefore.publish.x,
    dz = groupAfter.publish.z - groupBefore.publish.z;
  checks.movedAfterGroup = Object.keys(groupAfter).filter(
    (id) => JSON.stringify(groupBefore[id]) !== JSON.stringify(groupAfter[id]),
  );
  checks.pickedAfterGroup = await page
    .locator('#semantic [aria-pressed="true"]')
    .getAttribute("data-node-id");
  assert.ok(Math.hypot(dx, dz) > 1);
  assert.ok(Math.abs(groupAfter.load.x - groupBefore.load.x - dx) < 0.001);
  assert.ok(Math.abs(groupAfter.transaction.z - groupBefore.transaction.z - dz) < 0.001);
  checks.groupDrag = true;
  await page.click("#layers-all");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  await pick("publish");
  await page.waitForTimeout(180);
  const label = page.locator('[data-spatial-region="publish"]:visible').first();
  const labelBox = await label.boundingBox();
  assert.ok(labelBox, "Selected group label remains visible");
  const labelBefore = await page.evaluate(() => graphDebug.spatialPositions.publish);
  await page.mouse.move(labelBox.x + 5, labelBox.y + 5);
  await page.mouse.down();
  await page.mouse.move(labelBox.x + 35, labelBox.y + 15, { steps: 6 });
  await page.mouse.up();
  await page.waitForTimeout(150);
  assert.notDeepEqual(await page.evaluate(() => graphDebug.spatialPositions.publish), labelBefore);
  checks.labelDrag = true;
  await isolateLayer("business");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  await page.waitForTimeout(180);
  // Double-click actual perspective geometry, rather than a hidden semantic control.
  const collapsePoint = await page
    .locator('#semantic [data-node-id="publish"]')
    .evaluate((e) => ({ x: +e.dataset.screenX, y: +e.dataset.screenY }));
  await page.mouse.dblclick(collapsePoint.x, collapsePoint.y);
  await page.waitForFunction(
    () =>
      document.querySelector('#semantic [data-node-id="publish"]').getAttribute("aria-expanded") ===
      "false",
  );
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  await page.waitForTimeout(150);
  const expandPoint = await page
    .locator('#semantic [data-node-id="publish"]')
    .evaluate((e) => ({ x: +e.dataset.screenX, y: +e.dataset.screenY }));
  await page.mouse.dblclick(expandPoint.x, expandPoint.y);
  await page.waitForFunction(
    () =>
      document.querySelector('#semantic [data-node-id="publish"]').getAttribute("aria-expanded") ===
      "true",
  );
  checks.perspectiveExpansion = true;
  await page.click("#layers-all");
  await page.click("#layered-toggle");
  await page.click("#record-start");
  await request("/demo/run", { rollback: false });
  await page.click("#record-stop");
  await page.waitForFunction(() => document.querySelectorAll("#record-list option").length > 1);
  const record = await page.locator("#record-list option").last().getAttribute("value");
  await page.selectOption("#record-list", record);
  await page.waitForFunction(() => !document.querySelector("#replay").hidden);
  await page.click("#layered-toggle");
  await page.click("#replay-next");
  await shot("layers-replay");
  checks.replay = true;
  await page.selectOption("#record-list", "");
  await page.selectOption("#language", "zh-CN");
  await page.waitForURL(/lang=zh-CN/);
  await page.waitForFunction(() => window.graphDebug?.graph);
  assert.equal(await page.locator("#layered-toggle").innerText(), "3D");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(200);
  await isolateLayer("operations");
  await page.waitForTimeout(200);
  assert.ok(
    await page
      .locator("#semantic [data-node-id]")
      .evaluateAll((items) =>
        items.some(
          (e) =>
            +e.dataset.screenX > 0 &&
            +e.dataset.screenX < 390 &&
            +e.dataset.screenY > 300 &&
            +e.dataset.screenY < 760,
        ),
      ),
  );
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
  const bounds = await page.evaluate(() => ({
    legend: document.querySelector("#legend-panel").getBoundingClientRect().toJSON(),
    tools: document.querySelector(".view-tools").getBoundingClientRect().toJSON(),
  }));
  assert.ok(
    bounds.legend.bottom <= bounds.tools.top - 4,
    "The mobile legend must stay above the controls",
  );
  await shot("layers-mobile-zh");
  checks.languageAndMobile = true;
  const live = await request("/api/view");
  const commits = live.events.filter((e) => e.node === "transaction" && e.phase === "commit");
  assert.ok(commits.some((e) => e.outputs.committed === true));
  assert.ok(
    live.events.filter((e) => e.node === "save").every((e) => !("committed" in (e.outputs || {}))),
  );
  checks.actualTransactionOutcomes = true;
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify({ passed: true, checks, errors }, null, 2),
  );
  console.log(
    "PASS: layered viewer, quiet captures, accurate source ownership, business/state links, persistence, drag, replay and bilingual mobile.",
  );
} catch (error) {
  if (page) await shot("failure").catch(() => {});
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify({ passed: false, checks, errors, error: String(error.stack) }, null, 2),
  );
  throw error;
} finally {
  await browser?.close();
  server.kill();
  await writeFile(path.join(output, "server.log"), logs);
}
