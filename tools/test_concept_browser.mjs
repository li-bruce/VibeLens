/** Inspect a real accepted v2 project through the same controls a developer uses.
 * BO_CONCEPT_URL selects an independently constructed running project. No model,
 * event or HTTP response is replaced by this acceptance script.
 */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const url = process.env.BO_CONCEPT_URL;
if (!url) throw new Error("Set BO_CONCEPT_URL to an accepted v2 project's /graph URL");
const output = path.resolve(process.env.BO_CONCEPT_EVIDENCE || ".validation/concept-browser");
await mkdir(output, { recursive: true });
let browser, page;
const checks = [],
  errors = [],
  writes = [];
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (request.method() === "POST") writes.push(new URL(request.url()).pathname);
  });
  await page.goto(url);
  await page.waitForFunction(
    () => window.graphDebug?.view?.concept_structure?.schema === "bo-concept-projection/v1",
  );
  // Read the authored model independently of lazy source projections in the UI.
  const modelURL = new URL("/api/view", url).href;
  const modelResponse = await page.request.get(modelURL);
  assert.equal(modelResponse.status(), 200);
  const nativeModel = (await modelResponse.json()).model;
  const bound = await page.evaluate(() => {
    const view = graphDebug.view;
    return {
      schema: view.concept_structure.schema,
      revision: view.concept_structure.revision,
      concepts: view.concept_structure.nodes.map((node) => node.id),
      native: view.model.nodes.map((node) => node.id),
      maps: view.concept_structure.edges
        .filter((edge) => edge.mapping_role === "implements")
        .map((edge) => edge.id),
      inventory: [...graphDebug.graph.all.keys()],
    };
  });
  assert.ok(bound.maps.length, "The project supplies actual concept-to-source bindings");
  for (const id of new Set([...bound.concepts, ...bound.native]))
    assert.ok(bound.inventory.includes(id), id);
  checks.push({ boundIdentity: true, ...bound });
  if ((await page.locator("#layered-toggle").innerText()) === "3D")
    await page.click("#layered-toggle");
  // Static model review uses the canvas height, not an empty live Timeline.
  if ((await page.locator("#replay-timeline").getAttribute("aria-pressed")) === "true")
    await page.click("#replay-timeline");
  if ((await page.locator("#name-mode").getAttribute("aria-checked")) !== "true")
    await page.click("#name-mode");
  async function frameConcern(concern) {
    const viewport = await page.locator("#viewport").boundingBox();
    const bounds = await page.evaluate((concern) => {
      const boxes = graphDebug.displayGraph.boxes.filter(
        (box) => box.node.layer === concern && graphDebug.presentation.glyphs.has(box.id),
      );
      return {
        left: Math.min(...boxes.map((box) => box.x)),
        right: Math.max(...boxes.map((box) => box.x + box.w)),
        top: Math.min(...boxes.map((box) => box.y)),
        bottom: Math.max(...boxes.map((box) => box.y + box.h)),
      };
    }, concern);
    const desired = Math.min(
      0.82,
      (viewport.width - 350) / (bounds.right - bounds.left),
      (viewport.height - 140) / (bounds.bottom - bounds.top),
    );
    for (let step = 0; step < 12; step++) {
      const scale = await page.evaluate(() => graphDebug.camera.scale);
      if (scale >= desired / 1.2 && scale <= desired * 1.2) break;
      await page.click(scale < desired ? "#zoom-in" : "#zoom-out");
    }
    // Pan the visible concern through the actual canvas. Its saved global layout
    // can retain far-away source nodes that a preset intentionally hides.
    for (let step = 0; step < 30; step++) {
      const camera = await page.evaluate(() => graphDebug.camera);
      const dx =
        viewport.width / 2 - (((bounds.left + bounds.right) / 2) * camera.scale + camera.pan.x);
      const dy =
        viewport.height / 2 - (((bounds.top + bounds.bottom) / 2) * camera.scale + camera.pan.y);
      if (Math.abs(dx) + Math.abs(dy) < 4) break;
      const x = viewport.x + viewport.width - 12,
        y = viewport.y + viewport.height - 75;
      await page.mouse.move(x, y);
      await page.mouse.down();
      await page.mouse.move(
        x + Math.max(-250, Math.min(250, dx)),
        y + Math.max(-250, Math.min(250, dy)),
        { steps: 4 },
      );
      await page.mouse.up();
    }
    await page.locator("#viewport").focus();
    await page.keyboard.press("Escape");
  }
  for (const [preset, concern] of [
    ["business", "business"],
    ["states", "state"],
    ["rules", "rules"],
  ]) {
    await page.selectOption("#analysis-view", preset);
    await page.locator("#viewport").focus();
    await page.keyboard.press("Escape");
    await page.click("#filter-toggle");
    await page.click("#filter-reset");
    await page.click("#close-filters");
    await page.click("#expand");
    await page.click("#arrange");
    await page.waitForFunction(() => !graphDebug.layoutBusy);
    await page.click("#fit");
    if (concern === "rules") {
      const group = await page.evaluate(
        () =>
          graphDebug.displayGraph.regions.find(
            (region) =>
              (region.id === "policy:network" ||
                graphDebug.graph.all.get(region.id)?.layer === "rules") &&
              graphDebug.presentation.regions.has(region.id),
          )?.id,
      );
      if (group) {
        await page
          .locator("#semantic [data-node-id]")
          .evaluateAll(
            (elements, id) => elements.find((element) => element.dataset.nodeId === id).click(),
            group,
          );
        await page.locator("#viewport").focus();
        await page.keyboard.press("f");
      } else await frameConcern(concern);
    } else await frameConcern(concern);
    await page.evaluate(
      () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))),
    );
    const facts = await page.evaluate(() => ({
      glyphs: [...graphDebug.presentation.glyphs],
      regions: [...graphDebug.presentation.regions],
      nodes: graphDebug.displayGraph.boxes.map((box) => ({
        id: box.id,
        layer: box.node.layer,
        origin: box.node.origin,
        conceptId: box.node.concept_id,
        definition: box.node.concept_definition,
      })),
      concepts: graphDebug.view.concept_structure.nodes.map((node) => ({
        id: node.id,
        conceptId: node.concept_id || node.id,
        layer: node.layer,
        definition: node.concept_definition,
      })),
      edges: graphDebug.presentation.edges.flatMap((edge) =>
        edge.members.map((member) => ({
          id: member.id,
          type: member.type,
          observed: member.observed,
        })),
      ),
    }));
    // A shared native/concept ID retains native capture authority. Require the
    // exact confirmed definition, rather than assuming its origin is replaced.
    const visibleConcepts = facts.nodes.filter((node) => node.definition && node.layer === concern);
    assert.ok(visibleConcepts.length, preset + " retains its confirmed concepts");
    for (const node of visibleConcepts) {
      const declared = facts.concepts.find((concept) => concept.id === node.id);
      assert.ok(declared, "Confirmed definition exists: " + node.id);
      assert.equal(node.conceptId, declared.conceptId);
      assert.deepEqual(node.definition, declared.definition, node.id);
    }
    assert.ok(facts.edges.length, preset + " shows relationships as well as nodes");
    await page.screenshot({ path: path.join(output, `${concern}-2d.png`) });
    const inspectable = await page.evaluate(() =>
      graphDebug.displayGraph.boxes
        .filter(
          (box) =>
            box.node.concept_definition &&
            ["event", "transition", "fact", "rule_expression"].includes(box.node.concept_kind) &&
            (graphDebug.presentation.glyphs.has(box.id) ||
              graphDebug.presentation.regions.has(box.id)),
        )
        .map((box) => ({
          id: box.id,
          kind: box.node.concept_kind,
          definition: box.node.concept_definition,
        }))
        .filter(
          (node, index, values) => values.findIndex((other) => other.kind === node.kind) === index,
        ),
    );
    for (const node of inspectable) {
      await page
        .locator("#semantic [data-node-id]")
        .evaluateAll(
          (elements, id) => elements.find((element) => element.dataset.nodeId === id).click(),
          node.id,
        );
      await page.locator("#viewport").focus();
      await page.keyboard.press("Shift+F10");
      await page.click("#details");
      const disclosure = page.locator(".concept-definition");
      assert.equal(await disclosure.getAttribute("data-node-id"), node.id);
      if (!(await disclosure.evaluate((element) => element.open)))
        await disclosure.locator("summary").click();
      assert.deepEqual(JSON.parse(await disclosure.locator("pre").innerText()), node.definition);
      await page.screenshot({
        path: path.join(output, `definition-${node.kind}.png`),
      });
      await page.click("#close-detail");
    }
    if (["state", "rules"].includes(concern))
      assert.ok(inspectable.length, "Confirmed definition is inspectable in " + concern);
    checks.push({
      preset,
      nodes: facts.nodes.length,
      edges: facts.edges.length,
      inspectedDefinitions: inspectable.map((node) => ({
        id: node.id,
        kind: node.kind,
      })),
    });
  }
  const inspectedKinds = new Set(
    checks.flatMap((check) => check.inspectedDefinitions || []).map((node) => node.kind),
  );
  for (const kind of ["event", "transition", "fact", "rule_expression"])
    assert.ok(
      inspectedKinds.has(kind),
      "Definition details must survive native identity merging: " + kind,
    );
  await page.locator("#layers-all").evaluate((button) => button.click());
  await page.waitForFunction(() => !graphDebug.sourceBusy && !graphDebug.layoutBusy);
  await page.click("#expand");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  const shown = await page.evaluate(() =>
    [...new Set([...graphDebug.presentation.glyphs, ...graphDebug.presentation.regions])].sort(),
  );
  await page.click("#layered-toggle");
  await page.waitForFunction(() => graphDebug.spatial?.perspective && !graphDebug.layoutBusy);
  assert.equal(
    await page.evaluate(() =>
      graphDebug.displayGraph.boxes.some(
        (box) =>
          box.node.concept_kind === "state_model" &&
          box.rows?.some((row) => row.text === "phase: Phase = undefined"),
      ),
    ),
    false,
  );
  assert.deepEqual(
    await page.evaluate(() =>
      [...new Set([...graphDebug.presentation.glyphs, ...graphDebug.presentation.regions])].sort(),
    ),
    shown,
  );
  const spatial = await page.evaluate(() => ({
    planes: graphDebug.spatial.layerPlanes,
    webgl: graphDebug.spatial.webgl,
    position: graphDebug.spatial.camera.position,
    native: graphDebug.view.model.nodes.map((node) => node.id),
    source: [
      graphDebug.view.project_structure,
      graphDebug.view.api_structure,
      graphDebug.view.code_structure,
    ].flatMap((projection) => (projection?.nodes || []).map((node) => node.id)),
    bound: graphDebug.view.concept_structure.revision,
  }));
  assert.ok(spatial.webgl);
  const afterModel = await page.request.get(modelURL);
  assert.equal(afterModel.status(), 200);
  assert.deepEqual((await afterModel.json()).model, nativeModel);
  // Opening all layers may load additional genuine source declarations. Require
  // exactly the authored IDs plus those declared projections, never extra nodes
  // invented by the renderer or missing original model identities.
  assert.deepEqual(
    spatial.native.slice().sort(),
    [...new Set([...nativeModel.nodes.map((node) => node.id), ...spatial.source])].sort(),
  );
  assert.equal(spatial.bound, bound.revision);
  assert.ok(spatial.planes.some((plane) => plane.id === "symbols"));
  // A saved focus may put an expanded region under the old fixed drag point.
  // Frame and zoom out through real controls, then drag the empty left margin.
  // Moving a group is a different interaction and must not satisfy this check.
  await page.click("#fit");
  await page.click("#zoom-out");
  await page.click("#zoom-out");
  await page.click("#tool-orbit");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  const orbitStart = await page.evaluate(() => ({
    camera: graphDebug.spatial.camera.position,
    nodes: graphDebug.spatialPositions,
  }));
  const canvas = await page.locator("#viewport").boundingBox();
  const drag = {
    x: canvas.x + canvas.width * 0.23,
    y: canvas.y + canvas.height * 0.82,
  };
  assert.ok(
    await page.evaluate(
      (point) => document.elementFromPoint(point.x, point.y)?.classList.contains("spatial-canvas"),
      drag,
    ),
    "The orbit gesture must begin on the canvas, not the legend or a control",
  );
  await page.mouse.move(drag.x, drag.y);
  await page.mouse.down();
  await page.mouse.move(drag.x + 65, drag.y - 45, {
    steps: 8,
  });
  await page.mouse.up();
  await page.waitForFunction(
    (before) => JSON.stringify(graphDebug.spatial.camera.position) !== JSON.stringify(before),
    orbitStart.camera,
  );
  assert.deepEqual(await page.evaluate(() => graphDebug.spatialPositions), orbitStart.nodes);
  await page.click("#tool-select");
  await page.screenshot({ path: path.join(output, "bound-model-3d.png") });
  checks.push({ sameGraphIn3D: true, realOrbit: true, planes: spatial.planes });
  assert.deepEqual(errors, []);
  assert.ok(
    writes.every((route) => route === "/api/preferences"),
    "Inspection sends no application command",
  );
  if (process.env.BO_CONCEPT_APP_URL) {
    const appURL = process.env.BO_CONCEPT_APP_URL,
      captureID = process.env.BO_CONCEPT_CAPTURE_ID || "share",
      capturePreset = captureID.startsWith("event:") ? "states" : "business";
    if ((await page.locator("#layered-toggle").innerText()) === "3D")
      await page.click("#layered-toggle");
    await page.selectOption("#analysis-view", capturePreset);
    await page.click("#filter-toggle");
    await page.click("#filter-reset");
    await page.fill("#filter-query", "share");
    await page.fill("#custom-view-name", "Share observation");
    await page.locator('#save-view button[type="submit"]').click();
    await page.click("#close-filters");
    await page.click("#expand");
    await page.waitForFunction(() => !graphDebug.layoutBusy);
    const custom = await page.locator("#analysis-view").inputValue();
    assert.ok(custom.startsWith("custom-"));
    const target = await page.evaluate((captureID) => {
      const view = graphDebug.view,
        edge = view.concept_structure.edges.find(
          (edge) =>
            edge.from === captureID && edge.mapping_role === "implements" && edge.to !== edge.from,
        );
      return edge
        ? {
            concept: edge.from,
            native: edge.to,
            kind: view.concept_structure.nodes.find((node) => node.id === edge.from).concept_kind,
          }
        : null;
    }, captureID);
    assert.ok(target, "This runtime fixture must separate concept and native identities");
    await page
      .locator("#semantic [data-node-id]")
      .evaluateAll(
        (elements, id) => elements.find((element) => element.dataset.nodeId === id).click(),
        target.concept,
      );
    const uploaded = await page.request.post(new URL("/api/files", appURL).href, {
      headers: { "X-User": "Alice" },
      multipart: {
        file: {
          name: "browser.txt",
          mimeType: "text/plain",
          buffer: Buffer.from("Browser scope test"),
        },
      },
    });
    assert.equal(uploaded.status(), 201);
    const { file_id: fileID } = await uploaded.json();
    await page.selectOption("#capture-mode", "focused");
    const started = page.waitForResponse(
      (response) => new URL(response.url()).pathname === "/api/recordings/start",
    );
    await page.click("#record-start");
    const startResponse = await started;
    assert.equal(startResponse.status(), 200, await startResponse.text());
    const shared = await page.request.post(new URL(`/api/files/${fileID}/share`, appURL).href, {
      headers: { "X-User": "Alice" },
      data: { recipient: "Bob" },
    });
    assert.equal(shared.status(), 200);
    await page.waitForFunction(() => !document.querySelector("#record-stop").disabled);
    await page.click("#record-stop");
    await page.waitForFunction(
      () =>
        !document.querySelector("#replay").hidden &&
        document.querySelector("#record-list").value &&
        graphDebug.timeline?.lifecycles?.length,
    );
    const recordID = await page.locator("#record-list").inputValue();
    const recorded = await (
      await page.request.get(new URL("/api/recordings/" + encodeURIComponent(recordID), url).href)
    ).json();
    assert.equal(recorded.status, "stopped", JSON.stringify(recorded.gaps));
    assert.deepEqual(recorded.gaps, []);
    assert.ok(
      recorded.events.some((event) => event.node === target.native && event.phase === "return"),
    );
    assert.ok(!recorded.events.some((event) => event.node === target.concept));
    const trace = await page.evaluate(() => graphDebug.timeline);
    const intervals = trace.lifecycles.filter((slice) => slice.node === target.concept);
    if (target.kind === "action") assert.ok(intervals.length);
    else
      assert.equal(
        intervals.length,
        0,
        "An event definition does not inherit its function's call duration",
      );
    assert.ok(
      intervals.every(
        (slice) =>
          slice.source_node === target.native && slice.observation_basis.kind === "concept-binding",
      ),
    );
    for (const interval of intervals) {
      assert.ok(
        recorded.events.some(
          (event) => event.id === interval.entryEventId && event.node === target.native,
        ),
      );
      assert.ok(
        interval.unfinished ||
          recorded.events.some(
            (event) => event.id === interval.endEventId && event.node === target.native,
          ),
      );
    }
    assert.ok(
      trace.rows.some((row) => row.layer === (capturePreset === "states" ? "state" : "business")),
    );
    if ((await page.locator("#replay-timeline").getAttribute("aria-pressed")) !== "true")
      await page.click("#replay-timeline");
    await page.screenshot({
      path: path.join(output, "focused-concept-recording.png"),
    });
    await writeFile(path.join(output, "focused-recording.json"), JSON.stringify(recorded, null, 2));
    checks.push({
      focusedConceptCapture: target,
      customView: custom,
      recording: recordID,
      events: recorded.events.length,
      intervals,
    });
    await page.selectOption("#analysis-view", "business");
    await page.waitForFunction(() =>
      graphDebug.timeline?.lifecycles?.some((slice) => slice.node === "share" && !slice.unfinished),
    );
    const businessTrace = await page.evaluate(() => graphDebug.timeline);
    assert.ok(businessTrace.rows.some((row) => row.layer === "business"));
    await page.selectOption("#replay-grain", "events");
    const shareEntry =
      recorded.events.findIndex(
        (event) => event.node === target.native && event.phase === "enter",
      ) + 1;
    await page.selectOption("#replay-events", String(shareEntry));
    await page.click(".trace-fit");
    for (let step = 0; step < 4; step++) await page.click(".trace-zoom-in");
    await page.waitForFunction(() => !graphDebug.timeline.zooming);
    await page.click("#fit");
    await page.screenshot({
      path: path.join(output, "focused-business-timeline.png"),
    });
    checks.push({
      realBusinessTimeline: true,
      lifecycles: businessTrace.lifecycles.filter((slice) => slice.node === "share"),
    });
  }
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify({ passed: true, checks, errors, writes }, null, 2),
  );
  console.log(
    JSON.stringify({
      passed: true,
      checks: checks.length,
      concepts: bound.concepts.length,
      mappings: bound.maps.length,
    }),
  );
} catch (error) {
  await page?.screenshot({ path: path.join(output, "failure.png") }).catch(() => {});
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify({ passed: false, error: error.stack, checks, errors, writes }, null, 2),
  );
  throw error;
} finally {
  await browser?.close();
}
