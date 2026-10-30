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
const python =
  process.env.BO_PYTHON || (process.platform === "win32" ? ".venv/Scripts/python.exe" : "python");
const server = spawn(
  python,
  ["-u", "-B", "-X", "utf8", "tools/test_trace_lifecycle.py", "--serve", trial],
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
    "completed",
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
