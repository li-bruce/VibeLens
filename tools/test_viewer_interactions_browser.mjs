/** Real application + native UI regression for shared graph interactions.
 * Run through test_concept_browser.py. No model or runtime response is stubbed.
 */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { analysisPreferences, waitForPreferences } from "./browser-preferences.mjs";
const { chromium } = createRequire(import.meta.url)("playwright");
const url = process.env.BO_CONCEPT_URL,
  appURL = process.env.BO_CONCEPT_APP_URL;
const out = path.resolve(process.env.BO_CONCEPT_EVIDENCE || ".validation/viewer-interactions");
await mkdir(out, { recursive: true });
const checks = [],
  errors = [];
let browser, page;
const settled = () =>
  page.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy, null, {
    timeout: 30000,
  });
const shot = (name) => page.screenshot({ path: path.join(out, name + ".png") });
async function view(id) {
  await page.selectOption("#analysis-view", id);
  await settled();
  await page.click("#fit");
  await settled();
  assert.deepEqual(
    await page
      .locator("#layer-controls [data-layer][aria-pressed=true]")
      .evaluateAll((buttons) => buttons.map((button) => button.dataset.layer).sort()),
    (await page.evaluate(() => graphDebug.layers.visible)).sort(),
    "Ruler matches the preset",
  );
}
async function allElements() {
  const box = await page.locator("#layer-controls canvas").boundingBox();
  await page.mouse.click(box.x + box.width - 15, box.y + 18);
  await settled();
}
async function toggleLayer(id) {
  const index = await page.evaluate((id) => graphDebug.layers.order.indexOf(id), id);
  const box = await page.locator("#layer-controls canvas").boundingBox();
  await page.mouse.click(box.x + 22, box.y + 40 + index * 34 + 16);
  await settled();
}
async function point(id) {
  // Layout workers finish before the throttled accessible geometry update.
  // Wait for actual screen coordinates instead of dispatching a NaN pointer.
  await page.waitForFunction((id) => {
    const node = [...document.querySelectorAll("#semantic [data-node-id]")].find(
      (element) => element.dataset.nodeId === id,
    );
    return (
      node &&
      [node.dataset.screenX, node.dataset.screenY].every(
        (value) => value !== undefined && Number.isFinite(Number(value)),
      )
    );
  }, id);
  return page.locator("#semantic [data-node-id]").evaluateAll((elements, id) => {
    const node = elements.find((element) => element.dataset.nodeId === id);
    return node && { x: +node.dataset.screenX, y: +node.dataset.screenY };
  }, id);
}
async function drag(a, b) {
  await page.mouse.move(a.x, a.y);
  await page.mouse.down();
  await page.mouse.move(b.x, b.y, { steps: 10 });
  await page.mouse.up();
  await settled();
}
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
    args: ["--enable-unsafe-swiftshader"],
  });
  page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(url);
  await settled();
  if ((await page.locator("#replay-timeline").getAttribute("aria-pressed")) === "true")
    await page.click("#replay-timeline");
  if ((await page.locator("#layered-toggle").innerText()) === "3D")
    await page.click("#layered-toggle");
  for (const [id, layer] of [
    ["business", "business"],
    ["states", "state"],
    ["rules", "rules"],
    ["api", "entry"],
    ["project", "structure"],
    ["code", "symbols"],
    ["database", "data"],
  ]) {
    await view(id);
    const initial = await page.evaluate(() => ({
      layers: graphDebug.layers.visible,
      shown: [...new Set([...graphDebug.presentation.glyphs, ...graphDebug.presentation.regions])],
    }));
    assert.deepEqual(initial.layers, [layer], id);
    assert.ok(initial.shown.length, id + " contains visible application nodes");
    if (id === "code")
      assert.ok(
        await page.evaluate(() =>
          graphDebug.displayGraph.boxes.some(
            (box) => box.node.code_role === "function" && box.node.source?.path === "service.py",
          ),
        ),
        "Hidden file parents cannot swallow application functions",
      );
    await page.click("#collapse");
    await settled();
    await page.click("#fit");
    const candidate = await page.evaluate(
      () =>
        graphDebug.displayGraph.boxes.find(
          (box) => box.kids.length && graphDebug.presentation.glyphs.has(box.id),
        )?.id,
    );
    if (candidate) {
      const p = await point(candidate);
      const before = await page.evaluate(() => graphDebug.camera);
      await page.mouse.dblclick(p.x, p.y);
      await settled();
      const after = await page.evaluate(
        (id) => ({
          camera: graphDebug.camera,
          open: graphDebug.graph.byId.get(id)?.open,
          self: graphDebug.presentation.glyphs.has(id),
          region: graphDebug.presentation.regions.has(id),
        }),
        candidate,
      );
      assert.ok(after.open, id + " expands by double-click");
      assert.deepEqual(after.camera, before, id + " expansion preserves the camera");
      assert.ok(after.region, id + " owner is represented by an enclosure");
      if (id === "project")
        assert.equal(after.self, false, "Directory containment creates no phantom self glyph");
      checks.push({ expansion: id, ...after });
    }
    checks.push({ preset: id, ...initial });
  }
  // Exercise the same containment contract on every populated spatial plane,
  // not only on the business group used by the gesture tests below.
  await page.click("#layered-toggle");
  await page.click("#tool-select");
  for (const [id, layer] of [
    ["business", "business"],
    ["states", "state"],
    ["rules", "rules"],
    ["api", "entry"],
    ["project", "structure"],
    ["code", "symbols"],
    ["database", "data"],
  ]) {
    await view(id);
    await page.click("#collapse");
    await settled();
    await page.click("#fit");
    await settled();
    assert.deepEqual(await page.evaluate(() => graphDebug.layers.visible), [layer]);
    const candidate = await page.evaluate(
      () =>
        graphDebug.displayGraph.boxes.find(
          (box) => box.kids.length && graphDebug.presentation.glyphs.has(box.id),
        )?.id,
    );
    if (candidate) {
      const before = await page.evaluate(() => graphDebug.spatial.camera);
      const p = await point(candidate);
      await writeFile(
        path.join(out, "spatial-candidate-" + id + ".json"),
        JSON.stringify(
          await page.evaluate(
            ({ candidate, p }) => ({
              candidate,
              p,
              positions: graphDebug.spatialPositions,
              glyphs: [...graphDebug.presentation.glyphs],
              labels: [...document.querySelectorAll("#semantic [data-node-id]")].map((el) => ({
                ...el.dataset,
              })),
            }),
            { candidate, p },
          ),
          null,
          2,
        ),
      );
      await page.mouse.dblclick(p.x, p.y);
      await settled();
      const state = await page.evaluate(
        (id) => ({
          camera: graphDebug.spatial.camera,
          open: graphDebug.graph.byId.get(id)?.open,
          self: graphDebug.presentation.glyphs.has(id),
          region: graphDebug.presentation.regions.has(id),
        }),
        candidate,
      );
      assert.ok(state.open && state.region, "3D " + id + " opens into a region");
      if (id === "project") assert.equal(state.self, false);
      for (const key of ["position", "target"])
        for (let i = 0; i < 3; i++)
          assert.ok(
            Math.abs(state.camera[key][i] - before[key][i]) < 0.05,
            "3D " + id + " preserves the viewpoint",
          );
      checks.push({ spatialExpansion: id, ...state });
    }
    checks.push({ spatialPreset: id, layer });
  }
  await page.click("#layered-toggle");
  await settled();
  await view("project");
  await page.click("#expand");
  await settled();
  const sourcePaths = await page.evaluate(() =>
    [...graphDebug.graph.all.values()].filter((n) => n.project_path).map((n) => n.project_path),
  );
  for (const name of [
    "sync.json",
    "discovery.json",
    "intent.json",
    "acceptance.json",
    "bo_integration.py",
    "bo_projection.py",
    "bo_stategraph",
    "review",
  ])
    assert.ok(!sourcePaths.includes(name), "Observer support excluded: " + name);
  for (const name of ["app.py", "service.py"])
    assert.ok(sourcePaths.includes(name), "Application source retained: " + name);
  checks.push({ applicationSourceOnly: sourcePaths });
  await shot("project-2d");

  // A layer toggle starts a draft and loads the optional source index for the
  // new layer. Saving/restoring the draft also preserves hidden layers.
  await view("business");
  await toggleLayer("entry");
  assert.equal(await page.locator("#analysis-view").inputValue(), "custom-draft");
  await page.waitForFunction(() =>
    graphDebug.displayGraph.boxes.some((box) => box.node.code_role === "endpoint"),
  );
  await page.click("#filter-toggle");
  await page.fill("#custom-view-name", "Business + API");
  await page.locator('#save-view button[type="submit"]').click();
  const savedID = await page.locator("#analysis-view").inputValue();
  await page.click("#close-filters");
  await waitForPreferences(page, (document) => analysisPreferences(document)?.selected === savedID);
  await page.reload();
  await settled();
  assert.equal(await page.locator("#analysis-view").inputValue(), savedID);
  assert.deepEqual((await page.evaluate(() => graphDebug.layers.visible)).sort(), [
    "business",
    "entry",
  ]);
  await view("api");
  assert.deepEqual(await page.evaluate(() => graphDebug.layers.visible), ["entry"]);
  await allElements();
  assert.equal(await page.locator("#analysis-view").inputValue(), "custom-draft");
  assert.equal((await page.evaluate(() => graphDebug.layers.visible)).length, 8);
  checks.push({ presetDraftSaveReload: true, savedID, allElements: true });

  // Stable physical source identity remains available in either UI language.
  await view("api");
  const ids = await page.evaluate(() => graphDebug.displayGraph.boxes.map((box) => box.id).sort());
  await page.selectOption("#language", "en");
  await page.waitForURL(/lang=en/);
  await settled();
  assert.deepEqual(
    await page.evaluate(() => graphDebug.displayGraph.boxes.map((box) => box.id).sort()),
    ids,
  );
  assert.equal(await page.locator("#name-mode").innerText(), "Semantic labels");
  await page.selectOption("#language", "zh-CN");
  await page.waitForURL(/lang=zh-CN/);
  await settled();
  assert.equal(await page.locator("#name-mode").innerText(), "语义名");
  checks.push({ localeSwitchPreservesIdentity: true });

  for (const mode of ["2D", "3D"]) {
    await view("business");
    if ((await page.locator("#layered-toggle").innerText()) !== mode)
      await page.click("#layered-toggle");
    await settled();
    await page.click("#collapse");
    await settled();
    await page.click("#fit");
    await settled();
    const canvas = await page.locator("#canvas-host").boundingBox();
    await page.click("#tool-pan");
    const cameraBefore = await page.evaluate(() =>
      graphDebug.layers.enabled ? graphDebug.spatial.camera : graphDebug.camera,
    );
    await drag({ x: canvas.x + 350, y: canvas.y + 300 }, { x: canvas.x + 410, y: canvas.y + 330 });
    const cameraAfter = await page.evaluate(() =>
      graphDebug.layers.enabled ? graphDebug.spatial.camera : graphDebug.camera,
    );
    assert.notDeepEqual(cameraAfter, cameraBefore, mode + " pan moves the viewpoint");
    await page.click("#fit");
    await settled();
    await page.click("#tool-select");
    const points = await page.locator("#semantic [data-node-id]").evaluateAll((elements) =>
      elements.map((node) => ({
        id: node.dataset.nodeId,
        x: +node.dataset.screenX,
        y: +node.dataset.screenY,
      })),
    );
    const selected = points.filter(
      (p) =>
        p.x > canvas.x + 200 &&
        p.x < canvas.x + canvas.width - 240 &&
        p.y > canvas.y + 45 &&
        p.y < canvas.y + canvas.height - 95,
    );
    assert.ok(selected.length >= 2, mode + " fixture has two on-screen nodes");
    // Frame all visible business nodes through the empty margin of the viewport.
    await drag(
      {
        x: Math.min(...selected.map((p) => p.x)) - 50,
        y: Math.min(...selected.map((p) => p.y)) - 50,
      },
      {
        x: Math.max(...selected.map((p) => p.x)) + 50,
        y: Math.max(...selected.map((p) => p.y)) + 50,
      },
    );
    const group = await page.evaluate(() => graphDebug.selectedNodes);
    assert.ok(group.length >= 2, mode + " marquee selects multiple stable identities");
    const groupBefore = await page.evaluate(
      (ids) =>
        Object.fromEntries(
          ids.map((id) => [
            id,
            graphDebug.layers.enabled
              ? graphDebug.spatialPositions[id]
              : {
                  x: graphDebug.graph.byId.get(id).x,
                  y: graphDebug.graph.byId.get(id).y,
                },
          ]),
        ),
      group,
    );
    const p = await point(group[0]);
    await drag(p, { x: p.x + 40, y: p.y + 18 });
    const groupAfter = await page.evaluate(
      (ids) =>
        Object.fromEntries(
          ids.map((id) => [
            id,
            graphDebug.layers.enabled
              ? graphDebug.spatialPositions[id]
              : {
                  x: graphDebug.graph.byId.get(id).x,
                  y: graphDebug.graph.byId.get(id).y,
                },
          ]),
        ),
      group,
    );
    const deltas = group.map((id) => groupAfter[id].x - groupBefore[id].x);
    assert.ok(Math.abs(deltas[0]) > 1);
    assert.ok(
      deltas.every((delta) => Math.abs(delta - deltas[0]) < 0.01),
      mode + " whole selection moves equally",
    );
    const candidate = await page.evaluate(
      () => graphDebug.displayGraph.boxes.find((box) => box.kids.length)?.id,
    );
    if (candidate) {
      const camera = await page.evaluate(() =>
        graphDebug.layers.enabled ? graphDebug.spatial.camera : graphDebug.camera,
      );
      const p = await point(candidate);
      await page.mouse.dblclick(p.x, p.y);
      await settled();
      const after = await page.evaluate(() =>
        graphDebug.layers.enabled ? graphDebug.spatial.camera : graphDebug.camera,
      );
      if (mode === "3D") {
        // OrbitControls damping settles at subpixel precision after the preceding
        // pan. Expansion must not reframe the scene (world tolerance < 0.05).
        for (const key of ["position", "target"])
          for (let i = 0; i < 3; i++) assert.ok(Math.abs(after[key][i] - camera[key][i]) < 0.05);
      } else assert.deepEqual(after, camera);
    }
    const labelStyle = await page
      .locator(mode === "3D" ? ".spatial-labels" : "#canvas-host")
      .evaluate((el) => getComputedStyle(el).userSelect);
    assert.equal(labelStyle, "none");
    assert.equal(await page.evaluate(() => getSelection().toString()), "");
    await shot("selection-" + mode.toLowerCase());
    checks.push({
      mode,
      pan: true,
      selected: group,
      groupDelta: deltas[0],
      noTextSelection: true,
    });
  }

  // Capture native HTTP operations and re-use those facts for both renderers.
  if ((await page.locator("#layered-toggle").innerText()) === "3D")
    await page.click("#layered-toggle");
  await view("overview");
  await allElements();
  await page.click("#expand");
  await settled();
  await page.selectOption("#capture-mode", "all");
  await page.click("#record-start");
  await page.waitForFunction(() => !document.querySelector("#record-stop").disabled);
  const uploaded = await page.request.post(new URL("/api/files", appURL).href, {
    headers: { "X-User": "Alice" },
    multipart: {
      file: {
        name: "viewer.txt",
        mimeType: "text/plain",
        buffer: Buffer.from("Viewer test"),
      },
    },
  });
  assert.equal(uploaded.status(), 201);
  const fileID = (await uploaded.json()).file_id;
  const shared = await page.request.post(new URL(`/api/files/${fileID}/share`, appURL).href, {
    headers: { "X-User": "Alice" },
    data: { recipient: "Bob" },
  });
  assert.equal(shared.status(), 200);
  await page.click("#record-stop");
  await page.waitForFunction(
    () => !document.querySelector("#replay").hidden && document.querySelector("#record-list").value,
  );
  const recordID = await page.locator("#record-list").inputValue();
  const recording = await (
    await page.request.get(new URL("/api/recordings/" + recordID, url).href)
  ).json();
  assert.deepEqual(recording.gaps, []);
  await writeFile(path.join(out, "real-recording.json"), JSON.stringify(recording, null, 2));
  await page.selectOption("#replay-grain", "events");
  const options = await page
    .locator("#replay-events option")
    .evaluateAll((options) => options.map((o) => o.value));
  let transferStep;
  for (const option of options.slice(0, 65)) {
    await page.selectOption("#replay-events", option);
    if (
      await page.evaluate(
        () => JSON.parse(document.querySelector("#renderer").dataset.animatedEdges || "[]").length,
      )
    ) {
      transferStep = option;
      break;
    }
  }
  assert.ok(transferStep, "Recorded causality matches at least one visible relation");
  for (const mode of ["2D", "3D"]) {
    if ((await page.locator("#layered-toggle").innerText()) !== mode)
      await page.click("#layered-toggle");
    await settled();
    await page.click("#fit");
    await settled();
    await page.selectOption("#replay-events", transferStep);
    await page.waitForFunction(() => graphDebug.transferPoints.length > 0);
    const first = await page.evaluate(() => graphDebug.transferPoints);
    await shot("transfer-" + mode.toLowerCase() + "-a");
    await page.waitForFunction(
      (points) =>
        graphDebug.transferPoints.length &&
        JSON.stringify(graphDebug.transferPoints) !== JSON.stringify(points),
      first,
    );
    const second = await page.evaluate(() => graphDebug.transferPoints);
    await shot("transfer-" + mode.toLowerCase() + "-b");
    assert.notDeepEqual(first, second);
    assert.ok(
      (
        await page.evaluate(() =>
          JSON.parse(document.querySelector("#renderer").dataset.activeNodes),
        )
      ).length,
    );
    checks.push({ mode, actualMovingTransfers: second, recording: recordID });
  }
  const toolbar = await page.locator(".toolbar").boundingBox();
  assert.ok(toolbar.height < 55, "One compact toolbar row");
  const legend = await page.locator("[data-legend-edge]").evaluateAll((rows) =>
    rows.map((row) => ({
      family: row.dataset.legendEdge,
      dash: row.querySelector("path").getAttribute("stroke-dasharray"),
    })),
  );
  assert.ok(new Set(legend.map((row) => row.dash)).size >= 5);
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify({ passed: true, checks, errors, legend }, null, 2),
  );
  console.log(
    JSON.stringify({
      passed: true,
      checks: checks.length,
      realEvents: recording.events.length,
    }),
  );
} catch (error) {
  await shot("failure").catch(() => {});
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify({ passed: false, error: error.stack, checks, errors }, null, 2),
  );
  throw error;
} finally {
  await browser?.close();
}
