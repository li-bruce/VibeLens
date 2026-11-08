/** Real canonical viewer + SQLite application, including live source edits. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, writeFile, unlink } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { analysisPreferences, waitForPreferences } from "./browser-preferences.mjs";
const { chromium } = createRequire(import.meta.url)("playwright");
const root = fileURLToPath(new URL("../", import.meta.url));
const output = path.resolve(
  process.env.BO_BROWSER_EVIDENCE || path.join(root, "docs/review/code-vis"),
);
await mkdir(output, { recursive: true });
const port = process.env.BO_BROWSER_PORT || "8871",
  base = `http://127.0.0.1:${port}`;
const python =
  process.env.BO_PYTHON ||
  path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const server = spawn(python, ["-B", "-X", "utf8", "tools/database_demo.py", "--port", port], {
  cwd: root,
  windowsHide: true,
  stdio: ["ignore", "pipe", "pipe"],
});
let logs = "",
  browser,
  page;
const errors = [],
  checkpoints = {};
const pendingRequests = new Set();
server.stdout.on("data", (s) => (logs += s));
server.stderr.on("data", (s) => (logs += s));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function api(route, body) {
  const response = await fetch(
    base + route,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const data = await response.json();
  assert.ok(response.ok, JSON.stringify(data));
  return data;
}
async function pick(id) {
  // Search reveals current containment ancestors instead of assuming that one
  // global expansion reaches every declaration in the engineering tree.
  if (!(await page.locator(`#semantic [data-node-id="${id}"]`).count())) {
    await page.fill("#node-search", id);
    await page.locator("#node-search").press("Enter");
    await page.waitForFunction((key) => graphDebug.graph.byId.has(key), id);
    await page.fill("#node-search", "");
  }
  await page
    .locator("#semantic [data-node-id]")
    .evaluateAll((nodes, id) => nodes.find((n) => n.dataset.nodeId === id).click(), id);
}
async function shot(name) {
  await page.screenshot({ path: path.join(output, name + ".png"), fullPage: true });
}
async function menuClick(selector) {
  await page.locator("#viewport").focus();
  await page.keyboard.press("Shift+F10");
  await page.click(selector);
}
try {
  for (let i = 0; i < 80; i++) {
    try {
      await api("/api/bo/health");
      break;
    } catch {
      await sleep(250);
    }
  }
  const launch = { headless: true, args: ["--enable-unsafe-swiftshader"] };
  if (process.env.BO_BROWSER_EXECUTABLE) launch.executablePath = process.env.BO_BROWSER_EXECUTABLE;
  browser = await chromium.launch(launch);
  page = await browser.newPage({ viewport: { width: 1550, height: 1040 } });
  page.on("request", (r) => pendingRequests.add(r.url()));
  page.on("requestfinished", (r) => pendingRequests.delete(r.url()));
  page.on("requestfailed", (r) => pendingRequests.delete(r.url()));
  await page.route("**/api/design", (route) =>
    route.fulfill({
      json: {
        available: true,
        revision: "browser-discussion-1",
        stale: false,
        nodes: ["publish"],
        label: "Publish pictures",
      },
    }),
  );
  page.on("pageerror", (e) => errors.push(e.message));
  let codeRequests = 0,
    sourceRequests = 0;
  page.on("request", (r) => {
    if (r.url().includes("/api/code/graph")) codeRequests++;
    if (/\/api\/(?:code\/)?source\?/.test(r.url())) sourceRequests++;
  });
  await page.goto(base + "/graph?lang=en");
  if (process.env.BO_SPATIAL_TEST === "1") {
    await page.waitForFunction(() => window.graphDebug?.graph);
    await page.click("#layered-toggle");
    await page.waitForFunction(() => graphDebug.spatial?.perspective && !graphDebug.layoutBusy);
    checkpoints.real3D = true;
  }
  await page.waitForSelector('#semantic [data-node-id="publish"]', { state: "attached" });
  await page.waitForTimeout(1100);
  assert.equal(codeRequests, 0, "default overview must not construct a code index");
  assert.equal(sourceRequests, 0, "Full source is loaded only when opened");
  await shot("01-default-overview");
  await pick("publish");
  await page.click("#code-local");
  await page.waitForSelector('#semantic [data-node-type="code-function"]', { state: "attached" });
  await page.click("#fit");
  assert.ok(await page.locator('#semantic-edges [data-relation-type="code-maps"]').count());
  checkpoints.focus = await api("/api/code/graph?focus=publish");
  assert.ok(checkpoints.focus.edges.some((e) => e.code_relation === "calls"));
  await shot("02-business-to-code");
  await page.click("#code-local");
  await page.waitForFunction(
    () => !document.querySelector('#semantic [data-node-type="code-function"]'),
  );
  await page.selectOption("#analysis-view", "code");
  await page.waitForSelector('#semantic [data-node-type="code-file"]', { state: "attached" });
  await page.click("#expand");
  await page.click("#fit");
  checkpoints.all = await api("/api/code/graph");
  const parameter = checkpoints.all.nodes.find(
    (n) => n.code_role === "parameter" && n.label === "rows",
  );
  const parameterParent = checkpoints.all.nodes.find((n) => n.id === parameter.parent);
  await pick(parameterParent.id);
  await menuClick("#node-expand");
  await pick(parameter.id);
  await menuClick("#source");
  await page.waitForFunction(() =>
    document.getElementById("source-code").textContent.includes("rows"),
  );
  assert.match(await page.locator("#source-code").innerText(), /\d+\s+def/);
  assert.match(await page.locator("#source-code").innerText(), /def publish/);
  assert.match(await page.locator("#source-code").innerText(), /metadata = MetaData/);
  assert.equal(await page.locator("#source-code mark").first().innerText(), "rows");
  checkpoints.fullFileParameterHighlight = true;
  await shot("03-full-file-parameter-highlight");
  assert.equal(sourceRequests, 1);
  await page.click("#close-detail");

  const file = checkpoints.all.nodes.find(
    (n) => n.code_role === "file" && n.label === "gallery.py",
  );
  await pick(file.id);
  await menuClick("#pin");
  await menuClick("#annotate");
  await page.fill("#node-note", "Review this file after each schema change");
  // The selected view may already be saved. Require a newer acknowledgment
  // carrying this annotation before a reload can test durable restoration.
  const beforeAnnotation = await api("/api/preferences");
  const annotationSaved = waitForPreferences(
    page,
    (document) => {
      const analysis = analysisPreferences(document);
      return (
        analysis?.selected === "code" &&
        analysis.annotations?.[file.id]?.note === "Review this file after each schema change"
      );
    },
    {
      afterRevision: beforeAnnotation.revision,
      description: "code view and file annotation",
    },
  );
  await page.locator('#annotation-form button[type="submit"]').click();
  const annotationAcknowledgment = await annotationSaved;
  await page.reload();
  await page.waitForSelector('#semantic [data-node-type="code-file"]', {
    state: "attached",
  });
  const discussionAcknowledgment = await waitForPreferences(
    page,
    (document) => analysisPreferences(document)?.discussion?.active === true,
    { description: "restored active discussion" },
  );
  assert.equal(await page.locator("#discussion-bar").count(), 0);
  assert.equal(
    await page.inputValue("#analysis-view"),
    "code",
    "an existing discussion must not override the saved code view",
  );
  checkpoints.discussionReloadPreservesView = true;
  const discussionDismissed = waitForPreferences(
    page,
    (document) => {
      const analysis = analysisPreferences(document);
      return analysis?.selected === "code" && analysis.discussion?.active === false;
    },
    {
      afterRevision: discussionAcknowledgment.revision,
      description: "dismissed discussion in the code view",
    },
  );
  await page.locator("#viewport").focus();
  await page.keyboard.press("Escape");
  const dismissalAcknowledgment = await discussionDismissed;
  checkpoints.preferenceAcknowledgments = {
    beforeAnnotation: beforeAnnotation.revision,
    annotation: annotationAcknowledgment.revision,
    restoredDiscussion: discussionAcknowledgment.revision,
    dismissedDiscussion: dismissalAcknowledgment.revision,
  };
  await page.reload();
  await page.waitForSelector('#semantic [data-node-type="code-file"]', {
    state: "attached",
  });
  assert.equal(await page.inputValue("#analysis-view"), "code");
  assert.equal(await page.locator('#semantic [data-discussion="true"]').count(), 0);
  checkpoints.dismissedDiscussionSurvivesReload = true;
  await page.waitForTimeout(900);
  checkpoints.layoutBefore = await page
    .locator("#semantic [data-node-id]")
    .evaluateAll(
      (nodes, id) => ({ ...nodes.find((n) => n.dataset.nodeId === id).dataset }),
      file.id,
    );
  await shot("03-complete-code-view");
  await page.reload();
  await page.waitForSelector('#semantic [data-node-type="code-function"]', { state: "attached" });
  await pick(file.id);
  await menuClick("#annotate");
  assert.equal(await page.inputValue("#node-note"), "Review this file after each schema change");
  await page.locator('#annotation-form button[type="submit"]').click();
  await menuClick("#source");
  await page.waitForFunction(() =>
    document.getElementById("source-code").textContent.includes("def publish"),
  );
  await page.click("#close-detail");
  checkpoints.sourceFetchedOnDemand = true;
  const projectPath = logs.match(/Disposable application: (.+)/)?.[1].trim();
  assert.ok(projectPath, logs);
  const added = path.join(projectPath, "new_feature.py");
  await writeFile(added, "def newly_added(value):\n    return value\n");
  await page.waitForFunction(() =>
    [...document.querySelectorAll("#semantic [data-node-id]")].some((n) =>
      n.textContent.includes("new_feature.py"),
    ),
  );
  checkpoints.added = await api("/api/code/graph");
  assert.notEqual(checkpoints.all.revision, checkpoints.added.revision);
  await shot("04-new-file-auto-refresh");
  const routeFile = path.join(projectPath, "api_sample.py");
  await writeFile(
    routeFile,
    "from fastapi import FastAPI\napp = FastAPI()\n@app.post('/pictures')\ndef upload(name: str):\n    return name\n@app.get('/api/view')\ndef observer_view():\n    return {}\n",
  );
  await page.waitForSelector('#semantic [data-node-type="code-endpoint"]', { state: "attached" });
  checkpoints.api = await api("/api/code/graph");
  const endpoint = checkpoints.api.nodes.find((n) => n.code_role === "endpoint");
  assert.equal(endpoint.label, "POST /pictures");
  assert.equal(checkpoints.api.nodes.filter((n) => n.code_role === "endpoint").length, 1);
  assert.ok(await page.locator('#semantic-edges [data-relation-type="code-handles"]').count());
  await page.selectOption("#analysis-view", "api");
  await page.waitForSelector('#semantic [data-node-type="code-endpoint"]', { state: "attached" });
  await pick(endpoint.id);
  if ((await page.getAttribute("#layered-toggle", "aria-pressed")) !== "true")
    await page.click("#layered-toggle");
  {
    const planeControl = await page.locator("#layer-controls canvas").boundingBox();
    await page.mouse.click(planeControl.x + planeControl.width - 13, planeControl.y + 17);
  }
  const layerIds = await page
    .locator("#layer-controls button[data-layer]")
    .evaluateAll((items) => items.map((e) => e.dataset.layer));
  for (const id of layerIds)
    if (id !== "api") {
      const box = await page.locator("#layer-controls canvas").boundingBox();
      const order = await page.evaluate(() => graphDebug.layers.order);
      await page.mouse.click(box.x + 22, box.y + 40 + order.indexOf(id) * 34 + 17);
    }
  await page.click("#fit");
  await page.waitForFunction(
    () =>
      graphDebug.spatial?.perspective && graphDebug.spatial.frames > 0 && !graphDebug.layoutBusy,
  );
  assert.ok(
    await page.evaluate(() =>
      [...document.querySelectorAll("#semantic [data-node-id]")].every(
        (n) => n.dataset.plane === "api",
      ),
    ),
  );
  await shot("04-api-registration-layer");
  {
    const planeControl = await page.locator("#layer-controls canvas").boundingBox();
    await page.mouse.click(planeControl.x + planeControl.width - 13, planeControl.y + 17);
  }
  if (process.env.BO_SPATIAL_TEST !== "1") await page.click("#layered-toggle");
  await unlink(routeFile);
  await page.waitForFunction(
    () => !document.querySelector('#semantic [data-node-type="code-endpoint"]'),
  );
  await page.selectOption("#analysis-view", "code");

  await writeFile(added, "def invalid(:\n");
  await page.waitForFunction(() =>
    document.getElementById("code-status").textContent.includes("incomplete"),
  );
  checkpoints.parseFailure = await api("/api/code/graph");
  assert.equal(checkpoints.parseFailure.status, "incomplete");
  await shot("05-parser-error-is-visible");
  await unlink(added);
  await page.waitForFunction(
    () => !document.getElementById("code-status").textContent.includes("incomplete"),
  );
  const before = await api("/api/view");
  for (let i = 0; i < 3; i++) await api("/api/code/graph?focus=publish");
  assert.equal((await api("/api/view")).events.length, before.events.length);
  await page.selectOption("#analysis-view", "data-operations");
  await page.click("#record-start");
  await page.waitForFunction(() => !document.getElementById("record-stop").disabled);
  checkpoints.run = await api("/demo/run", {});
  assert.equal(checkpoints.run.stored, 7);
  await page.click("#record-stop");
  await page.waitForFunction(() => !document.getElementById("replay").hidden);
  checkpoints.replaySourceOption = await page
    .locator('#analysis-view option[value="code"]')
    .evaluate((n) => ({ disabled: n.disabled, html: n.outerHTML }));
  checkpoints.servedReplayGuard = (await (await fetch(base + "/viewer.js")).text()).includes(
    "replayReturnAnalysis",
  );
  assert.equal(
    checkpoints.replaySourceOption.disabled,
    true,
    "recorded frames must not offer a current-source-only view",
  );
  checkpoints.recordedCodeUnavailable = true;
  await page.click("#replay-live");
  await page.waitForFunction(
    () => !document.querySelector('#analysis-view option[value="code"]').disabled,
  );
  await page.selectOption("#analysis-view", "code");
  await page.waitForSelector('#semantic [data-node-type="code-file"]', { state: "attached" });
  const savedRecording = await page.locator("#record-list option").nth(1).getAttribute("value");
  const recordedContext = (await api("/api/recordings/" + savedRecording)).context;
  const replayReadiness = () =>
    page.evaluate(() => ({
      historical: graphDebug.view.historical,
      recording: graphDebug.view.replay?.id || null,
      analysis: document.getElementById("analysis-view").value,
      codeDisabled: document.querySelector('#analysis-view option[value="code"]').disabled,
      layoutBusy: graphDebug.layoutBusy,
      connection: document.getElementById("connection").textContent,
      sourceOptions: [...document.getElementById("analysis-view").options].map((option) => ({
        value: option.value,
        disabled: option.disabled,
        selected: option.selected,
      })),
      sourceContext: {
        codeStructure: graphDebug.view.code_structure || null,
        projectRevision: graphDebug.view.project_structure?.revision || null,
        modelRevision: graphDebug.view.model.revision,
      },
    }));
  checkpoints.recordedReadinessBefore = await replayReadiness();
  await page.selectOption("#record-list", savedRecording);
  // The source menu updates before its asynchronous graph projection. Inspect
  // the completed recorded overview. Its captured engineering tree legitimately
  // reuses file glyphs; the current-source AST is the part excluded from replay.
  await page.waitForFunction(
    (id) =>
      graphDebug.view.historical === true &&
      graphDebug.view.replay?.id === id &&
      !document.getElementById("replay").hidden &&
      document.getElementById("analysis-view").value === "overview" &&
      !graphDebug.layoutBusy &&
      ![...graphDebug.graph.all.values()].some((node) =>
        ["function", "parameter", "class"].includes(node.code_role),
      ) &&
      document.querySelector("#semantic [data-node-id]"),
    savedRecording,
  );
  checkpoints.recordedReadinessAfter = await replayReadiness();
  assert.equal(await page.inputValue("#analysis-view"), "overview");
  checkpoints.recordedCodeOption = await page
    .locator('#analysis-view option[value="code"]')
    .evaluate((option) => ({ disabled: option.disabled, html: option.outerHTML }));
  assert.equal(checkpoints.recordedCodeOption.disabled, true);
  const recordedProjection = await page.evaluate(() => {
    const graph = graphDebug.graph;
    const visible = new Set(
      [...document.querySelectorAll("#semantic [data-node-id]")].map((node) => node.dataset.nodeId),
    );
    return {
      files: [...graph.all.values()].filter((node) =>
        ["file", "directory"].includes(node.code_role),
      ),
      visibleFiles: [...graph.all.values()].filter(
        (node) => visible.has(node.id) && ["file", "directory"].includes(node.code_role),
      ),
      astNodes: [...graph.all.values()].filter((node) =>
        ["function", "parameter", "class"].includes(node.code_role),
      ),
      astCalls: graph.rawEdges.filter((edge) => edge.code_relation === "calls"),
      projectRelations: graph.edges.flatMap((edge) =>
        (edge.members || [edge]).filter((member) =>
          [member.from, member.to].some((id) =>
            ["file", "directory"].includes(graph.all.get(id)?.code_role),
          ),
        ),
      ),
    };
  });
  checkpoints.recordedProjection = recordedProjection;
  assert.equal(recordedProjection.astNodes.length, 0, "replay must not merge the current AST");
  assert.equal(recordedProjection.astCalls.length, 0, "replay must not merge current AST calls");
  const nodeIdentity = (node) => ({
    id: node.id,
    layer: node.layer,
    role: node.code_role,
    parent: node.parent || null,
    // JSON snapshots have no undefined properties; the renderer may add an
    // optional end_line with that value while normalizing a source reference.
    source: node.source ? JSON.parse(JSON.stringify(node.source)) : null,
  });
  const edgeIdentity = (edge) => ({
    id: edge.id,
    from: edge.from,
    to: edge.to,
    type: edge.type || null,
    relation: edge.code_relation || null,
    origin: edge.origin || null,
  });
  const capturedFiles = recordedContext.project_structure.nodes.filter((node) =>
    ["file", "directory"].includes(node.code_role),
  );
  assert.deepEqual(
    recordedProjection.files.map(nodeIdentity).sort((a, b) => a.id.localeCompare(b.id)),
    capturedFiles.map(nodeIdentity).sort((a, b) => a.id.localeCompare(b.id)),
    "the complete engineering inventory belongs to this recording's exact snapshot",
  );
  const capturedNodes = new Map(capturedFiles.map((node) => [node.id, node]));
  for (const node of recordedProjection.visibleFiles)
    assert.deepEqual(nodeIdentity(node), nodeIdentity(capturedNodes.get(node.id)));
  const capturedEdges = new Map(
    recordedContext.project_structure.edges.map((edge) => [edge.id, edge]),
  );
  // Folding projects a link onto visible ancestors; its members keep the exact
  // captured endpoints. Check every displayed member, rather than its label.
  for (const edge of recordedProjection.projectRelations) {
    assert.ok(capturedEdges.has(edge.id), "a displayed engineering relation must be captured");
    assert.deepEqual(edgeIdentity(edge), edgeIdentity(capturedEdges.get(edge.id)));
  }
  assert.ok(await page.locator("#semantic [data-node-id]").count());
  await shot("07-recorded-overview");
  await page.click("#replay-live");
  await page.waitForFunction(() => document.getElementById("analysis-view").value === "code");
  await page.waitForSelector('#semantic [data-node-type="code-file"]', { state: "attached" });
  checkpoints.liveCodeRestored = true;
  // The new collector reads a small live-history limit. Recording listeners
  // must still receive every event from the next real SQLite operation.
  const retentionPath = path.join(projectPath, "bo_stategraph/config/retention.json");
  await mkdir(path.dirname(retentionPath), { recursive: true });
  await writeFile(
    retentionPath,
    JSON.stringify({ memory_events: 2, memory_seconds: 1800, log_bytes: 8388608, log_backups: 2 }),
  );
  await api("/demo/upgrade", {});
  await page.waitForFunction(() => document.getElementById("record-list").options.length === 1);
  await page.selectOption("#analysis-view", "code");
  await page.waitForSelector('#semantic [data-node-type="code-file"]', { state: "attached" });
  checkpoints.layoutAfter = await page
    .locator("#semantic [data-node-id]")
    .evaluateAll(
      (nodes, id) => ({ ...nodes.find((n) => n.dataset.nodeId === id).dataset }),
      file.id,
    );
  assert.equal(checkpoints.layoutAfter.x, checkpoints.layoutBefore.x);
  assert.equal(checkpoints.layoutAfter.y, checkpoints.layoutBefore.y);
  assert.equal(checkpoints.layoutAfter.pinned, "true");
  await pick(file.id);
  await menuClick("#annotate");
  assert.equal(await page.inputValue("#node-note"), "Review this file after each schema change");
  await page.locator('#annotation-form button[type="submit"]').click();
  await page.selectOption("#language", "zh-CN");
  await page.waitForFunction(() =>
    document.getElementById("code-status").textContent.includes("代码"),
  );
  await shot("06-updated-code-zh");
  checkpoints.final = await api("/api/code/graph");
  assert.equal(checkpoints.final.status, "current");
  await api("/api/recordings/start", { label: "Real SQLite operations across live retention" });
  await api("/demo/run", {});
  checkpoints.retentionHealth = (await api("/api/view")).health;
  assert.ok(checkpoints.retentionHealth.evicted_events > 0);
  assert.equal(checkpoints.retentionHealth.dropped, 0);
  await page.waitForFunction(() =>
    document.getElementById("connection").textContent.includes("历史事件已过期"),
  );
  assert.ok(!(await page.locator("#connection").textContent()).includes("缺失"));
  await shot("08-retention-zh");
  await page.selectOption("#language", "en");
  await page.waitForFunction(() =>
    document.getElementById("connection").textContent.includes("earlier events expired"),
  );
  await shot("09-retention-en");
  const retainedStop = await api("/api/recordings/stop", {});
  const retainedRecording = await api("/api/recordings/" + retainedStop.id);
  assert.equal(
    retainedRecording.events.length,
    retainedRecording.end_seq - retainedRecording.start_seq,
  );
  assert.deepEqual(retainedRecording.gaps, []);
  checkpoints.retentionRecording = {
    events: retainedRecording.events.length,
    gaps: retainedRecording.gaps,
    start_seq: retainedRecording.start_seq,
    end_seq: retainedRecording.end_seq,
  };
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(output, "browser-result.json"),
    JSON.stringify({ passed: true, errors, checkpoints }, null, 2),
  );
  console.log(
    "PASS: lazy/focused/full code views, relationships, source, live edits/errors/deletion, persistence, exclusion, real recording and bilingual reload.",
  );
} catch (error) {
  checkpoints.replayReadinessOnFailure = await page
    ?.evaluate(() => ({
      historical: graphDebug.view?.historical,
      recording: graphDebug.view?.replay?.id || null,
      analysis: document.getElementById("analysis-view")?.value,
      codeDisabled: document.querySelector('#analysis-view option[value="code"]')?.disabled,
      layoutBusy: graphDebug.layoutBusy,
    }))
    .catch(() => null);
  checkpoints.pendingRequests = [...pendingRequests];
  checkpoints.url = page?.url();
  checkpoints.document = await page
    ?.evaluate(() => ({
      ready: document.readyState,
      resources: performance
        .getEntriesByType("resource")
        .map((r) => ({ name: r.name, duration: r.duration })),
    }))
    .catch(() => null);
  if (page) await shot("failure");
  if (page)
    checkpoints.codeStatus = await page
      .locator("#code-status")
      .evaluate((n) => ({ text: n.textContent, detail: n.title }))
      .catch(() => null);
  await writeFile(
    path.join(output, "browser-result.json"),
    JSON.stringify(
      { passed: false, error: String(error.stack), errors, checkpoints, logs },
      null,
      2,
    ),
  );
  throw error;
} finally {
  await browser?.close();
  try {
    await api("/demo/stop", {});
  } catch {}
  if (server.exitCode === null) server.kill();
  await writeFile(path.join(output, "server.log"), logs);
}
