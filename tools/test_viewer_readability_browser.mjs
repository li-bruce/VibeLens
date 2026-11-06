/** Native wheel, fit, preset and bundle checks against the accepted application. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { analysisPreferences, waitForPreferences } from "./browser-preferences.mjs";
const { chromium } = createRequire(import.meta.url)("playwright");
const url = process.env.BO_CONCEPT_URL;
const out = path.resolve(process.env.BO_CONCEPT_EVIDENCE || ".validation/viewer-readability");
await mkdir(out, { recursive: true });
const checks = [],
  errors = [];
let browser, page;
const settled = () =>
  page.waitForFunction(
    () => window.graphDebug?.graph && !graphDebug.layoutBusy && !graphDebug.geometryBusy,
    null,
    { timeout: 30000 },
  );
const shot = async (name) => page?.screenshot({ path: path.join(out, name + ".png") });
async function select(id) {
  await page.selectOption("#analysis-view", id);
  await settled();
  await page.click("#fit");
  await settled();
}
async function fitCheck(id) {
  const result = await page.evaluate(() => {
    const g = graphDebug.displayGraph,
      c = graphDebug.camera;
    const canvas = document.querySelector("#canvas-host").getBoundingClientRect();
    return {
      width: canvas.width,
      height: canvas.height,
      scale: c.scale,
      left: g.minX * c.scale + c.pan.x,
      top: g.minY * c.scale + c.pan.y,
      right: (g.minX + g.width) * c.scale + c.pan.x,
      bottom: (g.minY + g.height) * c.scale + c.pan.y,
      nodes: g.boxes.length,
    };
  });
  assert.ok(result.nodes > 0, id + " populated");
  assert.ok(
    result.left >= -1 && result.right <= result.width + 1,
    id + " horizontal fit: " + JSON.stringify(result),
  );
  assert.ok(
    result.top >= -1 && result.bottom <= result.height + 1,
    id + " vertical fit: " + JSON.stringify(result),
  );
  checks.push({ fit: id, ...result });
}
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
    args: ["--enable-unsafe-swiftshader"],
  });
  page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(url);
  await settled();
  if ((await page.locator("#replay-timeline").getAttribute("aria-pressed")) === "true")
    await page.click("#replay-timeline");
  if ((await page.locator("#layered-toggle").innerText()) === "3D")
    await page.click("#layered-toggle");
  if ((await page.locator("#name-mode").getAttribute("aria-checked")) !== "true")
    await page.click("#name-mode");
  for (const id of ["business", "states", "rules", "api", "project", "code", "database"]) {
    await select(id);
    await fitCheck(id);
    const labels = await page.evaluate(() =>
      graphDebug.displayGraph.boxes.map((b) => ({ id: b.id, label: b.node.label })),
    );
    await writeFile(path.join(out, id + "-labels.json"), JSON.stringify(labels, null, 2));
    assert.ok(
      labels.every((n) => /\p{Script=Han}/u.test(n.label)),
      id +
        " translated labels: " +
        JSON.stringify(labels.filter((n) => !/\p{Script=Han}/u.test(n.label))),
    );
    const before = await page.evaluate(() => graphDebug.camera.scale);
    await page.locator("#canvas-host").hover({ position: { x: 800, y: 450 } });
    await page.mouse.wheel(0, 700);
    await page.waitForFunction((before) => graphDebug.camera.scale < before, before);
    await page.click("#fit");
    await settled();
    await shot("layer-" + id);
  }
  await select("business");
  const business = await page.evaluate(() => ({
    nodes: graphDebug.displayGraph.boxes.map((b) => ({ id: b.id, label: b.node.label })),
    edges: graphDebug.displayGraph.edges.map((e) => ({
      id: e.id,
      from: e.from,
      to: e.to,
      label: e.label,
    })),
  }));
  assert.equal(business.nodes.length, 5);
  assert.equal(
    new Set(business.edges.filter((e) => e.from !== e.to).map((e) => e.from + ">" + e.to)).size,
    4,
  );
  assert.ok(business.nodes.every((n) => /\p{Script=Han}/u.test(n.label)));
  checks.push({ business });
  const identities = business.nodes.map((n) => n.id).sort();
  await page.click("#name-mode");
  await settled();
  assert.deepEqual(
    (await page.evaluate(() => graphDebug.displayGraph.boxes.map((b) => b.id))).sort(),
    identities,
  );
  await page.click("#name-mode");
  await page.goto(url.replace("lang=zh-CN", "lang=en"));
  await settled();
  await select("business");
  const english = await page.evaluate(() =>
    graphDebug.displayGraph.boxes.map((b) => ({ id: b.id, label: b.node.label })),
  );
  assert.deepEqual(english.map((n) => n.id).sort(), identities);
  assert.ok(english.every((n) => !/\p{Script=Han}/u.test(n.label)));
  checks.push({ english });
  await page.goto(url);
  await settled();
  await select("rules");
  await page.selectOption("#edge-routing", "curve");
  if ((await page.locator("#edge-bundling").getAttribute("aria-pressed")) !== "true")
    await page.click("#edge-bundling");
  await settled();
  await waitForPreferences(page, (value) => analysisPreferences(value)?.bundling === true);
  await page.reload();
  await settled();
  assert.equal(await page.locator("#edge-bundling").getAttribute("aria-pressed"), "true");
  await waitForPreferences(page, (value) => analysisPreferences(value)?.bundling === true);
  checks.push({
    savedCurveBundling: true,
    routeStats: await page.evaluate(() => graphDebug.metrics.routeSolver),
  });
  await page.selectOption("#edge-routing", "straight");
  assert.equal(await page.locator("#edge-bundling").isDisabled(), true);
  await page.selectOption("#edge-routing", "curve");
  await page.click("#layered-toggle");
  await settled();
  await page.click("#fit");
  await settled();
  for (const id of ["business", "states", "rules", "api", "project", "code", "database"]) {
    await select(id);
    const target = page
      .locator(".spatial-label:not(.edge-label):not(.region-label)")
      .filter({ visible: true })
      .first();
    await target.waitFor({ state: "visible" });
    const before = await page.evaluate(() => graphDebug.spatial.camera);
    await target.hover();
    await page.mouse.wheel(0, -200);
    await page.waitForFunction(
      (before) =>
        JSON.stringify(graphDebug.spatial.camera.position) !== JSON.stringify(before.position),
      before,
    );
    checks.push({
      spatialWheelOverLabel: id,
      cameraBefore: before,
      cameraAfter: await page.evaluate(() => graphDebug.spatial.camera),
    });
    await page.click("#fit");
    await settled();
  }
  await select("rules");
  if (!(await page.locator(".region-label:visible").count())) {
    const owner = await page.evaluate(
      () =>
        graphDebug.displayGraph.boxes.find(
          (b) => b.kids.length && graphDebug.presentation.glyphs.has(b.id),
        )?.id,
    );
    assert.ok(owner, "Rule graph has a real expandable owner");
    await page.locator(`[data-spatial-label="${owner}"]`).dblclick();
    await settled();
    await page.click("#fit");
    await settled();
  }
  for (const selector of [".region-label:visible", ".edge-label:visible"]) {
    if (selector.startsWith(".edge")) {
      // Relationship captions appear for a selected node or a live transfer.
      await select("business");
      await page.locator('[data-spatial-label="share"]').click();
      await settled();
    }
    const target = page.locator(selector).first();
    await target.waitFor({ state: "visible" });
    const before = await page.evaluate(() => graphDebug.spatial.camera);
    await target.hover();
    await page.mouse.wheel(0, -180);
    await page.waitForFunction(
      (before) =>
        JSON.stringify(graphDebug.spatial.camera.position) !== JSON.stringify(before.position),
      before,
    );
    checks.push({ wheelOver: selector });
    await page.click("#fit");
    await settled();
  }
  await select("business");
  await shot("business-3d");
  checks.push({ spatial: await page.evaluate(() => graphDebug.spatial) });
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify({ passed: true, checks, errors }, null, 2),
  );
  console.log(JSON.stringify({ passed: true, checks: checks.length, errors: errors.length }));
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
