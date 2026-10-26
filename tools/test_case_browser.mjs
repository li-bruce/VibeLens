/** Verify the published case in the real Pixi/Three.js viewer, in both locales. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const base = (process.env.BO_SITE_URL || "http://127.0.0.1:8897").replace(/\/$/, "");
const output = path.resolve(process.env.BO_CASE_BROWSER_EVIDENCE || ".validation/case-browser");
await mkdir(output, { recursive: true });
const python =
  process.env.BO_PYTHON ||
  path.resolve(".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const server = process.env.BO_SITE_URL
  ? null
  : spawn(
      python,
      ["-B", "-m", "http.server", "8897", "--bind", "127.0.0.1", "--directory", "docs/site"],
      { windowsHide: true, stdio: "ignore" },
    );
let browser;
const errors = [],
  receipts = [];
try {
  for (let i = 0; i < 60; i++) {
    try {
      if ((await fetch(base)).ok) break;
    } catch {
      /* Startup. */
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  browser = await chromium.launch({
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
    ...(process.env.BO_BROWSER_EXECUTABLE
      ? { executablePath: process.env.BO_BROWSER_EXECUTABLE }
      : {}),
  });
  const page = await browser.newPage({ viewport: { width: 1536, height: 1100 } });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("response", (response) => {
    if (response.status() >= 400 && !response.url().endsWith("favicon.ico"))
      errors.push(response.status() + " " + response.url());
  });
  async function graph() {
    const frame = page.frame({ url: /viewer\/index.html/ });
    assert.ok(frame);
    await frame.waitForFunction(() => window.graphDebug?.graph?.boxes.length > 0);
    return frame;
  }
  for (const language of ["en", "zh-CN"]) {
    await page.goto(base + "/demo.html?lang=" + language);
    await page.waitForFunction(
      () => document.querySelector("#chapter-title").textContent.length > 5,
    );
    let frame = await graph();
    await frame.waitForFunction(
      () => document.querySelector("#analysis-view").value === "business",
    );
    assert.equal(await page.getAttribute("html", "lang"), language);
    assert.equal(await page.locator("[data-chapter]").count(), 5);
    await page
      .locator(".case-desk")
      .screenshot({ path: path.join(output, language + "-01-confirm.png") });
    await page.click('[data-chapter="1"]');
    await frame.waitForFunction(
      () => document.querySelector("#analysis-view").value === "overview",
    );
    const eventCount = await frame.evaluate(
      async () => (await (await fetch("/api/view")).json()).events.length,
    );
    await frame.selectOption("#record-list", { index: 1 });
    await frame.waitForFunction(() => !document.querySelector("#replay").hidden);
    await frame.click("#replay-next");
    const position = await frame.locator("#replay-position").textContent();
    assert.ok(position.length > 0);
    await frame.click("#replay-live");
    await frame.waitForFunction((count) => graphDebug.view.events.length === count, eventCount);
    assert.equal(
      await frame.evaluate(async () => (await (await fetch("/api/view")).json()).events.length),
      eventCount,
    );
    await page.click('[data-chapter="2"]');
    await page.waitForFunction(() =>
      document.querySelector("#case-evidence").textContent.includes("allowed"),
    );
    await frame.waitForFunction(
      () => document.querySelector("#analysis-view").value === "permission",
    );
    await frame.waitForFunction(
      () =>
        graphDebug.view.replay?.event?.node === "review-policy" &&
        graphDebug.view.replay.event.phase === "return",
    );
    assert.equal(
      await frame.evaluate(() => graphDebug.view.replay.event.outputs.verdict),
      "allowed",
    );
    await page
      .locator(".case-desk")
      .screenshot({ path: path.join(output, language + "-02-find.png") });
    await page.click("#case-layers");
    await frame.waitForFunction(
      () => document.querySelector("#analysis-view").value === "overview",
    );
    await frame.click("#expand");
    await frame.waitForFunction(() => !graphDebug.layoutBusy);
    await page.click("#case-3d");
    await frame.waitForFunction(
      () =>
        graphDebug.spatial?.perspective &&
        !graphDebug.layoutBusy &&
        graphDebug.graph.boxes.length > 0,
      { timeout: 30000 },
    );
    const inventory = await frame.evaluate(async () => {
      const { layerOf } = await import("./graph-layers.js");
      return {
        layers: [...new Set(graphDebug.graph.boxes.map((box) => layerOf(box.node)))],
        planes: graphDebug.spatial.layerPlanes,
        nodes: graphDebug.graph.boxes.length,
        edges: graphDebug.graph.edges.length,
        perspective: graphDebug.spatial.perspective,
      };
    });
    assert.equal(inventory.layers.length, 8, JSON.stringify(inventory));
    assert.ok(inventory.edges > 20);
    const area = await frame.locator("#viewport").boundingBox();
    await page.mouse.move(area.x + area.width * 0.24, area.y + area.height * 0.83);
    await page.mouse.down();
    await page.mouse.move(area.x + area.width * 0.34, area.y + area.height * 0.6, { steps: 16 });
    await page.mouse.up();
    await page.waitForTimeout(650);
    await page
      .locator(".case-desk")
      .screenshot({ path: path.join(output, language + "-03-all-layers-3d.png") });
    await page.click("#case-2d");
    await frame.waitForFunction(() => !graphDebug.layers.enabled && !graphDebug.layoutBusy);
    await page
      .locator(".case-desk")
      .screenshot({ path: path.join(output, language + "-04-all-layers-2d.png") });
    await page.click('[data-chapter="3"]');
    await page.waitForFunction(() => document.querySelector("#case-graph").src.includes("case=2"));
    frame = await graph();
    await page.waitForFunction(() =>
      document.querySelector("#case-evidence").textContent.includes("stale_review"),
    );
    await page.click('[data-chapter="4"]');
    await page
      .locator(".case-desk")
      .screenshot({ path: path.join(output, language + "-05-retest.png") });
    assert.ok(
      (await page.locator("#case-source").textContent()).includes(
        "reviewed_version != current_version",
      ),
    );
    for (const view of [
      "api",
      "business",
      "states",
      "permission",
      "functions",
      "data-operations",
      "database",
      "code",
    ]) {
      await page.click('[data-layer="' + view + '"]');
      await frame.waitForFunction(
        (view) =>
          document.querySelector("#analysis-view").value === view &&
          graphDebug.graph.boxes.length > 0,
        view,
      );
      assert.ok(
        (await frame.locator("#semantic-edges [data-edge-id]").count()) ||
          (await frame.evaluate(() => graphDebug.graph.edges.length > 0)),
        "Layer lost its relations: " + view,
      );
    }
    await page.setViewportSize({ width: 390, height: 844 });
    assert.ok(
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2),
      "Page overflows on mobile",
    );
    await page.screenshot({ path: path.join(output, language + "-mobile.png"), fullPage: true });
    await page.setViewportSize({ width: 1536, height: 1100 });
    receipts.push({ language, chapters: 5, inventory, recording_replay: true, mobile: true });
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(base + "/demo.html?lang=en");
  await graph();
  assert.equal(errors.length, 0, errors.join("\n"));
  await writeFile(
    path.join(output, "summary.json"),
    JSON.stringify({ passed: true, receipts, errors }, null, 2),
  );
  console.log(JSON.stringify({ passed: true, output, receipts }));
} finally {
  await browser?.close();
  server?.kill();
  await writeFile(path.join(output, "errors.json"), JSON.stringify(errors, null, 2));
}
