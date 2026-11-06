/** Native pointer/keyboard acceptance against an unchanged, real execution recording. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import { timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import { serveRecording } from "./recording_browser_fixture.mjs";

const { chromium } = createRequire(import.meta.url)("playwright");
const out = path.resolve(
  process.env.BO_TIMELINE_EVIDENCE || "docs/review/recording-timeline/browser-01",
);
await mkdir(out, { recursive: true });
const fixturePath = path.resolve("docs/review/spatial-workspace/replay-fixture.json");
const fixture = await serveRecording(fixturePath),
  items = timeline(fixture.recording);
const commits = fixture.recording.runtime_frames.frames.map((frame) =>
  items.findIndex((item) => item.id === frame.event_id),
);
const errors = [],
  checks = [];
let browser, page;
const snapshot = () => page.evaluate(() => graphDebug.timeline);
/** A reload must follow the server's acknowledgment of this exact timeline setting. */
const timelineSave = (expected, afterRevision = -1) =>
  page
    .waitForResponse(async (response) => {
      if (
        new URL(response.url()).pathname !== "/api/preferences" ||
        response.request().method() !== "POST" ||
        response.status() !== 200
      )
        return false;
      const saved = await response.json();
      const raw = Object.entries(saved.entries).find(([key]) => key.endsWith(":analysis"))?.[1];
      const settings = raw && JSON.parse(raw).timeline;
      return (
        saved.revision > afterRevision &&
        settings &&
        Object.entries(expected).every(([key, value]) => settings[key] === value)
      );
    })
    .then((response) => response.json());
const sameCursor = async () => {
  // Sample one browser turn: playback can advance between separate round trips.
  const { trace, positionId, timelineId, graphRaw, transfers } = await page.evaluate(() => ({
    trace: graphDebug.timeline,
    positionId: document.querySelector("#replay-position").getAttribute("data-event-id"),
    timelineId: document.querySelector("#recording-timeline").getAttribute("data-event-id"),
    graphRaw: graphDebug.view.replay.index,
    transfers: JSON.parse(
      document.querySelector("#recording-timeline").getAttribute("data-graph-transfers"),
    ),
  }));
  assert.equal(positionId, trace.eventId);
  assert.equal(timelineId, trace.eventId);
  assert.equal(graphRaw, trace.raw);
  assert.deepEqual(transfers, trace.transfers);
  return trace;
};
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (error) => errors.push(String(error.stack)));
  await page.goto(fixture.url + "?lang=en");
  await page.waitForFunction(() => window.graphDebug?.graph);
  assert.equal(await page.locator("#recording-timeline").isVisible(), false);
  await page.selectOption("#record-list", fixture.recording.id);
  await page.waitForSelector("#recording-timeline canvas", { state: "visible" });
  await page.selectOption("#replay-grain", "events");
  await page.selectOption(".trace-scope", "all");
  await page.waitForFunction(() => graphDebug.timeline?.geometry);
  const canvas = page.locator("#recording-timeline canvas");
  await sameCursor();
  checks.push({
    dock: "historical snapshot has no live capture; saved replay opens its timeline",
    realEvents: fixture.recording.events.length,
  });

  for (const mode of ["2D", "3D"]) {
    if ((await page.locator("#layered-toggle").innerText()) !== mode)
      await page.click("#layered-toggle");
    await page.selectOption("#analysis-view", "states");
    await page.selectOption("#replay-events", String(commits[1]));
    await page.waitForFunction(() => !graphDebug.layoutBusy);
    let trace = await sameCursor();
    assert.equal(trace.raw, commits[1]);
    assert.equal(await page.evaluate(() => graphDebug.view.machine.current), "in_progress");
    const transferIds = trace.transfers;
    const animatedEdges = await page
      .locator("#semantic-edges [data-edge-id]")
      .evaluateAll((nodes) =>
        nodes.filter((node) => node.dataset.payload).map((node) => node.dataset.edgeId),
      );
    assert.deepEqual(
      animatedEdges.sort(),
      [...transferIds].sort(),
      "timeline reports exactly the graph's evidence-supported transfers",
    );
    await page.click(".trace-inspect");
    const transitionPayload = JSON.parse(await page.locator(".trace-payload").innerText());
    assert.ok(
      transitionPayload.changes.some(
        (change) => change.kind === "business" && change.after === "in_progress",
      ),
    );
    await page.click(".trace-inspect");
    await page.click(".trace-fit");
    // Zoom through real toolbar clicks, keeping the selected transition in view.
    for (let i = 0; i < 9; i++) await page.click(".trace-zoom-in");
    await page.waitForFunction(() => !graphDebug.timeline.zooming);
    trace = await snapshot();
    const box = await canvas.boundingBox();
    const target = trace.points
      .filter((point) => point.time > trace.window.start && point.time < trace.window.end)
      .find((point) => point.raw !== trace.raw);
    assert.ok(target, "zoomed window contains another real event");
    const px =
      box.x +
      trace.geometry.left +
      ((target.time - trace.window.start) / (trace.window.end - trace.window.start)) *
        trace.geometry.plot;
    await page.mouse.move(px - 3, box.y + 37);
    await page.mouse.down();
    await page.mouse.move(px, box.y + 37, { steps: 8 });
    await page.mouse.up();
    await page.waitForFunction((raw) => graphDebug.timeline.raw === raw, target.raw);
    await sameCursor();
    await canvas.press("ArrowRight");
    await page.waitForFunction((raw) => graphDebug.timeline.raw !== raw, target.raw);
    await sameCursor();
    await page.click(".trace-inspect");
    const payload = JSON.parse(await page.locator(".trace-payload").innerText());
    assert.equal(payload.id, (await snapshot()).eventId);
    await page.click(".trace-inspect");
    await page.screenshot({ path: path.join(out, `timeline-${mode.toLowerCase()}.png`) });
    checks.push({
      mode,
      scrub: true,
      keyboard: true,
      exactState: "in_progress",
      graphCursorAndTransfers: true,
      actualAnimatedEdges: transferIds,
    });
  }

  await page.click(".trace-fit");
  await page.waitForFunction(() => !graphDebug.timeline.zooming);
  let trace = await snapshot(),
    box = await canvas.boundingBox();
  const width = trace.window.end - trace.window.start;
  await page.mouse.move(box.x + trace.geometry.left + trace.geometry.plot * 0.45, box.y + 37);
  await page.mouse.wheel(0, -220);
  // Ordinary wheel scrolls tracks, Ctrl-wheel changes the time window.
  await page.keyboard.down("Control");
  await page.mouse.wheel(0, -220);
  await page.keyboard.up("Control");
  await page.waitForFunction(
    (width) => graphDebug.timeline.window.end - graphDebug.timeline.window.start < width,
    width,
  );
  trace = await snapshot();
  const beforePan = trace.window.start;
  await page.mouse.move(box.x + trace.geometry.left + trace.geometry.plot * 0.5, box.y + 12);
  await page.mouse.down();
  await page.mouse.move(box.x + trace.geometry.left + trace.geometry.plot * 0.6, box.y + 12, {
    steps: 12,
  });
  await page.mouse.up();
  await page.waitForFunction((before) => graphDebug.timeline.window.start !== before, beforePan);
  await page.click(".trace-fit");
  await page.waitForTimeout(40);
  trace = await snapshot();
  box = await canvas.boundingBox();
  await page.keyboard.down("Shift");
  await page.mouse.move(box.x + trace.geometry.left + trace.geometry.plot * 0.15, box.y + 38);
  await page.mouse.down();
  await page.mouse.move(box.x + trace.geometry.left + trace.geometry.plot * 0.75, box.y + 38, {
    steps: 14,
  });
  await page.mouse.up();
  await page.keyboard.up("Shift");
  assert.ok((await snapshot()).range);
  await page.click(".trace-loop");
  assert.equal(await page.locator("#replay-loop").isChecked(), true);
  await page.click(".trace-clear");
  assert.equal(await page.locator("#replay-loop").isChecked(), false);
  checks.push({ ctrlWheelZoom: true, overviewDrag: true, shiftRangeUsesExistingLoop: true });

  await page.click("#replay-steps-toggle");
  const skippedRaw = commits[1],
    skippedId = items[skippedRaw].id;
  await page.locator(`#replay-step-list input[data-event-id="${skippedId}"]`).uncheck();
  assert.equal(
    (await snapshot()).points.some((point) => point.raw === skippedRaw),
    false,
  );
  await page.locator(`#replay-step-list input[data-event-id="${skippedId}"]`).check();
  assert.equal(
    (await snapshot()).points.some((point) => point.raw === skippedRaw),
    true,
  );
  await page.click("#replay-steps-toggle");
  checks.push({ skippedStepsShareReplayPlan: true });

  await page.selectOption("#replay-events", String(commits[0]));
  await page.selectOption("#replay-speed", "300");
  await page.click("#replay-play");
  await page.waitForFunction((raw) => graphDebug.timeline.raw !== raw, commits[0]);
  await sameCursor();
  await page.click("#replay-play");
  const held = (await snapshot()).raw;
  await page.waitForTimeout(1000);
  assert.equal((await snapshot()).raw, held, "held graph animation does not advance timeline");
  checks.push({ playback: true, pauseRepeatsSameEvent: true });

  // This fixture contains actual data-transfer edges. State-only views above
  // correctly have no call edges; exercise a nonempty animation witness as well.
  await page.selectOption("#analysis-view", "data-operations");
  await page.locator("#layers-all").evaluate((button) => button.click());
  await page.click("#expand");
  const dataRaw = items.findIndex((item) => item.node === "db.read" && item.phase === "return");
  await page.selectOption("#replay-events", String(dataRaw));
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  const dataTrace = await sameCursor();
  assert.ok(dataTrace.transfers.length, "real query return has graph data-transfer animation");
  const payloadEdges = await page
    .locator("#semantic-edges [data-edge-id]")
    .evaluateAll((nodes) =>
      nodes.filter((node) => node.dataset.payload).map((node) => node.dataset.edgeId),
    );
  assert.deepEqual(payloadEdges.sort(), [...dataTrace.transfers].sort());
  checks.push({ nonemptyDataTransferAnimation: dataTrace.transfers });
  const transformedRaw = items.findIndex(
    (item) => item.node === "db.normalize" && item.phase === "change",
  );
  await page.selectOption("#replay-events", String(transformedRaw));
  await sameCursor();
  assert.match(await page.locator(".trace-selected").innerText(), /\d(?:\.\d+)? (?:ms|µs|s)/);
  assert.equal((await page.locator(".trace-selected").innerText()).includes("Open call"), false);
  const legacyData = await page.evaluate(() =>
    ["db.transaction", "db.normalize"].map((id) => {
      const box = graphDebug.graph.boxes.find((node) => node.id === id);
      return {
        id,
        phase: box.activation.phase,
        state: box.state,
        caption: box.rows[0].text,
        duration: box.activation.duration,
      };
    }),
  );
  assert.deepEqual(
    legacyData.map(({ id, phase, state, caption }) => ({ id, phase, state, caption })),
    [
      { id: "db.transaction", phase: "committed", state: "historical", caption: "Committed" },
      { id: "db.normalize", phase: "transformed", state: "historical", caption: "Transformed" },
    ],
  );
  assert.ok(legacyData.every((node) => node.duration > 0));
  checks.push({ actualDataTransformHasCompletedDuration: true });
  checks.push({ legacyDataPhysicalPhasesAndNeutralClosedStyles: legacyData });

  await page.selectOption(".trace-scope", "view");
  const scoped = await snapshot();
  await page.selectOption(".trace-scope", "all");
  assert.ok((await snapshot()).rows.length >= scoped.rows.length);
  const resize = page.locator(".trace-resize"),
    resizeBox = await resize.boundingBox();
  const originalHeight = await page
    .locator("#recording-timeline")
    .evaluate((element) => element.clientHeight);
  await page.mouse.move(resizeBox.x + resizeBox.width / 2, resizeBox.y + 4);
  await page.mouse.down();
  await page.mouse.move(resizeBox.x + resizeBox.width / 2, resizeBox.y - 65, { steps: 12 });
  await page.mouse.up();
  assert.ok(
    (await page.locator("#recording-timeline").evaluate((element) => element.clientHeight)) >
      originalHeight,
  );
  const timelineHeight = Number(await resize.getAttribute("aria-valuenow"));
  const closedSave = timelineSave({ scope: "all", height: timelineHeight, visible: false });
  await page.click(".trace-close");
  assert.equal(await page.locator("#recording-timeline").isVisible(), false);
  const closedAcknowledgment = await closedSave;
  const reopenedSave = timelineSave(
    { scope: "all", height: timelineHeight, visible: true },
    closedAcknowledgment.revision,
  );
  await page.click("#replay-timeline");
  assert.equal(await page.locator("#recording-timeline").isVisible(), true);
  const reopenedAcknowledgment = await reopenedSave;
  assert.ok(reopenedAcknowledgment.revision > closedAcknowledgment.revision);
  await page.reload();
  await page.waitForFunction(() => window.graphDebug?.graph);
  await page.selectOption("#record-list", fixture.recording.id);
  await page.waitForSelector("#recording-timeline", { state: "visible" });
  assert.equal(await page.locator(".trace-scope").inputValue(), "all");
  assert.equal(Number(await resize.getAttribute("aria-valuenow")), timelineHeight);
  checks.push({
    scopedRows: scoped.rows.length,
    persistedScopeHeightAndVisibility: true,
    acknowledgedRevision: reopenedAcknowledgment.revision,
  });

  await page.goto(fixture.url + "?lang=zh-CN");
  await page.waitForFunction(() => window.graphDebug?.graph);
  await page.selectOption("#record-list", fixture.recording.id);
  await page.waitForSelector("#recording-timeline", { state: "visible" });
  assert.equal(await page.locator(".trace-loop").innerText(), "循环选区");
  await page.setViewportSize({ width: 430, height: 850 });
  await page.waitForTimeout(180);
  assert.ok(await canvas.isVisible());
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  await canvas.press("Home");
  await sameCursor();
  await page.screenshot({ path: path.join(out, "timeline-mobile-zh.png") });
  const touchPage = await browser.newPage({
    viewport: { width: 430, height: 850 },
    hasTouch: true,
    isMobile: true,
  });
  touchPage.on("pageerror", (error) => errors.push(String(error.stack)));
  await touchPage.goto(fixture.url + "?lang=zh-CN");
  await touchPage.waitForFunction(() => window.graphDebug?.graph);
  await touchPage.selectOption("#record-list", fixture.recording.id);
  await touchPage.waitForSelector("#recording-timeline", { state: "visible" });
  await touchPage.selectOption("#replay-grain", "events");
  await touchPage.selectOption(".trace-scope", "all");
  await touchPage.selectOption("#replay-events", String(commits[1]));
  await touchPage.click(".trace-fit");
  for (let i = 0; i < 7; i++) await touchPage.click(".trace-zoom-in");
  await touchPage.waitForFunction(() => !graphDebug.timeline.zooming);
  const touchTrace = await touchPage.evaluate(() => graphDebug.timeline);
  const touchBox = await touchPage.locator("#recording-timeline canvas").boundingBox();
  const touchTime = (touchTrace.window.start + touchTrace.window.end) / 2;
  const expectedTouch = touchTrace.points.reduce((a, b) =>
    Math.abs(a.time - touchTime) <= Math.abs(b.time - touchTime) ? a : b,
  );
  await touchPage.touchscreen.tap(
    touchBox.x + touchTrace.geometry.left + touchTrace.geometry.plot / 2,
    touchBox.y + 37,
  );
  await touchPage.waitForFunction((raw) => graphDebug.timeline.raw === raw, expectedTouch.raw);
  assert.equal(
    await touchPage.locator("#replay-position").getAttribute("data-event-id"),
    (await touchPage.evaluate(() => graphDebug.timeline)).eventId,
  );
  await touchPage.screenshot({ path: path.join(out, "timeline-touch.png") });
  await touchPage.close();
  checks.push({ nativeTouchSeek: true });
  await page.click("#replay-live");
  assert.equal(await page.locator("#recording-timeline").isVisible(), false);
  assert.equal(await page.evaluate(() => graphDebug.timeline), null);
  assert.deepEqual(fixture.writes, []);
  assert.equal(
    createHash("sha256")
      .update(await readFile(fixturePath))
      .digest("hex"),
    createHash("sha256").update(fixture.bytes).digest("hex"),
  );
  assert.deepEqual(errors, []);
  checks.push({
    chinese: true,
    mobile: true,
    returnedToLive: true,
    businessWrites: fixture.writes.length,
    recordingBytesUnchanged: true,
  });
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify({ passed: true, checks, errors }, null, 2),
  );
  console.log(JSON.stringify({ passed: true, checks }, null, 2));
} catch (error) {
  await page?.screenshot({ path: path.join(out, "failure.png") }).catch(() => {});
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify({ passed: false, checks, errors, error: String(error.stack) }, null, 2),
  );
  throw error;
} finally {
  await browser?.close();
  await fixture.close();
}
