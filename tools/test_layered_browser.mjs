/** Real viewer acceptance: projection, inverse drag, source provenance and replay. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
const { chromium } = createRequire(import.meta.url)("playwright");
const root = fileURLToPath(new URL("../", import.meta.url));
const output = path.resolve(process.env.BO_BROWSER_EVIDENCE || "docs/review/layered-graph/browser");
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
  await shot("capture-owner");
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
  await page.waitForFunction(() => graphDebug.displayGraph.layered);
  const planes = await page.evaluate(() => graphDebug.displayGraph.planes.map((p) => p.id));
  assert.ok(
    planes.includes("business") &&
      planes.includes("execution") &&
      planes.includes("state") &&
      planes.includes("data"),
  );
  checks.planes = planes;
  await shot("layers-angled");
  await page.selectOption("#layer-camera", "side");
  await page.selectOption("#layer-only", "execution");
  assert.ok(
    await page.evaluate(() => graphDebug.displayGraph.boxes.every((b) => b.layer === "execution")),
  );
  await page.selectOption("#layer-only", "all");
  await page.click("#layered-toggle");
  assert.deepEqual(
    await page.evaluate(() => graphDebug.graph.boxes.map((b) => [b.id, b.x, b.y])),
    before,
  );
  await page.click("#layered-toggle");
  await page.selectOption("#layer-camera", "front");
  const pos = await page
    .locator('#semantic [data-node-id="load"]')
    .evaluate((e) => ({ x: +e.dataset.screenX, y: +e.dataset.screenY }));
  await page.mouse.move(pos.x, pos.y);
  await page.mouse.down();
  await page.mouse.move(pos.x + 45, pos.y + 25, { steps: 8 });
  await page.mouse.up();
  const after = await page.evaluate(() => ({
    positions: graphDebug.graph.boxes.map((b) => [b.id, b.x, b.y]),
    layers: graphDebug.layers,
  }));
  assert.notDeepEqual(
    after.positions,
    before,
    "Dragging in layers must update canonical positions",
  );
  await page.waitForTimeout(500);
  await page.reload();
  await page.waitForFunction(() => graphDebug?.displayGraph?.layered === true);
  assert.equal(await page.locator("#layer-camera").inputValue(), "front");
  assert.deepEqual(
    await page.evaluate(() => graphDebug.graph.boxes.map((b) => [b.id, b.x, b.y])),
    after.positions,
  );
  checks.roundTrip = true;
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
  assert.equal(await page.locator("#layered-toggle").innerText(), "分层");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(200);
  await page.selectOption("#layer-only", "execution");
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
  await shot("layers-mobile-zh");
  checks.languageAndMobile = true;
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
