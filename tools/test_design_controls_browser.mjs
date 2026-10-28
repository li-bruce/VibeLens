/** Exercise the actual declaration-only server before a business implementation exists. */
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(
  process.env.BO_DESIGN_CONTROL_EVIDENCE || ".validation/conversation-controls/design-browser",
);
const project = path.join(output, "project");
await mkdir(project, { recursive: true });
const document = JSON.parse(
  await readFile("skills/vibelens/assets/discovery.example.json", "utf8"),
);
document.project_id = document.layout_id = "design-control-browser";
const original = JSON.stringify(document);
await writeFile(path.join(project, "discovery.json"), original);
await writeFile(
  path.join(project, "sync.json"),
  JSON.stringify({ model: "behavior.json", discovery: "discovery.json" }),
);
const python = path.resolve(
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const server = spawn(
  python,
  [
    "-B",
    "-X",
    "utf8",
    "skills/vibelens/scripts/bo_web.py",
    "serve",
    "--root",
    project,
    "--port",
    "0",
  ],
  { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] },
);
const base = await new Promise((resolve, reject) => {
  let text = "";
  server.stdout.on("data", (chunk) => {
    text += chunk;
    if (text.includes("\n"))
      resolve(
        text
          .split("\n")[0]
          .trim()
          .split(" ")
          .at(-1)
          .replace(/\/graph$/, ""),
      );
  });
  server.once("exit", (code) => reject(Error("Design server stopped: " + code)));
});
const dialogue = [],
  errors = [];
let browser,
  passed = false;
function cli(action, message, extra = []) {
  const result = spawnSync(
    python,
    [
      "-B",
      "-X",
      "utf8",
      "skills/vibelens/scripts/bo_control.py",
      action,
      "--root",
      project,
      "--url",
      base,
      "--message",
      message,
      ...extra,
    ],
    {
      encoding: "utf8",
      windowsHide: true,
      env: { ...process.env, CODEX_THREAD_ID: "design-control-browser" },
    },
  );
  const value = JSON.parse(result.stdout);
  dialogue.push({ action, message, exit_code: result.status, result: value });
  return value;
}
try {
  const active = cli("activate", "$vibelens for this project");
  assert.equal(active.valid, true);
  const inspected = cli("inspect", "/vibelens show the draft graph");
  assert.equal(inspected.valid, true);
  assert.deepEqual(inspected.result.recordings, []);
  const anchor = inspected.result.nodes.find((node) => node.kind === "action").id;
  const specPath = path.join(output, "request.json");
  const spec = {
    action: "view",
    label: "Draft focus",
    anchors: [anchor],
    depth: 1,
    nodes: ["business", "decision", "data"],
    edges: ["flow", "guard", "data"],
    layout: "layered",
  };
  await writeFile(specPath, JSON.stringify(spec));
  const applied = cli("apply", "/vibelens focus upload and its adjacent steps", [
    "--spec",
    specPath,
  ]);
  assert.equal(applied.valid, true);
  browser = await chromium.launch({
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
    ...(process.env.BO_BROWSER_EXECUTABLE
      ? { executablePath: process.env.BO_BROWSER_EXECUTABLE }
      : {}),
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 400) errors.push(response.status() + " " + response.url());
  });
  await page.goto(active.result.graph_url + "&lang=en");
  await page.waitForFunction(
    (id) => document.body.dataset.controlPlan === id,
    applied.result.plan.id,
  );
  await page.waitForFunction(() => !graphDebug.layoutBusy && graphDebug.graph?.boxes.length > 0);
  assert.ok(
    await page.evaluate((id) => graphDebug.graph.boxes.some((box) => box.id === id), anchor),
  );
  await page.screenshot({ path: path.join(output, "design-focus.png") });
  await page.click("#layered-toggle");
  await page.waitForFunction(() => graphDebug.spatial?.perspective && !graphDebug.layoutBusy);
  await page.screenshot({ path: path.join(output, "design-3d.png") });
  const view = await (await fetch(base + "/api/view")).json();
  assert.equal(view.stage, "design");
  assert.deepEqual(view.events, []);
  assert.equal(view.machine.current, null);
  assert.equal(await readFile(path.join(project, "discovery.json"), "utf8"), original);
  await assert.rejects(readFile(path.join(project, "behavior.json")));
  await writeFile(specPath, JSON.stringify({ ...spec, action: "replay" }));
  const rejected = cli("apply", "/vibelens replay this draft", [
    "--spec",
    specPath,
    "--recording",
    "absent",
  ]);
  assert.equal(rejected.valid, false);
  assert.match(rejected.error, /no runtime recordings/);
  assert.deepEqual(errors, []);
  passed = true;
} finally {
  await writeFile(
    path.join(output, "dialogue.json"),
    JSON.stringify({ kind: "scripted-controls-against-real-design-server", dialogue }, null, 2),
  );
  await writeFile(path.join(output, "result.json"), JSON.stringify({ passed, errors }, null, 2));
  await browser?.close();
  server.kill();
}
assert.equal(passed, true);
console.log(
  "PASS: actual pre-code design server, scoped control, 2D/3D, unchanged declarations and no fabricated runtime facts",
);
