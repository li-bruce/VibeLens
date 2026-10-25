/** Synthetic rendering benchmark, separate from real-business runtime acceptance. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("../", import.meta.url));
const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(
  process.env.BO_BROWSER_EVIDENCE || "docs/review/spatial-graph/performance",
);
await mkdir(output, { recursive: true });
const port = process.env.BO_BROWSER_PORT || "8894",
  base = `http://127.0.0.1:${port}`;
const server = spawn(
  process.env.BO_PYTHON ||
    path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python"),
  ["-B", "-X", "utf8", "tools/database_demo.py", "--port", port],
  { cwd: root, windowsHide: true },
);
let logs = "",
  browser,
  page;
server.stdout.on("data", (data) => (logs += data));
server.stderr.on("data", (data) => (logs += data));
const errors = [],
  results = [];
try {
  for (let i = 0; i < 100; i++) {
    try {
      if ((await fetch(base + "/api/bo/health")).ok) break;
    } catch {}
    if (server.exitCode !== null) throw Error(logs);
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (error) => errors.push(error.stack || String(error)));
  await page.goto(base + "/graph?lang=en");
  await page.waitForFunction(() => window.graphDebug?.graph);
  for (const count of process.env.BO_SPATIAL_INTEGRATED_ONLY ? [] : [1000, 4000]) {
    const sample = await page.evaluate(async (count) => {
      const { SpatialRenderer } = await import("/spatial-renderer.js");
      const host = document.createElement("div");
      Object.assign(host.style, {
        position: "fixed",
        inset: "0",
        zIndex: "100",
        background: "#f6f8fa",
      });
      document.body.append(host);
      let viewportReads = 0;
      const readWidth = Object.getOwnPropertyDescriptor(Element.prototype, "clientWidth").get;
      const readHeight = Object.getOwnPropertyDescriptor(Element.prototype, "clientHeight").get;
      Object.defineProperties(host, {
        clientWidth: {
          get() {
            viewportReads++;
            return readWidth.call(host);
          },
        },
        clientHeight: {
          get() {
            viewportReads++;
            return readHeight.call(host);
          },
        },
      });
      const nodes = Array.from({ length: count }, (_, i) => ({
        id: "bench:" + i,
        kind: "function",
        layer: i % 3 === 0 ? "business" : i % 3 === 1 ? "state" : "execution",
        label: "Operation " + i,
      }));
      const boxes = nodes.map((node, i) => ({
        id: node.id,
        node,
        type: i % 3 === 0 ? "business" : i % 3 === 1 ? "state" : "function",
        state: "declared",
        rows: [],
        x: 0,
        y: 0,
        w: 100,
        h: 100,
      }));
      const edges = nodes.flatMap((node, i) =>
        Array.from({ length: 4 }, (_, offset) => ({
          id: `e:${i}:${offset}`,
          from: node.id,
          to: nodes[(i + offset * 23 + 1) % count].id,
          type: offset % 2 ? "call" : "guard",
          members: [],
        })),
      );
      const graph = {
        boxes,
        all: new Map(nodes.map((n) => [n.id, n])),
        byId: new Map(boxes.map((b) => [b.id, b])),
        edges,
        regions: [],
      };
      const presentation = {
        glyphs: new Set(nodes.map((node) => node.id)),
        regions: new Set(),
        edges,
      };
      const emptyFocus = { nodes: new Set(), edges: new Set(), regions: new Set(), active: false };
      const preferences = { annotations: {}, spatial: {} };
      const renderer = new SpatialRenderer(host);
      const input = {
        graph,
        presentation,
        preferences,
        selected: null,
        focusContext: emptyFocus,
        settings: { enabled: true, gap: 240, only: "all", projections: true },
        scope: "bench:" + count,
        boTransfers: new Map(),
      };
      const started = performance.now();
      renderer.update(input);
      renderer.setVisible(true);
      renderer.fit();
      let heartbeats = 0,
        worstDelay = 0,
        last = performance.now();
      const pulse = setInterval(() => {
        const now = performance.now();
        worstDelay = Math.max(worstDelay, now - last - 16);
        last = now;
        heartbeats++;
      }, 16);
      const deadline = performance.now() + 30000;
      while (renderer.busy && performance.now() < deadline)
        await new Promise((resolve) => setTimeout(resolve, 25));
      if (renderer.busy) throw Error("Spatial worker did not settle within 30 seconds");
      const settledMs = performance.now() - started;
      viewportReads = 0;
      for (let i = 0; i < 35; i++) {
        renderer.camera.position.x += 5;
        renderer.controls.update();
        renderer.schedule();
        await new Promise((resolve) => setTimeout(resolve, 16));
      }
      const before = renderer.diagnostics;
      const selectionStart = performance.now();
      renderer.update({
        ...input,
        selected: nodes[0].id,
        focusContext: { ...emptyFocus, active: true, nodes: new Set([nodes[0].id]) },
      });
      const selectionMs = performance.now() - selectionStart;
      await new Promise((resolve) => setTimeout(resolve, 150));
      const after = renderer.diagnostics;
      const cameraViewportReads = viewportReads,
        routingChecks = [];
      for (const routing of ["straight", "orthogonal", "bus"]) {
        const start = performance.now();
        renderer.update({ ...input, routing });
        const rebuildMs = performance.now() - start;
        await new Promise((resolve) => setTimeout(resolve, 70));
        const finite = [...renderer.curves.values()].every((curve) =>
          curve.getPoints(4).every((p) => [p.x, p.y, p.z].every(Number.isFinite)),
        );
        routingChecks.push({
          routing,
          rebuildMs,
          finite,
          drawCalls: renderer.diagnostics.drawCalls,
          geometries: renderer.diagnostics.geometries,
        });
      }
      // No observer traffic is made by the renderer itself.
      const gl = renderer.renderer.getContext(),
        ext = gl.getExtension("WEBGL_debug_renderer_info");
      const gpu = ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : "unavailable";
      clearInterval(pulse);
      window.benchmarkRenderer?.dispose();
      window.benchmarkRenderer = renderer;
      window.benchmarkHost?.remove();
      window.benchmarkHost = host;
      return {
        count,
        edges: edges.length,
        settledMs,
        heartbeats,
        worstDelay,
        selectionMs,
        viewportReads: cameraViewportReads,
        routingChecks,
        before,
        after,
        gpu,
      };
    }, count);
    results.push(sample);
    assert.ok(
      sample.routingChecks.every((check) => check.finite && check.drawCalls < 35),
      "Every routing style keeps finite batched geometry",
    );
    assert.ok(sample.heartbeats > 5, "Layout must leave the browser responsive");
    assert.ok(sample.after.labels <= 300, "DOM labels must remain bounded");
    assert.ok(
      sample.after.drawCalls < 35,
      "Instances and batched edges must bound draw submissions",
    );
    assert.equal(
      sample.after.geometries,
      sample.before.geometries,
      "Selection must reuse GPU geometry",
    );
    assert.ok(sample.selectionMs < 250, "Selection feedback exceeded the benchmark budget");
    assert.ok(
      sample.viewportReads < 5,
      "Camera frames repeatedly read layout dimensions while writing labels",
    );
    await page.screenshot({ path: path.join(output, `graph-${count}.png`) });
  }
  // Exercise the full coordinator and accessible controls as well as raw GPU drawing.
  await page.close();
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const live = await (await fetch(base + "/api/view")).json();
  const prefs = await (await fetch(base + "/api/preferences")).json();
  const nodes = Array.from({ length: 1000 }, (_, i) => ({
    id: `integrated:${i}`,
    kind: "function",
    label: `Function ${i}`,
  }));
  const edges = nodes.flatMap((node, i) =>
    Array.from({ length: 4 }, (_, j) => ({
      id: `integrated-edge:${i}:${j}`,
      from: node.id,
      to: nodes[(i + j * 17 + 1) % nodes.length].id,
      type: j % 2 ? "data" : "call",
    })),
  );
  const sample = {
    ...live,
    model: {
      ...live.model,
      nodes: [...live.model.nodes, ...nodes],
      edges: [...live.model.edges, ...edges],
    },
  };
  prefs.entries[`business-observer.layout.v2:${prefs.project_id}:analysis`] = JSON.stringify({
    selected: "overview",
    layers: { enabled: true, camera: "angled", only: "all", gap: 260 },
    custom: [],
    overrides: {},
  });
  await page.route("**/api/view*", (route) => route.fulfill({ json: sample }));
  await page.route("**/api/preferences", (route) => route.fulfill({ json: prefs }));
  page.on("pageerror", (error) => errors.push(error.stack || String(error)));
  const integratedStart = Date.now();
  await page.goto(base + "/graph?lang=en");
  await page.waitForFunction(
    () =>
      window.graphDebug?.spatial?.frames > 0 &&
      graphDebug.graph.boxes.length > 1000 &&
      !graphDebug.layoutBusy,
    {},
    { timeout: 30000 },
  );
  const integrated = await page.evaluate(() => ({
    readyMs: performance.now(),
    nodes: document.querySelectorAll("#semantic [data-node-id]").length,
    edges: document.querySelectorAll("#semantic-edges [data-edge-id]").length,
    metrics: graphDebug.spatial,
  }));
  integrated.wallMs = Date.now() - integratedStart;
  assert.ok(integrated.edges >= 4000);
  const selectStart = Date.now();
  await page.locator('#semantic [data-node-id="integrated:0"]').evaluate((el) => el.click());
  await page.waitForFunction(
    () =>
      document
        .querySelector('#semantic [data-node-id="integrated:0"]')
        .getAttribute("aria-pressed") === "true",
  );
  integrated.selectionRoundTripMs = Date.now() - selectStart;
  assert.ok(
    integrated.selectionRoundTripMs < 1000,
    "Full UI selection did not respond within one second",
  );
  await page.mouse.move(60, 480);
  await page.mouse.down();
  await page.mouse.move(210, 530, { steps: 30 });
  await page.mouse.up();
  await page.waitForTimeout(400);
  integrated.afterOrbit = await page.evaluate(() => graphDebug.spatial);
  results.push({ integrated });
  await page.screenshot({ path: path.join(output, "full-viewer-1000.png") });
  // Native page teardown includes pagehide followed by visibilitychange.
  await page.close();
  page = null;
  await new Promise((resolve) => setTimeout(resolve, 120));
  assert.deepEqual(errors, []);
  console.log(
    "PASS: worker responsiveness, batched 3D rendering, bounded labels and selection GPU reuse.",
  );
} catch (error) {
  errors.push(String(error.stack));
  if (page) {
    await page.screenshot({ path: path.join(output, "failure.png") }).catch(() => {});
    const debug = await page
      .evaluate(() => ({
        nodes: window.graphDebug?.graph?.boxes.length,
        layers: window.graphDebug?.layers,
        spatial: window.graphDebug?.spatial,
        layout: document.getElementById("layout-status")?.textContent,
        connection: document.getElementById("connection")?.textContent,
      }))
      .catch(() => null);
    await writeFile(path.join(output, "failure-debug.json"), JSON.stringify(debug, null, 2));
  }
  throw error;
} finally {
  await writeFile(path.join(output, "results.json"), JSON.stringify({ results, errors }, null, 2));
  await browser?.close();
  server.kill();
  await writeFile(path.join(output, "server.log"), logs);
}
