/** Exercise the shared replay dock using unchanged recorded facts and real assets.
 * Preferences stay in the HTTP fixture; neither business code nor recorded facts
 * are mutated. An external recording can repeat the check on a retained trial.
 */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { serveRecording } from "./recording_browser_fixture.mjs";
import { observeResources } from "./browser_resource_diagnostics.mjs";

const out = path.resolve(
  process.env.BO_REPLAY_WORKSPACE_EVIDENCE || ".validation/replay-workspace",
);
const recordingPath = path.resolve(
  process.env.BO_REPLAY_WORKSPACE_RECORDING || "docs/review/spatial-workspace/replay-fixture.json",
);
await mkdir(out, { recursive: true });
const fixture = await serveRecording(recordingPath, {
  assetsPath: process.env.BO_REPLAY_WORKSPACE_ASSETS,
});
const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");
const result = {
  passed: false,
  recording: fixture.recording.id,
  source_sha256: digest(fixture.bytes),
  checks: [],
  resources: [],
  negative_control: null,
};
let browser, page;
const ready = () =>
  page.waitForFunction(
    () =>
      window.graphDebug?.graph &&
      !graphDebug.sourceBusy &&
      !graphDebug.layoutBusy &&
      !graphDebug.geometryBusy,
  );

/** Actual bounds and hit tests catch overlay regressions in either renderer. */
async function measure() {
  return page.evaluate(() => {
    const rect = (selector) => {
      const r = document.querySelector(selector).getBoundingClientRect();
      return { x: r.x, y: r.y, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
    };
    const replay = rect("#replay"),
      graph = rect("#viewport"),
      timeline = rect("#recording-timeline");
    const overlap = (a, b) =>
      Math.max(0, Math.min(a.right, b.right) - Math.max(a.x, b.x)) *
      Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.y, b.y));
    const controls = [
      "#replay-play",
      "#replay-range",
      "#replay-events",
      "#replay-live",
      "#replay-steps-toggle",
    ].map((selector) => {
      const el = document.querySelector(selector),
        r = el.getBoundingClientRect();
      const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
      return { selector, reachable: el === hit || el.contains(hit), width: r.width };
    });
    return {
      replay,
      graph,
      timeline,
      graphOverlap: overlap(replay, graph),
      timelineOverlap: overlap(replay, timeline),
      controls,
      documentWidth: document.documentElement.scrollWidth,
      windowWidth: innerWidth,
    };
  });
}

try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
    args: ["--enable-unsafe-swiftshader"],
  });
  for (const [width, height] of [
    [1600, 1000],
    [1280, 720],
  ]) {
    for (const language of ["en", "zh-CN"]) {
      const context = await browser.newContext({ viewport: { width, height } });
      page = await context.newPage();
      const resources = await observeResources(page);
      result.resources.push({ width, height, language, ...resources });
      await page.goto(fixture.url + "?lang=" + language, { waitUntil: "domcontentloaded" });
      await page.waitForFunction(
        (id) => [...document.querySelector("#record-list").options].some((o) => o.value === id),
        fixture.recording.id,
      );
      await page.selectOption("#record-list", fixture.recording.id);
      await page.waitForFunction((id) => graphDebug.view?.replay?.id === id, fixture.recording.id);
      await page.selectOption("#replay-grain", "events");
      for (const mode of ["2D", "3D"]) {
        if ((await page.locator("#layered-toggle").innerText()).trim() !== mode)
          await page.click("#layered-toggle");
        await ready();
        for (const timeline of [false, true]) {
          if ((await page.locator("#recording-timeline").isVisible()) !== timeline)
            await page.click("#replay-timeline");
          for (const filters of [false, true]) {
            if ((await page.locator("#replay-selection").isVisible()) !== filters)
              await page.click("#replay-steps-toggle");
            await ready();
            const bounds = await measure();
            const check = { width, height, language, mode, timeline, filters, ...bounds };
            result.checks.push(check);
            assert.equal(bounds.graphOverlap, 0, "Replay controls cover the graph");
            assert.equal(bounds.timelineOverlap, 0, "Replay controls overlap the Timeline");
            assert.ok(bounds.graph.height >= 180, "Graph loses useful desktop space");
            assert.ok(bounds.documentWidth <= bounds.windowWidth, "Horizontal page overflow");
            assert.ok(
              bounds.controls.every((c) => c.reachable && c.width > 0),
              "Replay controls are obscured",
            );
            if (timeline && filters) {
              await page.click(".trace-maximize");
              await page.waitForFunction(() =>
                document.querySelector("#recording-timeline").classList.contains("trace-maximized"),
              );
              check.maximized = await measure();
              assert.equal(
                check.maximized.timelineOverlap,
                0,
                "Expanded Timeline covers replay controls",
              );
              assert.ok(check.maximized.controls.every((c) => c.reachable));
              await page.click(".trace-maximize");
              await page.screenshot({ path: path.join(out, `${width}-${language}-${mode}.png`) });
            }
          }
        }
        // Real pointer actions seek and play; the current frame must advance.
        await page.click("#replay-next");
        const before = await page.locator("#replay-events").inputValue();
        await page.selectOption("#replay-speed", "300");
        await page.click("#replay-play");
        await page.waitForFunction(
          (value) => document.querySelector("#replay-events").value !== value,
          before,
        );
        if ((await page.locator("#replay-play").getAttribute("data-icon")) === "pause")
          await page.click("#replay-play");
      }
      await page.click("#replay-live");
      assert.equal(await page.locator("#replay").isVisible(), false);
      await ready();
      assert.deepEqual(resources.failures, []);
      assert.deepEqual(resources.consoleErrors, []);
      assert.deepEqual(resources.pageErrors, []);
      await context.close();
    }
  }
  // Independent negative control: a genuine missing asset must remain a failure.
  const negative = await browser.newPage();
  const diagnostics = await observeResources(negative);
  await negative.goto(fixture.url, { waitUntil: "domcontentloaded" });
  const missing = new URL("/missing-workspace-negative-control.svg", fixture.url).href;
  await Promise.all([
    diagnostics.waitForResponse(missing),
    negative.evaluate(async (url) => {
      await fetch(url);
    }, missing),
  ]);
  assert.ok(diagnostics.failures.some((r) => r.url === missing && r.status === 404));
  result.negative_control = diagnostics.failures.filter((r) => r.url === missing);
  await negative.close();
  assert.deepEqual(fixture.writes, []);
  assert.equal(digest(await readFile(recordingPath)), result.source_sha256);
  result.business_writes = fixture.writes.length;
  result.passed = true;
} catch (error) {
  result.error = String(error.stack || error);
  await page?.screenshot({ path: path.join(out, "failure.png"), timeout: 10000 }).catch(() => {});
  process.exitCode = 1;
} finally {
  await writeFile(path.join(out, "result.json"), JSON.stringify(result, null, 2));
  await browser?.close();
  await fixture.close();
}
console.log(
  JSON.stringify({ passed: result.passed, checks: result.checks.length, error: result.error, out }),
);
