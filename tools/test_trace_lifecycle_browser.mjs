/** Actual Python/SQLite work, active recording and native graph/timeline interaction. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const { chromium } = createRequire(import.meta.url)("playwright");
const out = path.resolve(process.env.BO_LIFECYCLE_EVIDENCE || ".validation/lifecycle-browser");
await mkdir(out, { recursive: true });
const trial = path.join(out, "project-" + Date.now());
const registered = process.env.BO_REGISTERED_LIFECYCLE === "1";
const telemetry = process.env.BO_TELEMETRY_BACKEND === "1";
const python =
  process.env.BO_PYTHON || (process.platform === "win32" ? ".venv/Scripts/python.exe" : "python");
const server = spawn(
  python,
  [
    "-u",
    "-B",
    "-X",
    "utf8",
    "tools/test_trace_lifecycle.py",
    "--serve",
    trial,
    ...(registered ? ["--registered"] : []),
    ...(telemetry ? ["--telemetry"] : []),
  ],
  { stdio: ["ignore", "pipe", "pipe"] },
);
let stdout = "",
  stderr = "",
  browser,
  page;
server.stdout.on("data", (data) => {
  stdout += data;
});
server.stderr.on("data", (data) => {
  stderr += data;
});
const checks = [],
  errors = [];
const midSpan = process.env.BO_RECORD_MIDSPAN === "1";
const ready = await new Promise((resolve, reject) => {
  const timer = setTimeout(() => reject(Error("Live fixture did not start: " + stderr)), 20000);
  server.stdout.on("data", () => {
    const line = stdout.split(/\r?\n/).find((line) => line.startsWith('{"observer"'));
    if (line) {
      clearTimeout(timer);
      resolve(JSON.parse(line));
    }
  });
  server.once("exit", (code) => {
    clearTimeout(timer);
    reject(Error("Live fixture exited " + code + ": " + stderr));
  });
});
const trace = () => page.evaluate(() => graphDebug.timeline);
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  page = await browser.newPage({ viewport: { width: 1520, height: 1060 } });
  page.on("pageerror", (error) => errors.push(String(error.stack)));
  await page.goto(ready.observer + "/graph?lang=en");
  await page.waitForFunction(() => graphDebug?.timeline?.geometry);
  await page.selectOption(".trace-scope", "all");
  assert.equal((await trace()).source, "live");
  // Freeze the empty live boundary and use the actual source menu. Synthetic
  // live IDs must not be sent to the saved-recording source endpoint.
  const initialCanvas = page.locator("#recording-timeline canvas");
  await initialCanvas.focus();
  await page.keyboard.press("Home");
  await page.waitForFunction(() => graphDebug.view.replay?.index === 0);
  await page.fill("#node-search", "Share file");
  await page.locator("#search-results button").first().click();
  await page.locator("#viewport").focus();
  await page.keyboard.press("Shift+F10");
  await page.click("#source");
  await page.waitForFunction(() =>
    document.querySelector("#source-code").textContent.includes("def advance"),
  );
  await page.screenshot({ path: path.join(out, "source-while-inspecting.png") });
  await page.click("#close-detail");
  await page.fill("#node-search", "");
  await page.click(".trace-live");
  await page.waitForFunction(() => !graphDebug.view.replay);
  checks.push(
    "live inspection can freeze its current boundary and read the actual complete source file",
  );
  await page.selectOption("#analysis-view", "code");
  await page.waitForFunction(() => graphDebug.view.code_structure?.loaded_nodes > 0);
  const codeIds = await page.evaluate(() =>
    [...graphDebug.graph.all.values()]
      .filter((node) => node.code_role)
      .map((node) => node.id)
      .sort(),
  );
  await initialCanvas.focus();
  await page.keyboard.press("Home");
  await page.waitForFunction(() => graphDebug.view.replay?.index === 0);
  assert.deepEqual(
    await page.evaluate(() =>
      [...graphDebug.graph.all.values()]
        .filter((node) => node.code_role)
        .map((node) => node.id)
        .sort(),
    ),
    codeIds,
  );
  await page.click(".trace-live");
  await page.waitForFunction(() => !graphDebug.view.replay);
  await page.selectOption("#analysis-view", "overview");
  checks.push(
    "live inspection retains the already-loaded static code projection and its physical node IDs",
  );
  if (!midSpan) await page.click("#record-start");
  await page.request.post(ready.application + "/begin");
  await page.waitForFunction(
    () =>
      graphDebug.graph.boxes.find((box) => box.id === "advance")?.activation?.phase === "waiting",
  );
  if (midSpan) await page.click("#record-start");
  await page.waitForFunction(
    () =>
      graphDebug.timeline?.source === "recording" &&
      graphDebug.timeline.lifecycles.some((slice) => slice.node === "advance" && slice.unfinished),
  );
  const running = await trace();
  if (registered) {
    assert.equal(
      await page.evaluate(
        () => graphDebug.graph.boxes.find((box) => box.id === "advance")?.activation?.label,
      ),
      "Waiting for confirmation",
    );
    assert.ok(
      running.lifecycles
        .find((slice) => slice.node === "advance")
        .stages.some((stage) => stage.state === "awaiting_release" && stage.registered),
    );
  }
  if (!midSpan) assert.ok(running.flows > 0);
  const duration = running.lifecycles.find((slice) => slice.node === "advance");
  await page.waitForFunction(
    (end) =>
      graphDebug.timeline.lifecycles.find((slice) => slice.node === "advance")?.end > end + 500,
    duration.end,
  );
  assert.equal((await page.request.get(ready.application)).ok(), true);
  assert.equal((await (await page.request.get(ready.application)).json()).shares, 0);
  await page.screenshot({ path: path.join(out, "active-waiting.png") });
  checks.push(
    "actual SQLite operation waits with a growing parent bar, graph waiting state and full child call/return chain",
  );

  const canvas = page.locator("#recording-timeline canvas");
  let box = await canvas.boundingBox(),
    state = await trace();
  await page.keyboard.down("Shift");
  await page.mouse.move(box.x + state.geometry.left + state.geometry.plot * 0.15, box.y + 66);
  await page.mouse.down();
  await page.mouse.move(box.x + state.geometry.left + state.geometry.plot * 0.8, box.y + 66, {
    steps: 12,
  });
  await page.mouse.up();
  await page.keyboard.up("Shift");
  assert.ok((await trace()).range[1] > (await trace()).range[0]);
  await canvas.focus();
  await page.keyboard.press("Home");
  await page.waitForFunction(() => graphDebug.view.replay?.index === 0);
  assert.equal((await page.request.get(ready.application)).ok(), true);
  await page.click(".trace-live");
  await page.waitForFunction(() => !graphDebug.view.replay);
  checks.push(
    "native interval drag and live-to-read-only seek keep business work running; return to live restores current state",
  );

  await page.request.post(ready.application + "/release");
  for (let i = 0; i < 80; i++) {
    if (!(await (await page.request.get(ready.application)).json()).running) break;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  const facts = await (await page.request.get(ready.application)).json();
  assert.deepEqual(
    { state: facts.state, shares: facts.shares, errors: facts.probe_errors },
    { state: "done", shares: 1, errors: 0 },
  );
  await page.click("#record-stop");
  await page.waitForFunction(() => graphDebug.timeline?.source === "saved");
  await page.selectOption("#replay-grain", "events");
  await page.selectOption(".trace-scope", "all");
  await canvas.focus();
  await page.keyboard.press("End");
  await page.waitForFunction(
    () => graphDebug.view.replay?.event?.id === "end" || graphDebug.timeline.eventId === "end",
  );
  state = await trace();
  const parent = state.lifecycles.find((slice) => slice.node === "advance");
  assert.ok(parent.duration > 500);
  assert.equal(parent.unfinished, false);
  if (midSpan) assert.equal(parent.clippedStart, true);
  assert.equal(
    await page.evaluate(
      () => graphDebug.graph.boxes.find((box) => box.id === "advance")?.activation?.phase,
    ),
    registered ? "ended" : "returned",
  );
  const recordingId = await page.locator("#record-list").inputValue();
  const saved = await (
    await page.request.get(ready.observer + "/api/recordings/" + recordingId)
  ).json();
  await writeFile(path.join(out, "actual-recording.json"), JSON.stringify(saved, null, 2));
  checks.push({
    actualCompletion: facts,
    parentMilliseconds: parent.duration,
    recordedEvents: saved.events.length,
  });

  const cursor = state.eventId;
  if (registered) {
    assert.equal(parent.terminal.state, "shared");
    assert.equal(parent.terminal.termination, "return");
    if (!state.rows.some((row) => row.members.includes("advance")))
      await page.click(".trace-tracks");
    await page.waitForFunction(() =>
      graphDebug.timeline.rows.some((row) => row.members.includes("advance")),
    );
    await page.click(".trace-maximize");
    await page.waitForFunction(() =>
      document.querySelector("#recording-timeline").classList.contains("trace-maximized"),
    );
    await page.waitForFunction(() => {
      const canvas = document.querySelector("#recording-timeline canvas");
      const geometry = graphDebug.timeline.geometry;
      return geometry.plot === Math.max(1, canvas.clientWidth - geometry.left - 12);
    });
    state = await trace();
    assert.ok(state.routes.some((route) => route.fromRow !== route.toRow));
    assert.ok(
      state.routes.some((route) => route.type === "control" && route.fromRow === route.toRow),
      "the actual wait-to-resume dependency has a same-track connector",
    );
    if (!midSpan) {
      // The actual SQL/check calls last microseconds. Inspect their real time
      // scale rather than inflating them to look long in the full recording.
      const entry = state.routes.find((route) => route.type === "call");
      const check = state.lifecycles.find((slice) => slice.node === "check");
      const factor = Math.max(
        16,
        (state.window.end - state.window.start) / Math.max(0.25, check.duration * 4),
      );
      const beforeZoom = state.window.end - state.window.start;
      const bounds = await canvas.boundingBox();
      await page.mouse.move(bounds.x + entry.route[0].x, bounds.y + 38);
      await page.keyboard.down("Control");
      await page.mouse.wheel(0, -Math.log(factor) / 0.005);
      await page.keyboard.up("Control");
      await page.waitForFunction(
        (width) =>
          !graphDebug.timeline.zooming &&
          graphDebug.timeline.window.end - graphDebug.timeline.window.start < width / 10,
        beforeZoom,
      );
      state = await trace();
      await page.screenshot({ path: path.join(out, "local-call-lifetimes.png") });
    }
    const route = state.routes.find(
      (route) =>
        route.type === (midSpan ? "return" : "call") &&
        route.fromRow !== route.toRow &&
        route.route[1].y > state.geometry.top + 5,
    );
    assert.ok(route);
    const point = {
      x: (route.route[1].x + route.route[2].x) / 2,
      y: (route.route[1].y + route.route[2].y) / 2,
    };
    const canvasBox = await canvas.boundingBox();
    await page.mouse.move(canvasBox.x + point.x, canvasBox.y + point.y);
    await page.waitForSelector(".trace-tooltip:not([hidden])");
    assert.match(await page.locator(".trace-tooltip").innerText(), /→/);
    await page.screenshot({ path: path.join(out, "causal-link-hover.png") });
    await page.mouse.click(canvasBox.x + point.x, canvasBox.y + point.y);
    await page.waitForFunction((raw) => graphDebug.timeline.raw === raw, route.raw);
    const expectedEvent = saved.events.find(
      (event) =>
        event.node === (midSpan ? "write" : "check") &&
        event.phase === (midSpan ? "return" : "enter"),
    );
    assert.equal(
      (await trace()).eventId,
      expectedEvent.id,
      "clicked handoff matches the original captured boundary event",
    );
    const fixedEvent = (await trace()).eventId;
    const xs = route.route.map((point) => point.x),
      ys = route.route.map((point) => point.y);
    const clip = {
      x: canvasBox.x + Math.max(state.geometry.left, Math.min(...xs) - 5),
      y: canvasBox.y + Math.max(state.geometry.top, Math.min(...ys) - 5),
      width: Math.max(12, Math.max(...xs) - Math.min(...xs) + 10),
      height: Math.max(12, Math.max(...ys) - Math.min(...ys) + 10),
    };
    await page.waitForTimeout(90);
    const motionA = await page.screenshot({ path: path.join(out, "connector-motion-a.png"), clip });
    await page.waitForTimeout(230);
    const motionB = await page.screenshot({ path: path.join(out, "connector-motion-b.png"), clip });
    assert.notDeepEqual(
      motionA,
      motionB,
      "the selected connector moves while its raw event stays fixed",
    );
    assert.equal((await trace()).eventId, fixedEvent);
    await canvas.focus();
    await page.keyboard.press("End");
    await page.waitForFunction(() => graphDebug.timeline.eventId === "end");
    await page.click(".trace-fit");
    await page.waitForFunction(
      () => !graphDebug.timeline.zooming && graphDebug.timeline.window.start === 0,
    );
    state = await trace();
    const sameTrack = state.routes.find(
      (route) => route.type === "control" && route.fromRow === route.toRow,
    );
    const middle = {
      x: (sameTrack.route[1].x + sameTrack.route[2].x) / 2,
      y: sameTrack.route[1].y,
    };
    const fullBox = await canvas.boundingBox();
    await page.mouse.move(fullBox.x + middle.x, fullBox.y + middle.y);
    await page.waitForSelector(".trace-tooltip:not([hidden])");
    assert.match(await page.locator(".trace-tooltip").innerText(), /Control transfer/);
    await page.screenshot({ path: path.join(out, "same-track-link.png") });
    await page.click(".trace-maximize");
    checks.push(
      "registered lifecycle stages and terminal meanings match actual values; node tracks expose directed handoff/return links with native hover and click-to-seek",
    );
  }
  await page.selectOption(".trace-depth", "rules");
  state = await trace();
  assert.ok(state.rows.every((row) => ["business", "state", "rules"].includes(row.layer)));
  await page.click(".trace-single");
  assert.ok((await trace()).rows.every((row) => row.layer === "rules"));
  assert.equal((await trace()).eventId, cursor);
  await page.click(".trace-single");
  await page.click(".trace-single");
  await page.selectOption(".trace-depth", "all");
  assert.equal(await page.locator(".trace-single").getAttribute("aria-pressed"), "false");
  for (const mode of ["3D", "2D"]) {
    if ((await page.locator("#layered-toggle").innerText()) !== mode)
      await page.click("#layered-toggle");
    await page.waitForFunction(() => !graphDebug.layoutBusy);
    assert.equal((await trace()).eventId, cursor);
    assert.ok((await trace()).flows > 0);
    await page.screenshot({ path: path.join(out, "completed-" + mode + ".png") });
  }
  checks.push(
    "bottom-up depth, single-layer inspection and 2D/3D retain the same raw cursor and original recording",
  );

  box = await canvas.boundingBox();
  state = await trace();
  await page.mouse.move(box.x + state.geometry.left + state.geometry.plot / 2, box.y + 37);
  await page.keyboard.down("Control");
  await page.mouse.wheel(0, -140);
  await page.keyboard.up("Control");
  await page.waitForTimeout(40);
  const during = await trace();
  await page.waitForTimeout(220);
  const after = await trace();
  assert.ok(after.window.end - after.window.start < state.window.end - state.window.start);
  assert.ok(during.window.end - during.window.start >= after.window.end - after.window.start);
  await page.screenshot({ path: path.join(out, "zoomed.png") });
  const countBefore = facts.events;
  if (telemetry) {
    const rawEvents = await page.evaluate(() => graphDebug.view.events);
    assert.ok(rawEvents.some((event) => event.trace?.span_id));
    assert.ok(
      rawEvents
        .filter((event) => event.lifecycle === "span")
        .every((event) => event.trace?.trace_id),
    );
    checks.push(
      "real OpenTelemetry SpanContexts survive live observation, recording, Timeline and both graph renderers",
    );
  }
  await page.click(".trace-fit");
  await page.click("#replay-timeline");
  await page.click("#replay-timeline");
  assert.equal((await (await page.request.get(ready.application)).json()).events, countBefore);
  assert.deepEqual(errors, []);
  checks.push("smooth native wheel zoom, fit and visibility controls create zero business events");
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
  server.kill();
  await writeFile(path.join(out, "service.log"), stdout + "\n" + stderr);
}
