/** Reproduce native zoom selection against the retained main-run recording. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { serveRecording } from "../../../../tools/recording_browser_fixture.mjs";

const { chromium } = createRequire(import.meta.url)("playwright");
const out = path.resolve(process.env.BO_ZOOM_EVIDENCE || ".validation/registered-zoom-proof");
const fixture = await serveRecording(
  path.resolve(
    "docs/review/graph-quality-20261104/publication/lifecycle-main-registered-original/actual-recording.json",
  ),
);
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.BO_BROWSER_EXECUTABLE,
});
const page = await browser.newPage({ viewport: { width: 1520, height: 1060 } });
const errors = [];
page.on("pageerror", (error) => errors.push(String(error.stack)));
const trace = () => page.evaluate(() => graphDebug.timeline);
try {
  await page.goto(fixture.url + "?lang=en");
  await page.selectOption("#record-list", fixture.recording.id);
  await page.waitForFunction(() => graphDebug.timeline?.source === "saved");
  await page.selectOption("#replay-grain", "events");
  await page.selectOption(".trace-scope", "all");
  const canvas = page.locator("#recording-timeline canvas");
  await canvas.focus();
  await page.keyboard.press("End");
  await page.waitForFunction(() => graphDebug.timeline.eventId === "end");
  await page.click(".trace-maximize");
  await page.waitForFunction(() => {
    const canvas = document.querySelector("#recording-timeline canvas"),
      g = graphDebug.timeline.geometry;
    return g.plot === Math.max(1, canvas.clientWidth - g.left - 12);
  });
  const before = await trace(),
    entry = before.routes.find((route) => route.type === "call");
  const check = before.lifecycles.find((slice) => slice.node === "check");
  const factor = Math.max(
    16,
    (before.window.end - before.window.start) / Math.max(0.25, check.duration * 4),
  );
  const box = await canvas.boundingBox();
  await page.mouse.move(box.x + entry.route[0].x, box.y + 38);
  await page.keyboard.down("Control");
  await page.mouse.wheel(0, -Math.log(factor) / 0.005);
  await page.keyboard.up("Control");
  await page.waitForFunction(
    (width) =>
      !graphDebug.timeline.zooming &&
      graphDebug.timeline.window.end - graphDebug.timeline.window.start < width / 10,
    before.window.end - before.window.start,
  );
  const old = await trace();
  await page.screenshot({ path: path.join(out, "old-polyline-anchor.png") });
  await page.click(".trace-fit");
  await page.waitForFunction(
    (width) =>
      !graphDebug.timeline.zooming &&
      graphDebug.timeline.window.end - graphDebug.timeline.window.start > width * 0.99,
    before.window.end - before.window.start,
  );
  const target = (check.start + check.end) / 2;
  const desired = Math.max(0.25, check.duration * 4);
  const stages = [];
  for (let attempt = 0; attempt < 8; attempt++) {
    let current = await trace();
    const width = current.window.end - current.window.start;
    if (width <= desired * 1.02) break;
    const centeredStart = Math.max(0, target - width / 2);
    const panPixels = ((centeredStart - current.window.start) / width) * current.geometry.plot;
    if (attempt && Math.abs(panPixels) > 1) {
      const bounds = await canvas.boundingBox();
      await page.mouse.move(
        bounds.x + current.geometry.left + current.geometry.plot / 2,
        bounds.y + 38,
      );
      await page.keyboard.down("Shift");
      await page.mouse.wheel(0, panPixels);
      await page.keyboard.up("Shift");
      await page.waitForFunction(
        ({ start, tolerance }) => Math.abs(graphDebug.timeline.window.start - start) <= tolerance,
        { start: centeredStart, tolerance: width / current.geometry.plot },
      );
      current = await trace();
    }
    const step = Math.min(16, width / desired);
    const canvasBox = await canvas.boundingBox();
    const anchor =
      current.geometry.left + current.geometry.plot * ((target - current.window.start) / width);
    await page.mouse.move(canvasBox.x + anchor, canvasBox.y + 38);
    await page.keyboard.down("Control");
    await page.mouse.wheel(0, -Math.log(step) / 0.005);
    await page.keyboard.up("Control");
    await page.waitForFunction(
      (expected) =>
        !graphDebug.timeline.zooming &&
        graphDebug.timeline.window.end - graphDebug.timeline.window.start <= expected * 1.02,
      width / step,
    );
    stages.push(await trace());
  }
  await page.waitForFunction(
    (target) =>
      !graphDebug.timeline.zooming &&
      graphDebug.timeline.window.start <= target &&
      graphDebug.timeline.window.end >= target &&
      graphDebug.timeline.routes.some(
        (r) =>
          r.type === "call" &&
          r.raw === graphDebug.timeline.lifecycles.find((s) => s.node === "check").raw &&
          r.fromRow !== r.toRow &&
          r.route[1].y > graphDebug.timeline.geometry.top + 5,
      ),
    target,
  );
  const fixed = await trace();
  await page.screenshot({ path: path.join(out, "staged-time-anchor.png") });
  assert.ok(
    fixed.routes.some(
      (r) => r.type === "call" && r.fromRow !== r.toRow && r.route[1].y > fixed.geometry.top + 5,
    ),
  );
  assert.ok(fixed.window.end - fixed.window.start < (before.window.end - before.window.start) / 10);
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify(
      {
        check,
        initialWindow: before.window,
        initialRoute: entry,
        old: {
          window: old.window,
          routes: old.routes,
          intendedRoutePresent: old.routes.some(
            (r) =>
              r.type === "call" && r.fromRow !== r.toRow && r.route[1].y > old.geometry.top + 5,
          ),
        },
        staged: {
          target,
          desired,
          stages: stages.map((s) => ({ window: s.window, flows: s.flows })),
          window: fixed.window,
          routes: fixed.routes,
        },
        recording_id: fixture.recording.id,
        writes: fixture.writes,
        errors,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(
    JSON.stringify({
      passed: true,
      oldRoutes: old.routes.length,
      fixedRoutes: fixed.routes.length,
      stages: stages.length,
      out,
    }),
  );
} finally {
  await browser.close();
  await fixture.close();
}
