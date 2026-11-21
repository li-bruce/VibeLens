/** Exercise the native multi-network story without generating application facts.
 * Both languages use real recorded identities, native 3D rendering and the
 * canonical full viewer. Preserve screenshots and failures for review.
 */
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { startSite } from "./site_browser_fixture.mjs";
const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(process.env.BO_FOREST_EVIDENCE || ".validation/forest-browser");
await fs.mkdir(output, { recursive: true });
const server = await startSite(),
  report = { valid: false, cases: [] };
let browser;
try {
  browser = await chromium.launch({
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
    ...(process.env.BO_BROWSER_EXECUTABLE
      ? { executablePath: process.env.BO_BROWSER_EXECUTABLE }
      : {}),
  });
  for (const language of ["en", "zh-CN"]) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage(),
      errors = [],
      archives = [];
    page.setDefaultTimeout(45000);
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("request", (request) => {
      if (/forest-data\/.+\.gz/.test(request.url())) archives.push(request.url());
    });
    const item = { language, errors, networks: [] };
    report.cases.push(item);
    try {
      await page.goto(`${server.url}/demo.html?lang=${language}#foundation`, {
        waitUntil: "networkidle",
      });
      await page.waitForFunction(
        () => document.querySelector("#forest-graph").dataset.ready === "true",
      );
      const choose = async (id) => {
        await page.locator(`.forest-stages a[href="#${id}"]`).click();
        await page
          .locator(`#${id}`)
          .evaluate((node) => node.scrollIntoView({ behavior: "instant", block: "start" }));
        await page.waitForFunction((id) => document.body.dataset.forestScene === id, id);
      };
      await choose("foundation");
      for (let i = 0; i < 5; i++) await page.locator("#forest-next").click();
      assert.equal(await page.locator("#foundation .forest-turn").count(), 6);
      for (const view of ["business", "states", "rules"]) {
        await page.locator(`[data-forest-view="${view}"]`).click();
        const choices = await page
          .locator("#forest-network option")
          .evaluateAll((nodes) => nodes.map((node) => node.value));
        for (const id of choices) {
          await page.locator("#forest-network").selectOption(id);
          const count = await page.locator(".prepared-node").count();
          assert(count > 0);
          item.networks.push({ view, id, count });
        }
      }
      assert.equal(item.networks.filter((item) => item.view === "states").length, 4);
      await page.locator('[data-forest-view="states"]').click();
      await page.locator("#forest-network").selectOption("download_task");
      const initialIds = await page
        .locator(".prepared-node")
        .evaluateAll((nodes) => nodes.map((node) => node.dataset.nodeId));
      assert.equal(initialIds.length, 4);
      await page.screenshot({ path: path.join(output, `${language}-foundation.png`) });
      await choose("run");
      const maximum = Number(await page.locator("#forest-position").getAttribute("max"));
      assert(maximum > 0);
      await page.locator("#forest-position").fill(String(maximum));
      await page.locator("#forest-position").dispatchEvent("input");
      assert((await page.locator("[data-transfer]").count()) > 0);
      assert((await page.locator(".prepared-node.is-active").count()) > 0);
      await page.locator("#forest-play").click();
      const event = await page.locator("#forest-graph").getAttribute("data-event-id");
      await page.waitForFunction(
        (before) => document.querySelector("#forest-graph").dataset.eventId !== before,
        event,
      );
      await page.locator("#forest-play").click();
      await page.screenshot({ path: path.join(output, `${language}-replay.png`) });
      await page.locator("#forest-3d").click();
      await page.waitForFunction(
        () => document.querySelector("#forest-graph").dataset.mode === "3d",
      );
      const camera = await page.locator("#forest-graph").getAttribute("data-camera");
      const bounds = await page.locator(".prepared-webgl").boundingBox();
      const x = bounds.x + 35,
        y = bounds.y + 40;
      await page.mouse.move(x, y);
      await page.mouse.down();
      await page.mouse.move(x + 90, y + 45, { steps: 12 });
      await page.mouse.up();
      await page.waitForFunction(
        (old) => document.querySelector("#forest-graph").dataset.camera !== old,
        camera,
      );
      await page.screenshot({ path: path.join(output, `${language}-3d.png`) });
      await page.locator("#forest-2d").click();
      await choose("iterate");
      const updatedIds = await page
        .locator(".prepared-node")
        .evaluateAll((nodes) => nodes.map((node) => node.dataset.nodeId));
      assert.equal(updatedIds.length, 5);
      assert(initialIds.every((id) => updatedIds.includes(id)));
      assert(updatedIds.includes("native_state:download_task:cancelled"));
      await page.screenshot({ path: path.join(output, `${language}-iteration.png`) });
      await choose("verify");
      assert.equal(archives.length, 0, "All six stages use only prepared data");
      await choose("drill");
      // This is the cross-layer slice, not merely a tilted state diagram.
      await page.locator("#forest-3d").click();
      await page.waitForFunction(
        () => document.querySelector("#forest-graph").dataset.mode === "3d",
      );
      await page.screenshot({ path: path.join(output, `${language}-layers.png`) });
      await page.locator("#forest-2d").click();
      await page.locator('.prepared-node[data-node-id="request_download"]').dblclick();
      await page.locator("#forest-detail button").last().click();
      await page.locator("#forest-detail pre").waitFor();
      assert((await page.locator("#forest-detail pre").textContent()).includes("requestDownload"));
      assert.equal(await page.locator("body").getAttribute("data-forest-scene"), "drill");
      assert(
        await page.locator("#forest-detail pre").evaluate((pre) => {
          const mark = pre.querySelector("mark").getBoundingClientRect();
          const pane = pre.getBoundingClientRect();
          return mark.top >= pane.top && mark.bottom < pane.top + pane.height * 0.7;
        }),
        "The declaration leaves room for its body without scrolling the story",
      );
      assert.equal(archives.length, 1);
      await page.screenshot({ path: path.join(output, `${language}-source.png`) });
      const popupPromise = page.waitForEvent("popup");
      await page.locator("#forest-full").click();
      const full = await popupPromise;
      full.on("pageerror", (error) => errors.push(error.message));
      await full.waitForFunction(
        () => window.graphDebug?.graph && document.body.dataset.forestRecording,
        null,
        { timeout: 60000 },
      );
      assert.equal(await full.locator("html").getAttribute("lang"), language);
      const recordingId = await full.locator("body").getAttribute("data-forest-recording");
      await full
        .locator(`#record-list option[value="${recordingId}"]`)
        .waitFor({ state: "attached" });
      await full.locator("#record-list").selectOption(recordingId);
      await full.waitForFunction((id) => graphDebug.view?.replay?.id === id, recordingId);
      await full.locator("#analysis-view").selectOption("business");
      await full.waitForFunction(
        () =>
          graphDebug.presentation?.glyphs?.size > 0 &&
          !graphDebug.layoutBusy &&
          !graphDebug.geometryBusy,
      );
      await full.locator("#fit").click();
      await full.waitForFunction(() => !graphDebug.geometryBusy);
      assert(
        !/Cannot read|undefined|TypeError/.test(await full.locator("body").innerText()),
        "No caught transport failure in the status bar",
      );
      await full.screenshot({ path: path.join(output, `${language}-full.png`) });
      item.full_recording = await full.locator("body").getAttribute("data-forest-recording");
      item.no_eager_archive = true;
      item.actual_motion = true;
      item.source = true;
      await full.close();
      assert.deepEqual(errors, []);
    } catch (error) {
      item.failure = error.stack;
      await page.screenshot({ path: path.join(output, `${language}-failed.png`) });
      throw error;
    } finally {
      await context.close();
    }
  }
  // A delayed full archive must leave the parent story usable. The retry uses
  // the actual HTTP response and lossless archive, without fabricated events.
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  let release,
    started,
    fail = true;
  const held = new Promise((resolve) => (release = resolve));
  const requested = new Promise((resolve) => (started = resolve));
  await context.route("**/forest-data/initial.json.gz", async (route) => {
    started();
    await held;
    if (fail) {
      fail = false;
      await route.fulfill({ status: 503, body: "Unavailable" });
    } else await route.continue();
  });
  try {
    await page.goto(`${server.url}/demo.html?lang=zh-CN#foundation`, { waitUntil: "networkidle" });
    const popupPromise = page.waitForEvent("popup");
    await page.locator("#forest-full").click();
    const full = await popupPromise;
    await requested;
    await full.locator("#forest-viewer-loading").waitFor();
    await page.locator('.forest-stages a[href="#iterate"]').click();
    await page.waitForFunction(() => document.body.dataset.forestScene === "iterate");
    assert.equal(await page.locator(".prepared-node").count(), 5);
    release();
    await full.locator("#forest-viewer-loading button").waitFor();
    await full.screenshot({ path: path.join(output, "archive-retry.png") });
    await full.locator("#forest-viewer-loading button").click();
    await full.waitForFunction(() => document.body.dataset.forestRecording);
    await full.locator("#forest-viewer-loading").waitFor({ state: "detached" });
    assert.equal(await full.locator("#forest-viewer-loading").count(), 0);
    report.cases.push({ archive_delay_parent_usable: true, actual_http_failure_retry: true });
  } finally {
    release();
    await context.close();
  }
  report.valid = true;
} catch (error) {
  report.error = error.stack;
  process.exitCode = 1;
} finally {
  await browser?.close();
  server.close();
  await fs.writeFile(path.join(output, "result.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
}
