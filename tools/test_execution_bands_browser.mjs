/** Native concurrent workers, real SQLite writes and actual canvas controls. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const out = path.resolve(process.env.BO_EXECUTION_EVIDENCE || ".validation/execution-bands");
await mkdir(out, { recursive: true });
const python =
  process.env.BO_PYTHON || (process.platform === "win32" ? ".venv/Scripts/python.exe" : "python");
const server = spawn(
  python,
  [
    "-B",
    "-X",
    "utf8",
    "-u",
    "tools/execution_band_fixture.py",
    "--serve",
    path.join(out, "project"),
  ],
  { stdio: ["ignore", "pipe", "pipe"] },
);
let stdout = "",
  stderr = "",
  browser,
  page,
  ready;
server.stdout.on("data", (value) => {
  stdout += value;
});
server.stderr.on("data", (value) => {
  stderr += value;
});
const checks = [],
  errors = [];
const midSpan = process.env.BO_EXECUTION_MIDSPAN === "1";

/** Read a completed render and its endpoints in the same browser turn.
 * A separate wait followed by evaluate can straddle a queued reroute: its
 * first frame clears the previous paths before the worker supplies new ones.
 * Flush the control's scheduled frame first, then retain the exact geometry
 * that satisfied readiness. Assertions below still reject missing/bad anchors.
 */
async function routedAnchors(mode, style, previousFrame) {
  await page.evaluate(
    () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
  );
  const handle = await page.waitForFunction(
    ({ mode, style, previousFrame }) => {
      const g = graphDebug,
        spatial = mode === "3D",
        frame = spatial ? g.spatial?.frames : g.metrics.drawCount,
        paths = spatial ? g.spatial?.edgePorts : g.planarPorts;
      if (
        g.layoutBusy ||
        document.querySelector("#edge-routing").value !== style ||
        (spatial && g.spatial?.routing !== style) ||
        !(frame > previousFrame) ||
        !paths?.length
      )
        return false;
      const anchors = g.presentation.edges.flatMap((edge) => {
        const route = paths.find((path) => path.id === edge.id);
        if (!route) return [];
        return [
          [edge.from, edge.sourceRegion, route.start],
          [edge.to, edge.targetRegion, route.end],
        ].flatMap(([id, region, port]) => {
          if (region) return [];
          const box = g.graph.byId.get(id),
            position = spatial ? g.spatialPositions[id] : { x: box.x + box.w / 2, y: box.y + 31 };
          return [
            {
              id,
              error: Math.hypot(
                port.x - position.x,
                port.y - position.y,
                spatial ? port.z - position.z : 0,
              ),
            },
          ];
        });
      });
      return {
        mode,
        style,
        frame,
        paths,
        anchors,
        edgeIds: g.presentation.edges.map((edge) => edge.id),
        routing: spatial ? g.spatial.routeSolver : g.metrics.routeSolver,
      };
    },
    { mode, style, previousFrame },
  );
  try {
    return await handle.jsonValue();
  } finally {
    await handle.dispose();
  }
}

async function startRecording() {
  // Recording startup is asynchronous; workers must start after its boundary
  // is acknowledged unless this fixture intentionally captures mid-span.
  const [response] = await Promise.all([
    page.waitForResponse(
      (response) =>
        response.request().method() === "POST" &&
        new URL(response.url()).pathname === "/api/recordings/start",
    ),
    page.click("#record-start"),
  ]);
  assert.equal(response.status(), 200);
  const acknowledgement = await response.json();
  assert.equal(acknowledgement.status, "recording");
  await page.waitForFunction(
    () =>
      document.querySelector("#record-start").getAttribute("aria-pressed") === "true" &&
      !document.querySelector("#record-stop").disabled,
  );
  await writeFile(
    path.join(out, "recording-start.json"),
    JSON.stringify({ ...acknowledgement, midSpan }, null, 2) + "\n",
  );
}
try {
  ready = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(Error("Worker startup timeout: " + stderr)), 20000);
    const inspect = () => {
      const line = stdout.split(/\r?\n/).find((value) => value.startsWith('{"observer"'));
      if (line) {
        clearTimeout(timer);
        resolve(JSON.parse(line));
      }
    };
    server.stdout.on("data", inspect);
    inspect();
    server.once("exit", (code) => {
      clearTimeout(timer);
      reject(Error(`Worker exited ${code}: ${stderr}`));
    });
  });
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  page = await browser.newPage({ viewport: { width: 1540, height: 1100 } });
  page.on("pageerror", (error) => errors.push(String(error.stack)));
  await page.goto(ready.observer + "/graph?lang=en");
  await page.waitForFunction(() => window.graphDebug?.graph);
  await page.selectOption(".trace-scope", "all");
  if (!midSpan) await startRecording();
  await Promise.all(
    ["alice", "bob"].map(async (actor) =>
      assert.ok((await page.request.post(`${ready.application}/begin?actor=${actor}`)).ok()),
    ),
  );
  await page.waitForFunction(
    () =>
      graphDebug.timeline?.groups === 2 &&
      graphDebug.timeline.lifecycles.filter((slice) => slice.node === "advance" && slice.unfinished)
        .length === 2,
  );
  if (midSpan) {
    await startRecording();
    await page.waitForFunction(
      () => graphDebug.timeline?.source === "recording" && graphDebug.timeline.groups === 2,
    );
  }
  await page.click(".trace-maximize");
  await page.waitForFunction(() => graphDebug.timeline.rows.length === 8);
  await page.screenshot({ path: path.join(out, "concurrent-wait.png") });
  let trace = await page.evaluate(() => graphDebug.timeline);
  assert.deepEqual(
    trace.rows.map((row) => row.layer),
    [
      "business",
      "state",
      "rules",
      "implementation",
      "business",
      "state",
      "rules",
      "implementation",
    ],
  );
  assert.equal(trace.executions.length, 2);
  assert.ok(
    trace.lifecycles.filter((slice) => slice.node === "advance").every((slice) => slice.unfinished),
  );
  checks.push(
    "two real users wait in two complete four concern bands retaining implementation and file projections",
  );
  const canvas = page.locator("#recording-timeline canvas");
  const box = await canvas.boundingBox();
  await page.mouse.click(box.x + 50, box.y + trace.geometry.top + 14);
  await page.waitForFunction(() => graphDebug.timeline.rows.length === 5);
  assert.equal((await page.evaluate(() => graphDebug.timeline.rows))[0].layer, "business");
  await page.screenshot({ path: path.join(out, "one-group-collapsed.png") });
  await page.mouse.click(box.x + 50, box.y + trace.geometry.top + 14);
  await page.waitForFunction(() => graphDebug.timeline.rows.length === 8);
  await page.click(".trace-tracks");
  await page.waitForFunction(() => graphDebug.timeline.rows.length === 2);
  assert.ok(
    (await page.evaluate(() => graphDebug.timeline.rows)).every((row) => row.layer === "business"),
  );
  await page.click(".trace-tracks");
  await page.waitForFunction(() => graphDebug.timeline.rows.length === 8);
  checks.push("independent collapse and all-group collapse retain only business rows");
  await page.request.post(ready.application + "/release");
  let completed = false;
  for (let i = 0; i < 60; i++) {
    const status = await (await page.request.get(ready.application)).json();
    if (
      status.results.alice === "done" &&
      status.results.bob === "done" &&
      status.health.pending === 0
    ) {
      completed = true;
      break;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  assert.ok(completed, "Concurrent workers complete through the actual HTTP interface");
  const actual = await (await page.request.get(ready.application)).json();
  await writeFile(path.join(out, "actual-status.json"), JSON.stringify(actual, null, 2));
  assert.deepEqual(actual.recipients, ["alice", "bob"]);
  assert.equal(actual.health.errors, 0);
  assert.ok(actual.closure.valid, JSON.stringify(actual.closure));
  await page.click("#record-stop");
  await page.waitForFunction(() => graphDebug.timeline?.source === "saved");
  await page.selectOption("#replay-grain", "events");
  await page.click(".trace-fit");
  await page.waitForFunction(
    () =>
      !graphDebug.timeline.zooming &&
      graphDebug.timeline.routes.some((route) => route.route.length === 21),
  );
  trace = await page.evaluate(() => graphDebug.timeline);
  assert.equal(trace.groups, 2);
  assert.ok(
    trace.lifecycles
      .filter((slice) => slice.node === "advance")
      .every((slice) => !slice.unfinished && slice.duration > 100),
  );
  assert.ok(
    trace.routes.some((route) => route.type === "control" && route.fromRow === route.toRow),
  );
  assert.ok(
    trace.routes.some((route) => trace.rows[route.fromRow].group !== trace.rows[route.toRow].group),
  );
  const recordingId = await page.locator("#record-list").inputValue();
  const recording = await (
    await page.request.get(ready.observer + "/api/recordings/" + recordingId)
  ).json();
  await writeFile(path.join(out, "actual-recording.json"), JSON.stringify(recording, null, 2));
  const points = recording.events.filter((event) => event.node === "rule_fact");
  assert.equal(points.length, midSpan ? 2 : 4);
  assert.ok(
    points.every(
      (point) => point.entity === "file-1" && point.parent_event_id && point.parent_call_id,
    ),
  );
  assert.equal(trace.invocationGroups, 2);
  assert.equal(trace.unassignedObservations, 0);
  assert.ok(trace.routes.some((route) => route.type === "observation"));
  checks.push(
    "explicit file-scoped rule facts retain actual parent entries and introduce no extra execution bands",
  );
  await page.screenshot({ path: path.join(out, "completed-links.png") });
  checks.push(
    "real transaction release/acquire dependency curves across bands; both call lifetimes close",
  );
  await page.click(".trace-maximize");
  await page.locator('#semantic [data-node-id="advance"]').evaluate((element) => element.click());
  await page.click("#selection-menu");
  await page.click("#node-expand");
  await page.waitForFunction(() => !graphDebug.layoutBusy && graphDebug.planarPorts.length > 0);
  for (const mode of ["2D", "3D"]) {
    if ((await page.locator("#layered-toggle").innerText()) !== mode)
      await page.click("#layered-toggle");
    for (const style of ["straight", "curve", "orthogonal", "bus"]) {
      const previousFrame = await page.evaluate(
        (mode) => (mode === "3D" ? graphDebug.spatial?.frames || 0 : graphDebug.metrics.drawCount),
        mode,
      );
      await page.selectOption("#edge-routing", style);
      const sample = await routedAnchors(mode, style, previousFrame);
      await writeFile(
        path.join(out, `routing-${mode.toLowerCase()}-${style}.json`),
        JSON.stringify(sample, null, 2) + "\n",
      );
      const { anchors } = sample;
      assert.ok(anchors.length > 0, `${mode} ${style} exercises actual rendered paths`);
      assert.ok(
        anchors.every((anchor) => anchor.error < 1e-5),
        JSON.stringify({ mode, style, anchors }),
      );
    }
    await page.screenshot({
      path: path.join(out, `timeline-${mode.toLowerCase()}.png`),
    });
  }
  checks.push("all four real routed styles use icon centres in 2D and 3D");
  await page.selectOption(".trace-depth", "rules");
  await page.waitForFunction(() => graphDebug.timeline.rows.length === 6);
  await page.click(".trace-single");
  await page.waitForFunction(() => graphDebug.timeline.rows.length === 2);
  assert.ok(
    (await page.evaluate(() => graphDebug.timeline.rows)).every((row) => row.layer === "rules"),
  );
  await page.selectOption(".trace-depth", "all");
  await page.waitForFunction(() => graphDebug.timeline.rows.length === 8);
  const later = await (await page.request.get(ready.application)).json();
  assert.equal(later.events, actual.events, "observation controls create zero business events");
  assert.deepEqual(
    await (await page.request.get(ready.observer + "/api/recordings/" + recordingId)).json(),
    recording,
  );
  checks.push("layer depth and single-layer controls preserve native events and recording bytes");
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify({ passed: true, checks, actual, trace, errors }, null, 2),
  );
  console.log(
    JSON.stringify({
      passed: true,
      checks: checks.length,
      events: recording.events.length,
      groups: 2,
      layerRows: 8,
    }),
  );
} catch (error) {
  await page?.screenshot({ path: path.join(out, "failure.png") }).catch(() => {});
  const diagnostic = await page
    ?.evaluate(() => ({
      metrics: window.graphDebug?.metrics,
      presentation: window.graphDebug?.presentation?.edges,
      planar: window.graphDebug?.planarPorts,
      spatial: window.graphDebug?.spatial,
      timeline: window.graphDebug?.timeline,
    }))
    .catch(() => null);
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify(
      {
        passed: false,
        checks,
        error: String(error.stack),
        errors,
        stdout,
        stderr,
        diagnostic,
      },
      null,
      2,
    ),
  );
  throw error;
} finally {
  if (ready) await page?.request.post(ready.application + "/stop").catch(() => {});
  await browser?.close();
  if (server.exitCode === null) server.kill();
}
