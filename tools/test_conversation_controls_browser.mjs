/** Use prefixed dialogue requests against the real control API and native viewer. */
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(
  process.env.BO_CONTROL_EVIDENCE || ".validation/conversation-controls/browser",
);
const project = path.join(output, "project");
await mkdir(project, { recursive: true });
const python = path.resolve(
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const server = spawn(python, ["-B", "-X", "utf8", "tools/serve_control_case.py", project], {
  windowsHide: true,
  stdio: ["ignore", "pipe", "pipe"],
});
const info = await new Promise((resolve, reject) => {
  let text = "";
  server.stdout.on("data", (chunk) => {
    text += chunk;
    if (text.includes("\n")) resolve(JSON.parse(text.split("\n")[0]));
  });
  server.once("exit", (code) => reject(Error("Fixture stopped: " + code)));
});
const dialogue = [],
  errors = [];
let browser,
  page,
  passed = false;
function cli(command, message, more = [], thread = "control-browser-a") {
  const result = spawnSync(
    python,
    [
      "-B",
      "-X",
      "utf8",
      "skills/vibelens/scripts/bo_control.py",
      command,
      "--root",
      project,
      "--url",
      info.url,
      "--message",
      message,
      ...more,
    ],
    { encoding: "utf8", windowsHide: true, env: { ...process.env, CODEX_THREAD_ID: thread } },
  );
  const value = JSON.parse(result.stdout);
  dialogue.push({ speaker: "user", message, command, exit_code: result.status, result: value });
  return value;
}
try {
  const activation = cli("activate", "$vibelens for this project");
  assert.equal(activation.valid, true);
  const session = activation.result.session;
  assert.equal(cli("status", "/vibelens status", [], "control-browser-b").valid, false);
  browser = await chromium.launch({
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
    ...(process.env.BO_BROWSER_EXECUTABLE
      ? { executablePath: process.env.BO_BROWSER_EXECUTABLE }
      : {}),
  });
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text() + " @ " + message.location().url);
  });
  page.on("response", (response) => {
    if (response.status() >= 400) errors.push(response.status() + " " + response.url());
  });
  await page.goto(activation.result.graph_url + "&lang=en");
  await page.waitForFunction(() => window.graphDebug?.graph?.boxes.length > 0);
  const peer = await browser.newPage({ viewport: { width: 1000, height: 800 } });
  await peer.goto(info.url + "/graph?lang=en");
  await peer.waitForFunction(() => window.graphDebug?.graph?.boxes.length > 0);
  await page.waitForTimeout(500);
  const peerBefore = await peer.evaluate(() => ({
    nodes: graphDebug.graph.boxes.map((box) => box.id).sort(),
    view: document.querySelector("#analysis-view").value,
  }));
  const originalEvents = await page.evaluate(
    async () => (await (await fetch("/api/view")).json()).events,
  );
  const specFile = path.join(output, "request.json");
  await writeFile(
    specFile,
    JSON.stringify({
      action: "view",
      label: "Upload and approval",
      anchors: ["upload", "publish"],
      depth: 0,
      direction: "forward",
      nodes: ["business"],
      edges: ["flow"],
      layout: "layered",
    }),
  );
  assert.equal(cli("apply", "只看上传和审核", ["--spec", specFile]).valid, false);
  const applied = cli("apply", "/vibelens 只看上传到审核的主要过程，保留业务节点和流程关系", [
    "--spec",
    specFile,
  ]);
  assert.equal(applied.valid, true);
  await page.waitForFunction(
    (id) => document.body.dataset.controlPlan === id,
    applied.result.plan.id,
  );
  let status;
  for (let i = 0; i < 30; i++) {
    status = cli("status", "/vibelens status");
    if (status.result.result?.status === "applied") break;
    await page.waitForTimeout(150);
  }
  assert.equal(status.result.result.status, "applied");
  assert.deepEqual(await page.evaluate(() => graphDebug.graph.boxes.map((box) => box.id).sort()), [
    "publish",
    "review",
    "upload",
  ]);
  assert.ok(await page.evaluate(() => graphDebug.graph.edges.length >= 2));
  await page.screenshot({ path: path.join(output, "business-view.png") });
  assert.deepEqual(
    await peer.evaluate(() => ({
      nodes: graphDebug.graph.boxes.map((box) => box.id).sort(),
      view: document.querySelector("#analysis-view").value,
    })),
    peerBefore,
  );
  const viewId = status.result.result.view_id;
  await page.reload();
  await page.waitForFunction(
    (id) =>
      document.querySelector("#analysis-view")?.value === id &&
      graphDebug.graph?.boxes.length === 3,
    viewId,
  );
  await page.click("#layered-toggle");
  await page.waitForFunction(() => graphDebug.spatial?.perspective && !graphDebug.layoutBusy);
  assert.deepEqual(await page.evaluate(() => graphDebug.graph.boxes.map((box) => box.id).sort()), [
    "publish",
    "review",
    "upload",
  ]);
  await page.screenshot({ path: path.join(output, "business-3d.png") });
  await writeFile(
    specFile,
    JSON.stringify({
      action: "replay",
      label: "Approval detail",
      anchors: ["review-policy"],
      depth: 1,
      nodes: ["business", "decision", "data", "function"],
      edges: ["flow", "guard", "data", "call"],
      layout: "cluster",
      loop: true,
    }),
  );
  const replay = cli("apply", "/vibelens 在这段记录里只回放审核判定与相邻参数，循环播放", [
    "--spec",
    specFile,
    "--recording",
    info.recording,
  ]);
  assert.equal(replay.valid, true);
  await page.waitForFunction(
    (id) => document.body.dataset.controlPlan === id,
    replay.result.plan.id,
  );
  assert.ok(
    await page.evaluate(() =>
      ["field:review-policy:in:reviewed_version", "field:review-policy:in:current_version"].every(
        (id) => graphDebug.graph.boxes.some((box) => box.id === id),
      ),
    ),
  );
  await page.waitForTimeout(500);
  const selection = await page.evaluate(async (session) => {
    const value = await (await fetch("/api/preferences?vl_session=" + session)).json();
    const analysis = Object.entries(value.entries).find(([key]) => key.endsWith(":analysis"));
    return JSON.parse(analysis[1]);
  }, session);
  assert.equal(selection.replays[info.recording].loop, true);
  assert.ok(selection.replays[info.recording].skipped.length > 0);
  assert.ok(
    replay.result.plan.recording.selected_events < replay.result.plan.recording.total_events,
  );
  assert.deepEqual(
    await page.evaluate(async () => (await (await fetch("/api/view")).json()).events),
    originalEvents,
  );
  await page.click("#replay-play");
  const start = await page.evaluate(() => graphDebug.view.replay.event.id);
  await page.waitForFunction((id) => graphDebug.view.replay?.event?.id !== id, start);
  await page.screenshot({ path: path.join(output, "filtered-replay.png") });
  assert.equal(cli("end", "/vibelens stop").valid, true);
  assert.equal(
    cli("apply", "/vibelens show approval", ["--spec", specFile, "--recording", info.recording])
      .valid,
    false,
  );
  assert.equal(errors.length, 0, errors.join("\n"));
  passed = true;
  console.log(
    "PASS: scoped dialogue controls, original relationships, reload, 2D/3D, replay filter and unchanged events",
  );
} catch (error) {
  await page?.screenshot({ path: path.join(output, "failure.png") });
  throw error;
} finally {
  await writeFile(
    path.join(output, "dialogue.json"),
    JSON.stringify(
      { kind: "scripted-user-requests-through-real-cli-and-browser", dialogue },
      null,
      2,
    ),
  );
  await writeFile(path.join(output, "result.json"), JSON.stringify({ passed, errors }, null, 2));
  await browser?.close();
  server.kill();
}
