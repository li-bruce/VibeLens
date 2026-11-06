/** Exercise folding, dragging and relation identity on every populated plane.
 * Uses an isolated accepted application via test_concept_browser.py. All changes
 * go through the viewer's pointer/select controls, never debug setters.
 */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const out = path.resolve(process.env.BO_CONCEPT_EVIDENCE || ".validation/expansion-relations");
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.BO_BROWSER_EXECUTABLE,
  args: ["--enable-unsafe-swiftshader"],
});
const page = await browser.newPage({ viewport: { width: 1680, height: 1100 } });
const checks = [],
  errors = [],
  failures = [];
page.on("pageerror", (error) => errors.push(error.message));
const settled = () =>
  page.waitForFunction(
    () =>
      window.graphDebug?.graph &&
      !graphDebug.sourceBusy &&
      !graphDebug.layoutBusy &&
      !graphDebug.geometryBusy,
    null,
    { timeout: 30000 },
  );
async function point(id) {
  await page.waitForFunction((id) => {
    const el = [...document.querySelectorAll("#semantic [data-node-id]")].find(
      (el) => el.dataset.nodeId === id,
    );
    return (
      el &&
      Number.isFinite(Number(el.dataset.screenX)) &&
      Number.isFinite(Number(el.dataset.screenY)) &&
      !graphDebug.geometryBusy
    );
  }, id);
  return page.locator("#semantic [data-node-id]").evaluateAll((elements, id) => {
    const el = elements.find((el) => el.dataset.nodeId === id);
    return el && { x: +el.dataset.screenX, y: +el.dataset.screenY };
  }, id);
}
async function toggle(id) {
  const region = await page.evaluate((id) => graphDebug.presentation.regions.has(id), id);
  if (region) {
    // A region center can contain another glyph. Its visible title is an
    // unambiguous interaction target; use it just as a user would.
    await page.click("#fit");
    await settled();
    if (await page.evaluate(() => graphDebug.layers.enabled)) {
      const label = page
        .locator(`.spatial-label.region-label[data-spatial-region="${id}"]`)
        .first();
      await label.dblclick();
    } else {
      const p = await page.evaluate((id) => {
        const r = graphDebug.displayGraph.regions.find((r) => r.id === id);
        const { scale, pan } = graphDebug.camera;
        const rect = document.querySelector("#canvas-host canvas").getBoundingClientRect();
        const h = Math.max(13, 11 / scale) + 8 / scale;
        return {
          x: rect.left + r.cx * scale + pan.x,
          y: rect.top + (r.cy + r.radius + h / 2 + 5 / scale) * scale + pan.y,
        };
      }, id);
      await page.mouse.dblclick(p.x, p.y);
    }
    await settled();
    assert.equal(
      await page.evaluate((id) => graphDebug.graph.byId.get(id)?.open, id),
      false,
      "Region title closes its owner",
    );
    return;
  }
  const p = await point(id);
  assert.ok(p && Number.isFinite(p.x) && Number.isFinite(p.y), id + " has a screen coordinate");
  await page.mouse.dblclick(p.x, p.y);
  await settled();
  const children = +(await page
    .locator(`#semantic [data-node-id="${id}"]`)
    .getAttribute("data-child-count"));
  if (children)
    assert.equal(
      await page.evaluate((id) => graphDebug.graph.byId.get(id)?.open, id),
      true,
      "Double-click opens the intended node: " + id,
    );
}
async function drag(id) {
  const p = await point(id);
  await page.mouse.move(p.x, p.y);
  await page.mouse.down();
  await page.mouse.move(p.x + 55, p.y + 22, { steps: 10 });
  await page.mouse.up();
  await settled();
}
async function snapshot() {
  return page.evaluate(() => {
    const g = graphDebug,
      spatial = g.layers.enabled,
      visible = new Set([...g.presentation.glyphs, ...g.presentation.regions]);
    return {
      camera: spatial ? g.spatial.camera : g.camera,
      positions: Object.fromEntries(
        g.displayGraph.boxes
          .filter((box) => visible.has(box.id))
          .map((box) => [box.id, spatial ? g.spatialPositions[box.id] : { x: box.x, y: box.y }]),
      ),
      regions: spatial
        ? g.spatial.volumes
        : g.displayGraph.regions.map((r) => ({ id: r.id, cx: r.cx, cy: r.cy, radius: r.radius })),
      edges: g.presentation.edges
        .map((e) => ({
          from: e.from,
          to: e.to,
          type: e.type,
          members: e.members.map((m) => m.id).sort(),
        }))
        .sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b))),
      visible: [...new Set([...g.presentation.glyphs, ...g.presentation.regions])].sort(),
    };
  });
}
function samePositions(before, after, message) {
  for (const [id, p] of Object.entries(before.positions)) {
    assert.ok(after.positions[id], message + ": " + id + " still exists");
    for (const key of ["x", "y", "z"].filter((key) => Number.isFinite(p?.[key])))
      assert.ok(
        Math.abs(p[key] - after.positions[id][key]) < 0.05,
        `${message}: ${id}.${key}: ${p[key]} -> ${after.positions[id][key]}`,
      );
  }
}
async function selectLayer(preset, layer) {
  await page.selectOption("#analysis-view", preset);
  await settled();
  if (preset === "overview") {
    const other = await page.evaluate(
      (layer) => graphDebug.layers.visible.filter((id) => id !== layer),
      layer,
    );
    for (const id of other) {
      const index = await page.evaluate((id) => graphDebug.layers.order.indexOf(id), id);
      const box = await page.locator("#layer-controls canvas").boundingBox();
      await page.mouse.click(box.x + 22, box.y + 40 + index * 34 + 16);
      await settled();
    }
  }
  await page.click("#collapse");
  await settled();
  await page.click("#fit");
  await settled();
  assert.deepEqual(await page.evaluate(() => graphDebug.layers.visible), [layer]);
}
try {
  await page.goto(process.env.BO_CONCEPT_URL);
  await settled();
  if ((await page.locator("#replay-timeline").getAttribute("aria-pressed")) === "true")
    await page.click("#replay-timeline");
  for (const mode of ["2D", "3D"]) {
    if ((await page.locator("#layered-toggle").innerText()) !== mode) {
      await page.click("#layered-toggle");
      await settled();
    }
    await page.click("#tool-select");
    for (const [preset, layer] of [
      ["overview", "business"],
      ["states", "state"],
      ["rules", "rules"],
      ["api", "entry"],
      ["project", "structure"],
      ["code", "symbols"],
      ["database", "data"],
    ]) {
      const record = { mode, layer };
      checks.push(record);
      try {
        await selectLayer(preset, layer);
        const candidates = await page
          .locator("#semantic [data-node-id]")
          .evaluateAll((elements) =>
            elements.map((el) => ({ id: el.dataset.nodeId, children: +el.dataset.childCount })),
          );
        assert.ok(candidates.length, layer + " contains application nodes");
        const candidate = candidates.find((n) => n.children > 0) || candidates[0];
        record.candidate = candidate;
        record.before = await snapshot();
        await toggle(candidate.id);
        record.opened = await snapshot();
        await page.screenshot({ path: path.join(out, `${mode}-${layer}-opened.png`) });
        assert.deepEqual(
          record.opened.camera,
          record.before.camera,
          "Expansion preserves the camera",
        );
        if (candidate.children) {
          assert.ok(
            record.opened.visible.length > record.before.visible.length,
            "Visible children expand",
          );
          await toggle(candidate.id);
        }
        record.closed = await snapshot();
        samePositions(record.before, record.closed, "Expand/collapse preserves positions");
        assert.deepEqual(
          record.closed.edges,
          record.before.edges,
          "Expand/collapse preserves original edge members",
        );
        await drag(candidate.id);
        record.dragged = await snapshot();
        assert.notDeepEqual(
          record.dragged.positions[candidate.id],
          record.closed.positions[candidate.id],
          "Pointer drag moves the intended node",
        );
        for (let cycle = 0; cycle < 2; cycle++) {
          await toggle(candidate.id);
          if (candidate.children) await toggle(candidate.id);
          const after = await snapshot();
          (record.cycles ||= []).push(after);
          samePositions(record.dragged, after, "Dragging then reopening preserves saved positions");
          assert.deepEqual(after.edges, record.dragged.edges, "No phantom repeated edges");
        }
        // Business-only Upload has no visible descendants. Repeated double-click
        // must not promote its hidden database helper's calls onto this plane.
        if (layer === "business") {
          await toggle(candidate.id);
          await page.click("#fit");
          await settled();
          const before = await snapshot();
          assert.equal(
            await page
              .locator('#semantic [data-node-id="upload"]')
              .getAttribute("data-child-count"),
            "0",
          );
          for (let i = 0; i < 4; i++) await toggle("upload");
          const after = await snapshot();
          samePositions(before, after, "Upload does not rearrange the business group");
          assert.deepEqual(after.regions, before.regions, "The parent region stays fixed");
          assert.deepEqual(
            after.edges,
            before.edges,
            "Hidden source calls stay off the business plane",
          );
          const flows = after.edges.filter((e) => e.type === "flow");
          assert.equal(flows.length, 4);
          assert.ok(
            flows.every((e) => e.members.length === 1),
            "Bound definitions never inflate x2",
          );
          assert.ok(!after.edges.some((e) => e.type === "call"));
          const relation = await page.evaluate(
            () =>
              graphDebug.presentation.edges.find((e) =>
                e.members.some((m) => m.id === "upload-share"),
              ).id,
          );
          // Exercise the keyboard-accessible relation control, which uses the
          // same details handler as clicking the WebGL line in either mode.
          await page.locator(`#semantic-edges [data-edge-id="${relation}"]`).focus();
          await page.keyboard.press("Enter");
          await page.locator("#edge-details").waitFor({ state: "visible" });
          assert.equal(await page.locator("#edge-members > li").count(), 1);
          await page.locator("#edge-members details summary").click();
          assert.deepEqual(await page.locator("#edge-members details code").allTextContents(), [
            "upload-share",
            "concept-relation:upload-share",
          ]);
          record.boundDefinitions = await page.locator("#edge-members").innerText();
          await page.screenshot({ path: path.join(out, `${mode}-relation-definitions.png`) });
          await page.keyboard.press("Escape");
        }
        await page.screenshot({ path: path.join(out, `${mode}-${layer}.png`) });
        record.passed = true;
      } catch (error) {
        record.failure = error.stack;
        failures.push({ mode, layer, message: error.message });
        await page.screenshot({ path: path.join(out, `${mode}-${layer}-failure.png`) });
      }
      await writeFile(
        path.join(out, "expansion-checks.json"),
        JSON.stringify({ checks, failures, errors }, null, 2),
      );
    }
  }
  await writeFile(
    path.join(out, "expansion-checks.json"),
    JSON.stringify({ checks, failures, errors }, null, 2),
  );
  assert.deepEqual(failures, []);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ passed: true, planes: 7, modes: 2, checks: checks.length, errors }));
} finally {
  await browser.close();
}
