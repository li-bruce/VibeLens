/** Actual single-rule recording keeps callers and omits their business values. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const out = path.resolve(process.env.BO_FOCUSED_EVIDENCE || ".validation/focused-boundaries");
await mkdir(out, { recursive: true });
const python = process.platform === "win32" ? ".venv/Scripts/python.exe" : "python";
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
  ready,
  browser,
  page;
const errors = [];
server.stdout.on("data", (value) => {
  stdout += value;
});
server.stderr.on("data", (value) => {
  stderr += value;
});
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
    server.once("exit", (code) => {
      clearTimeout(timer);
      reject(Error(`Worker exited ${code}: ${stderr}`));
    });
    inspect();
  });
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  page = await browser.newPage({ viewport: { width: 1540, height: 1100 } });
  page.on("pageerror", (error) => errors.push(String(error.stack)));
  await page.goto(ready.observer + "/graph?lang=en");
  await page.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
  await page.click("#show-all");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  await page.locator("#node-search").fill("Grant result");
  await page.locator("#node-search").press("Enter");
  await page.waitForFunction(() => graphDebug.graph.byId.has("rule_fact"));
  await page.locator("#node-search").fill("");
  await page.locator('#semantic [data-node-id="rule_fact"]').evaluate((element) => element.click());
  await page.selectOption("#capture-mode", "focused");
  await page.selectOption(".trace-scope", "all");
  await page.click("#record-start");
  await page.waitForFunction(() => !document.querySelector("#record-stop").disabled);
  const listing = await (await page.request.get(ready.observer + "/api/recordings")).json();
  const identifier = listing.active.id;
  assert.deepEqual(listing.active.capture.nodes, ["rule_fact"]);
  await Promise.all(
    ["alice", "bob"].map(async (actor) => {
      assert.ok((await page.request.post(`${ready.application}/begin?actor=${actor}`)).ok());
    }),
  );
  await page.waitForFunction(
    () =>
      graphDebug.timeline?.invocationGroups === 2 &&
      graphDebug.timeline.unassignedObservations === 0,
  );
  await page.click(".trace-maximize");
  await page.screenshot({ path: path.join(out, "focused-concurrent.png") });
  await page.request.post(ready.application + "/release");
  let actual;
  for (let attempt = 0; attempt < 60; attempt++) {
    actual = await (await page.request.get(ready.application)).json();
    if (
      actual.results.alice === "done" &&
      actual.results.bob === "done" &&
      actual.health.pending === 0
    )
      break;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  assert.deepEqual(actual.recipients, ["alice", "bob"]);
  assert.equal(actual.health.errors, 0);
  assert.equal(
    actual.closure.valid,
    false,
    "Partial metadata cannot pass a complete-run acceptance",
  );
  assert.ok(actual.closure.errors.some((error) => error.partial_boundary_in_complete_run));
  await page.click("#record-stop");
  await page.waitForFunction(() => graphDebug.timeline?.source === "saved");
  await page.selectOption("#replay-grain", "events");
  await page.click(".trace-fit");
  const recording = await (
    await page.request.get(ready.observer + "/api/recordings/" + identifier)
  ).json();
  const trace = await page.evaluate(() => graphDebug.timeline);
  const boundaries = recording.events.filter((event) => event.context_only);
  const facts = recording.events.filter((event) => !event.context_only);
  const byId = new Map(
    [...recording.context.events, ...recording.events].map((event) => [event.id, event]),
  );
  assert.equal(facts.length, 4);
  assert.ok(facts.every((event) => event.node === "rule_fact" && event.outputs.allowed === true));
  assert.ok(facts.every((event) => byId.get(event.parent_event_id)?.phase === "enter"));
  assert.ok(boundaries.length > 0);
  assert.ok(
    boundaries.every(
      (event) => Object.keys(event.inputs).length === 0 && Object.keys(event.outputs).length === 0,
    ),
  );
  assert.ok(
    boundaries.every((event) => event.node !== "query"),
    "Unrelated completed calls are pruned",
  );
  assert.equal(trace.invocationGroups, 2);
  assert.equal(trace.unassignedObservations, 0);
  assert.equal(await page.locator("#replay-events option").count(), 6);
  assert.deepEqual(recording.gaps, []);
  const stopped = await (await page.request.get(ready.application)).json();
  assert.equal(stopped.capture_nodes, null);
  await page.screenshot({ path: path.join(out, "focused-completed.png") });
  assert.deepEqual(errors, []);
  await writeFile(path.join(out, "recording.json"), JSON.stringify(recording, null, 2));
  await writeFile(path.join(out, "timeline.json"), JSON.stringify(trace, null, 2));
  const result = {
    passed: true,
    actual,
    selectedFacts: facts.length,
    realBoundaries: boundaries.length,
    invocationBands: trace.invocationGroups,
    unassigned: trace.unassignedObservations,
    replaySteps: 6,
    errors,
  };
  await writeFile(path.join(out, "result.json"), JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
} catch (error) {
  await page?.screenshot({ path: path.join(out, "failure.png") }).catch(() => {});
  const trace = await page?.evaluate(() => window.graphDebug?.timeline).catch(() => null);
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify(
      { passed: false, error: String(error.stack), trace, stdout, stderr, errors },
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
