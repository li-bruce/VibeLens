/** Exercise the naming switch through native controls over real recorded execution. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import { serveRecording } from "./recording_browser_fixture.mjs";
import { analysisPreferences, waitForPreferences } from "./browser-preferences.mjs";

const { chromium } = createRequire(import.meta.url)("playwright");
const out = path.resolve(process.env.BO_NAMES_EVIDENCE || ".validation/semantic-names-browser");
await mkdir(out, { recursive: true });
const source = "docs/review/recording-timeline/real-project-completion/v2-recording.json",
  names = JSON.parse(await readFile("docs/review/semantic-names/preview-names.json", "utf8")),
  fixture = await serveRecording(source, { names });
const errors = [],
  checks = [];
let browser, page;
const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (error) => errors.push(String(error.stack)));
  await page.goto(fixture.url + "?lang=zh-CN");
  await page.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
  const toggle = page.locator("#name-mode"),
    node = page.locator('#semantic [data-node-id="login"]');
  assert.equal(await node.innerText(), "登录");
  const geometry = () =>
    page.evaluate(() => ({
      points: graphDebug.graph.boxes.map((b) => [b.id, b.x, b.y]),
      camera: graphDebug.camera,
    }));
  const before = await geometry();
  const beforeSourceNames = await page.evaluate(
    async () => (await (await fetch("/api/preferences")).json()).revision,
  );
  const sourceNamesSave = waitForPreferences(
    page,
    (saved) => analysisPreferences(saved)?.explainedNames === false,
    { afterRevision: beforeSourceNames },
  );
  await toggle.click();
  assert.equal(await toggle.getAttribute("aria-checked"), "false");
  assert.equal(await node.innerText(), "SharingService.authenticate");
  assert.deepEqual(await geometry(), before);
  assert.ok((await page.locator("#semantic-edges").allTextContents())[0].includes("flow"));
  await page.fill("#node-search", "登录");
  assert.ok(
    (await page.locator("#search-results").innerText()).includes("SharingService.authenticate"),
  );
  await page.fill("#node-search", "");
  checks.push("Source names retain layout; both names remain searchable");
  await page.screenshot({ path: path.join(out, "source-2d.png") });
  // Project settings, including the switch, survive an actual reload.
  await sourceNamesSave;
  await page.reload();
  await page.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
  assert.equal(await toggle.getAttribute("aria-checked"), "false");
  assert.equal(await node.innerText(), "SharingService.authenticate");
  await toggle.click();
  assert.equal(await node.innerText(), "登录");
  checks.push("Project preference survives reload");

  await page.selectOption("#record-list", fixture.recording.id);
  await page.waitForSelector("#recording-timeline canvas", { state: "visible" });
  await page.selectOption("#replay-grain", "events");
  const loginRaw = await page.evaluate(
    () =>
      [...document.querySelectorAll("#replay-events option")].find((o) =>
        o.textContent.includes("登录"),
      )?.value,
  );
  assert.ok(loginRaw);
  await page.selectOption("#replay-events", loginRaw);
  const cursor = () =>
    page.evaluate(() => ({
      raw: graphDebug.timeline.raw,
      event: graphDebug.timeline.eventId,
      window: graphDebug.timeline.window,
      transfers: graphDebug.timeline.transfers,
    }));
  const recorded = await cursor();
  await toggle.click();
  assert.deepEqual(await cursor(), recorded);
  assert.ok(
    (await page.locator(".trace-selected").innerText()).includes("SharingService.authenticate"),
  );
  await toggle.click();
  assert.deepEqual(await cursor(), recorded);
  assert.ok((await page.locator(".trace-selected").innerText()).includes("登录"));
  checks.push("Timeline and graph keep one event cursor and transfer path");

  for (const mode of ["2D", "3D"]) {
    if ((await page.locator("#layered-toggle").innerText()) !== mode)
      await page.click("#layered-toggle");
    await page.selectOption("#analysis-view", "states");
    await page.waitForFunction(() => !graphDebug.layoutBusy);
    const state = page.locator('#semantic [data-node-id="state_shared"]');
    assert.equal(await state.innerText(), "已共享给接收者");
    await toggle.click();
    assert.equal(await state.innerText(), "shared");
    if (mode === "3D")
      assert.equal(
        await page.locator('[data-spatial-label="state_shared"] .spatial-label-title').innerText(),
        "shared",
      );
    await toggle.click();
    assert.equal(await state.innerText(), "已共享给接收者");
    if (mode === "3D")
      assert.equal(
        await page.locator('[data-spatial-label="state_shared"] .spatial-label-title').innerText(),
        "已共享给接收者",
      );
    await page.screenshot({ path: path.join(out, `explained-${mode.toLowerCase()}.png`) });
    checks.push(`${mode}: executable state names switch consistently`);
  }
  await page.goto(fixture.url + "?lang=en");
  await page.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
  assert.equal(await page.locator("#name-mode").innerText(), "Semantic labels");
  await page.selectOption("#analysis-view", "business");
  assert.equal(await node.innerText(), "Sign in");
  // White-box cache regression complements the native controls above: replacing
  // only the display overlay must refresh text without scheduling another layout.
  const cachedUpdate = await page.evaluate(async () => {
    const { SpatialRenderer } = await import("/spatial-renderer.js");
    const cached = Object.create(SpatialRenderer.prototype);
    cached.scope = "name-cache-test";
    let layouts = 0,
      rendered = [];
    cached.seedMissing = () => {};
    cached.layout = () => layouts++;
    cached.rebuild = cached.updateEmphasis = () => {
      rendered = cached.model.nodes.map((n) => n.label);
    };
    const input = {
      // Spatial projection reads declarations and boxes. The live graph also
      // carries filter callbacks, which are not part of this data contract and
      // cannot be structured-cloned with the labels under inspection.
      graph: structuredClone({
        boxes: graphDebug.displayGraph.boxes,
        all: graphDebug.displayGraph.all,
      }),
      presentation: graphDebug.presentation,
      scope: cached.scope,
      preferences: { annotations: {}, nameMode: "explained" },
      focusContext: { nodes: new Set() },
      settings: graphDebug.layers,
      boTransfers: new Map(),
      routing: "straight",
    };
    cached.update(input);
    const before = layouts;
    input.graph.boxes[0].node.label = "Updated human explanation";
    cached.update(input);
    return {
      updated: rendered.includes("Updated human explanation"),
      layoutsUnchanged: layouts === before,
    };
  });
  assert.deepEqual(cachedUpdate, { updated: true, layoutsUnchanged: true });
  checks.push("Changed 3D display labels invalidate text cache without relayout");
  assert.equal(hash(await readFile(source)), hash(fixture.bytes));
  assert.deepEqual(fixture.writes, []);
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify(
      {
        valid: true,
        browser: await browser.version(),
        checks,
        recordingSHA256: hash(fixture.bytes),
        businessWrites: fixture.writes,
        errors,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(JSON.stringify({ valid: true, out, checks }));
} catch (error) {
  await page?.screenshot({ path: path.join(out, "failure.png") }).catch(() => {});
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify({ valid: false, error: String(error.stack), errors, checks }, null, 2) + "\n",
  );
  throw error;
} finally {
  await browser?.close();
  await fixture.close();
}
