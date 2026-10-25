/** Browser acceptance of semantic planar clustering, fixed pins and solid objects. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const output = process.env.BO_BROWSER_EVIDENCE || "docs/review/spatial-objects/clusters";
await mkdir(output, { recursive: true });
const base = "http://127.0.0.1:8896";
const server = spawn(
  ".venv/Scripts/python.exe",
  ["-B", "-X", "utf8", "tools/database_demo.py", "--port", "8896"],
  { windowsHide: true },
);
let logs = "",
  browser,
  page;
const errors = [];
server.stdout.on("data", (d) => (logs += d));
server.stderr.on("data", (d) => (logs += d));
const result = {};
try {
  for (let i = 0; i < 100; i++) {
    try {
      if ((await fetch(base + "/api/bo/health")).ok) break;
    } catch {}
    if (server.exitCode !== null) throw Error(logs);
    await new Promise((r) => setTimeout(r, 200));
  }
  const live = await (await fetch(base + "/api/view")).json();
  const nodes = Array.from({ length: 36 }, (_, i) => ({
    id: "cluster:" + i,
    kind: ["function", "decision", "data"][Math.floor(i / 12)],
    label: ["Load", "Check", "Value"][Math.floor(i / 12)] + " " + i,
  }));
  const edges = nodes.flatMap((n, i) =>
    i % 12 < 11 ? [{ id: "internal:" + i, from: n.id, to: nodes[i + 1].id, type: "call" }] : [],
  );
  edges.push(
    { id: "bridge:one", from: "cluster:0", to: "cluster:12", type: "data" },
    { id: "bridge:two", from: "cluster:1", to: "cluster:24", type: "guard" },
  );
  const sample = { ...live, model: { ...live.model, nodes, edges, capture: [] } };
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.route("**/api/view*", (r) => r.fulfill({ json: sample }));
  await page.goto(base + "/graph?lang=en");
  await page.waitForFunction(
    () => window.graphDebug?.graph?.boxes.length >= 36 && !graphDebug.layoutBusy,
  );
  await page.click("#arrange");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  result.positions = await page.evaluate(() =>
    graphDebug.graph.boxes
      .filter((n) => n.id.startsWith("cluster:"))
      .map((n) => ({ id: n.id, type: n.type, x: n.x, y: n.y })),
  );
  const groups = ["function", "decision", "data"];
  const centers = Object.fromEntries(
    groups.map((type) => {
      const a = result.positions.filter((n) => n.type === type);
      return [
        type,
        {
          x: a.reduce((s, n) => s + n.x, 0) / a.length,
          y: a.reduce((s, n) => s + n.y, 0) / a.length,
        },
      ];
    }),
  );
  for (const n of result.positions) {
    const distance = (c) => Math.hypot(n.x - c.x, n.y - c.y);
    assert.ok(
      distance(centers[n.type]) <
        Math.min(...groups.filter((t) => t !== n.type).map((t) => distance(centers[t]))),
      "Actual 2D layout keeps each type near its own cluster",
    );
  }
  await page.screenshot({ path: path.join(output, "clusters-2d.png") });
  await page.locator('#semantic [data-node-id="cluster:4"]').evaluate((e) => e.click());
  await page.click("#selection-menu");
  await page.click("#pin");
  const pin = await page.evaluate(() => {
    const n = graphDebug.graph.byId.get("cluster:4");
    return { x: n.x, y: n.y };
  });
  await page.click("#arrange");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  assert.deepEqual(
    await page.evaluate(() => {
      const n = graphDebug.graph.byId.get("cluster:4");
      return { x: n.x, y: n.y };
    }),
    pin,
    "Explicit pins remain exact after cluster layout",
  );
  await page.click("#layered-toggle");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  await page.mouse.move(950, 580);
  await page.mouse.down();
  await page.mouse.move(1100, 660, { steps: 12 });
  await page.mouse.up();
  await page.waitForTimeout(250);
  await page.screenshot({ path: path.join(output, "solid-objects-3d.png") });
  result.workerPerformance = await page.evaluate(async () => {
    let pulses = 0;
    const timer = setInterval(() => pulses++, 16),
      started = performance.now();
    const positions = await new Promise((resolve, reject) => {
      const worker = new Worker("/cluster-worker.js", { type: "module" });
      const timeout = setTimeout(() => {
        worker.terminate();
        reject(Error("4k cluster worker exceeded 30s"));
      }, 30000);
      worker.onmessage = ({ data }) => {
        clearTimeout(timeout);
        worker.terminate();
        data.error ? reject(Error(data.error)) : resolve(data.positions);
      };
      worker.onerror = (e) => {
        clearTimeout(timeout);
        worker.terminate();
        reject(Error(e.message));
      };
      worker.postMessage({
        units: Array.from({ length: 4000 }, (_, i) => ({
          id: "large:" + i,
          type: "type:" + (i % 8),
          radius: 25,
        })),
        edges: Array.from({ length: 4000 }, (_, i) => ({
          from: "large:" + i,
          to: "large:" + ((i + 1) % 4000),
        })),
      });
    });
    clearInterval(timer);
    return {
      nodes: positions.length,
      elapsedMs: performance.now() - started,
      heartbeats: pulses,
      finite: positions.every((p) => Number.isFinite(p.x) && Number.isFinite(p.y)),
    };
  });
  assert.equal(result.workerPerformance.nodes, 4000);
  assert.ok(
    result.workerPerformance.finite && result.workerPerformance.heartbeats > 0,
    "Large planar clustering leaves the UI event loop responsive",
  );
  result.pinned = true;
  result.clusters = centers;
  result.spatial = await page.evaluate(() => graphDebug.spatial);
  assert.deepEqual(errors, []);
  result.passed = true;
  console.log(
    "PASS: actual planar type clusters, cross-type bridges, exact pins and real 3D objects.",
  );
} catch (error) {
  result.error = String(error.stack);
  await page?.screenshot({ path: path.join(output, "failure.png") }).catch(() => {});
  throw error;
} finally {
  await writeFile(
    path.join(output, "results.json"),
    JSON.stringify({ ...result, errors }, null, 2),
  );
  await browser?.close();
  server.kill();
  await writeFile(path.join(output, "server.log"), logs);
}
