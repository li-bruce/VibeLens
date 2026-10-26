/** Native scroll, real replay and saved focus views on local or published Pages. */
import assert from "node:assert/strict";
import {spawn} from "node:child_process";
import {createRequire} from "node:module";
import {mkdir, writeFile} from "node:fs/promises";
import path from "node:path";
const {chromium} = createRequire(import.meta.url)("playwright");
const base = (process.env.BO_SITE_URL || "http://127.0.0.1:8897").replace(/\/$/, "");
const output = path.resolve(process.env.BO_CASE_BROWSER_EVIDENCE || ".validation/scroll-demo/browser");
await mkdir(output, {recursive: true});
const python = process.env.BO_PYTHON || path.resolve(".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const server = process.env.BO_SITE_URL ? null : spawn(python, ["-B", "-m", "http.server", "8897", "--bind", "127.0.0.1", "--directory", "docs/site"], {windowsHide: true, stdio: "ignore"});
let browser, page, scene;
const errors = [], receipts = [];
try {
  for (let i = 0; i < 60; i++) {try {if ((await fetch(base)).ok) break;} catch {} await new Promise((resolve) => setTimeout(resolve, 200));}
  browser = await chromium.launch({headless: true, args: ["--enable-unsafe-swiftshader"], ...(process.env.BO_BROWSER_EXECUTABLE ? {executablePath: process.env.BO_BROWSER_EXECUTABLE} : {})});
  page = await browser.newPage({viewport: {width: 1536, height: 1050}});
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {if (message.type() === "error") errors.push(message.text());});
  await page.route("**/case-viewer.mjs*", async (route) => {await new Promise((resolve) => setTimeout(resolve, 400)); await route.continue();});
  async function frame() {
    const child = page.frame({url: /viewer\/index.html/}); assert.ok(child);
    await child.waitForFunction(() => window.graphDebug?.graph?.boxes.length > 0);
    return child;
  }
  async function go(id) {
    scene = id;
    await page.locator("#" + id).scrollIntoViewIfNeeded();
    await page.waitForFunction((id) => document.body.dataset.sceneReady === id, id, {timeout: 30000});
    return frame();
  }
  async function shot(name) {await page.waitForTimeout(300); await page.screenshot({path: path.join(output, name + ".png"), fullPage: false});}
  for (const language of ["en", "zh-CN"]) {
    await page.goto(base + "/demo.html?lang=" + language);
    await page.waitForSelector("#foundation");
    assert.equal(await page.locator(".case-scene").count(), 6);
    assert.equal(await page.getAttribute("html", "lang"), language);
    let child = await go("foundation");
    assert.deepEqual(await child.evaluate(() => graphDebug.graph.boxes.map((box) => box.id).sort()), ["exhibit", "publish", "review", "upload"]);
    assert.equal(await child.evaluate(() => graphDebug.view.stage), "design");
    await shot(language + "-01-foundation");
    // The graph's visible region must not trap normal page wheel scrolling.
    const area = await page.locator("#case-graph").boundingBox();
    await page.mouse.move(area.x + area.width / 2, area.y + area.height / 2);
    const beforeScroll = await page.evaluate(() => scrollY);
    await page.mouse.wheel(0, 200); await page.waitForTimeout(200);
    assert.ok(await page.evaluate((before) => scrollY > before + 20, beforeScroll));
    child = await go("run");
    await child.waitForFunction(() => graphDebug.view.replay?.event?.node);
    const first = await child.evaluate(() => graphDebug.view.replay.index);
    await page.waitForTimeout(750);
    assert.ok(await child.evaluate((first) => graphDebug.view.replay.index > first, first), "Recorded playback must advance");
    const eventCount = await child.evaluate(async () => (await (await fetch("/api/view")).json()).events.length);
    child = await go("drill");
    await child.waitForFunction(() => graphDebug.view.replay?.event?.node === "review-policy" && graphDebug.view.replay.event.phase === "return");
    assert.equal(await child.evaluate(() => graphDebug.view.replay.event.outputs.verdict), "allowed");
    await page.waitForFunction(()=>document.querySelector('#case-telemetry').textContent.includes('allowed'));
    const drillIds = await child.evaluate(() => graphDebug.graph.boxes.map((box) => box.id));
    assert.ok(drillIds.length <= 8, JSON.stringify(drillIds));
    assert.ok(drillIds.includes("field:review-policy:in:reviewed_version"));
    assert.ok(drillIds.includes("field:review-policy:in:current_version"));
    await shot(language + "-02-drill");
    child = await go("watch");
    await page.locator('[data-watch="effects"]').uncheck();
    await child.waitForFunction(() => !graphDebug.graph.boxes.some((box) => box.id === "save-exhibition"));
    await page.locator('[data-watch="effects"]').check();
    await child.waitForFunction(() => graphDebug.graph.boxes.some((box) => box.id === "save-exhibition"));
    await page.locator('[data-watch="states"]').check();
    await child.waitForFunction(() => graphDebug.graph.boxes.some((box) => box.id === "state.pending"));
    const customName = language === "en" ? "Exhibition review" : "展览审核";
    await page.fill("#watch-name", customName); await page.click("#save-watch");
    await page.waitForFunction(() => document.body.dataset.savedView?.startsWith("custom-"));
    const savedId = await page.getAttribute("body", "data-saved-view");
    await child.waitForFunction((id) => document.querySelector("#analysis-view").value === id, savedId);
    const savedNodes = await child.evaluate(() => graphDebug.graph.boxes.map((box) => box.id).sort());
    assert.ok(savedNodes.length <= 12, JSON.stringify(savedNodes));
    assert.ok(await child.evaluate(() => graphDebug.graph.edges.length > 4));
    await shot(language + "-03-saved-view");
    await child.waitForFunction(async (name) => {
      const stored = (await (await fetch("/api/preferences")).json()).entries;
      return JSON.stringify(stored).includes(name);
    }, customName);
    child = await go("iterate");
    await child.waitForFunction((id) => document.querySelector("#analysis-view").value === id && graphDebug.view.replay?.event?.outputs?.verdict === "stale_review", savedId);
    await page.waitForFunction(()=>document.querySelector('#case-telemetry').textContent.includes('stale_review'));
    assert.deepEqual(await child.evaluate(() => graphDebug.graph.boxes.map((box) => box.id).sort()), savedNodes);
    await shot(language + "-04-iteration");
    await page.reload(); child = await go("iterate");
    await child.waitForFunction((id) => document.querySelector("#analysis-view").value === id && graphDebug.view.replay?.event?.outputs?.verdict === "stale_review", savedId);
    assert.deepEqual(await child.evaluate(() => graphDebug.graph.boxes.map((box) => box.id).sort()), savedNodes);
    child = await go("verify");
    await child.waitForFunction(() => graphDebug.view.replay?.event?.node);
    await page.click("#case-tools");
    await child.waitForFunction(() => document.body.dataset.caseCompact === "false");
    await page.click("#case-play");
    await child.click("#replay-live");
    assert.equal(await child.evaluate(async () => (await (await fetch("/api/view")).json()).events.length), 138);
    for (const view of ["api", "business", "states", "permission", "functions", "data-operations", "database", "code"]) {
      await child.click("#show-all");
      await child.selectOption("#analysis-view", view);
      await child.click("#expand");
      await child.waitForFunction((view) => document.querySelector("#analysis-view").value === view && graphDebug.graph.boxes.length > 0, view);
      assert.ok(await child.evaluate(() => graphDebug.graph.edges.length > 0), "Missing relationships: " + view);
    }
    await child.selectOption("#analysis-view", "overview"); await child.click("#show-all"); await child.click("#expand");
    await page.click("#case-3d");
    await child.waitForFunction(() => graphDebug.spatial?.perspective && !graphDebug.layoutBusy);
    const layers = await child.evaluate(() => graphDebug.spatial.layerPlanes);
    assert.equal(layers.length, 8);
    await shot(language + "-05-explore-3d");
    await page.click("#case-2d"); await child.waitForFunction(() => !graphDebug.layers.enabled);
    await page.click("#case-tools");
    await page.setViewportSize({width: 390, height: 844}); await go("watch");
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
    await shot(language + "-mobile");
    await page.setViewportSize({width: 1536, height: 1050});
    receipts.push({language, stages: 6, initial_business_nodes: 4, focused_nodes: drillIds.length, custom_nodes: savedNodes.length, saved_view_id: savedId, retained_across_builds: true, retained_after_reload: true, source_and_layer_presets: 8, real_3d_layers: layers.length, native_scroll: true, events_before_replay: eventCount});
  }
  await page.emulateMedia({reducedMotion: "reduce"});
  await page.goto(base + "/demo.html?lang=en"); await go("run");
  const child = await frame(); await page.waitForTimeout(600);
  assert.ok(!(await child.locator("#replay-play").getAttribute("aria-label"))?.match(/Pause|暂停/));
  assert.equal(errors.length, 0, errors.join("\n"));
  await writeFile(path.join(output, "summary.json"), JSON.stringify({passed: true, receipts, reduced_motion: true, errors}, null, 2));
  console.log(JSON.stringify({passed: true, receipts}));
} catch (error) {
  await page?.screenshot({path:path.join(output,"failure.png")});
  const state = await page?.evaluate(() => ({chapter: document.body.dataset.chapter, ready: document.body.dataset.sceneReady, scroll: scrollY}));
  const child = page?.frame({url:/viewer\/index.html/});
  const graph = await child?.evaluate(() => ({view:document.querySelector('#analysis-view').value, nodes:window.graphDebug?.graph?.boxes.map(box=>box.id), stage:window.graphDebug?.view?.stage}));
  await writeFile(path.join(output, "failure.json"), JSON.stringify({scene, state, graph, error: String(error.stack), errors}, null, 2)); throw error;
}
finally {await browser?.close(); server?.kill(); await writeFile(path.join(output, "errors.json"), JSON.stringify(errors, null, 2));}
