/** Exercise the recorded file-sharing story through native viewer interactions. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const base = (process.env.BO_SITE_URL || "http://127.0.0.1:8897").replace(/\/$/, "");
const output = path.resolve(
  process.env.BO_CASE_BROWSER_EVIDENCE || ".validation/file-story/browser",
);
await mkdir(output, { recursive: true });
const artifacts = await Promise.all(
  [1, 2].map(async (version) =>
    JSON.parse(await readFile(`docs/site/case-data/v${version}.json`, "utf8")),
  ),
);
const first = artifacts[0],
  fixed = artifacts[1];
const inspection = (artifact) =>
  artifact.recording.events.find((event) => event.id === artifact.story.inspection_event);
const python =
  process.env.BO_PYTHON ||
  path.resolve(".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const server = process.env.BO_SITE_URL
  ? null
  : spawn(
      python,
      ["-B", "-m", "http.server", "8897", "--bind", "127.0.0.1", "--directory", "docs/site"],
      { windowsHide: true, stdio: "ignore" },
    );
let browser, page, scene;
const errors = [],
  receipts = [];
async function frame() {
  const child = page.frame({ url: /viewer\/index.html\?case=/ });
  assert.ok(child);
  await child.waitForFunction(() => window.graphDebug?.graph?.boxes.length > 0);
  return child;
}
async function go(id) {
  scene = id;
  await page.locator("#" + id).scrollIntoViewIfNeeded();
  await page.waitForFunction((id) => document.body.dataset.sceneReady === id, id, {
    timeout: 45000,
  });
  assert.equal(await page.getAttribute("#case-context", "data-scene"), id);
  const coding = ["foundation", "iterate"].includes(id);
  assert.equal(await page.locator("#case-conversation .conversation-turns").isVisible(), coding);
  assert.equal(
    await page.getAttribute("#case-conversation", "data-mode"),
    coding ? "current" : "history",
  );
  assert.equal(await page.locator(".case-playback").isVisible(), ["run", "verify"].includes(id));
  return frame();
}
async function shot(name) {
  await page.waitForTimeout(300);
  await page.screenshot({ path: path.join(output, name + ".png") });
}
// Count what the two renderers actually display. The layout inventory can retain
// source-boundary boxes whose type is hidden and has no glyph or accessible button.
const boxIds = async (child) => {
  await child.waitForFunction(() => {
    const visible = new Set([
      ...graphDebug.presentation.glyphs.keys(),
      ...graphDebug.presentation.regions.keys(),
    ]);
    const semantic = [...document.querySelectorAll("#semantic [data-node-id]")];
    return (
      semantic.length === visible.size && semantic.every((node) => visible.has(node.dataset.nodeId))
    );
  });
  return child.evaluate(() =>
    [
      ...new Set([
        ...graphDebug.presentation.glyphs.keys(),
        ...graphDebug.presentation.regions.keys(),
      ]),
    ].sort(),
  );
};
/** Keep gestures inside the visible canvas, away from clipped iframe edges and toolbars. */
async function cameraPoint(child) {
  const canvas = await child.locator(".spatial-canvas").boundingBox(),
    viewport = page.viewportSize(),
    top = Math.max(0, canvas.y),
    bottom = Math.min(viewport.height, canvas.y + canvas.height),
    left = Math.max(0, canvas.x),
    right = Math.min(viewport.width, canvas.x + canvas.width);
  assert.ok(bottom - top > 180 && right - left > 240, "A visible canvas must receive the gesture");
  for (const ratio of [0.17, 0.78, 0.32]) {
    const point = { x: left + (right - left) * ratio, y: top + 135 };
    const onCanvas = await child.evaluate(
      ({ point, canvas }) => {
        const element = document.querySelector(".spatial-canvas"),
          local = element.getBoundingClientRect();
        return (
          document.elementFromPoint(local.x + point.x - canvas.x, local.y + point.y - canvas.y) ===
          element
        );
      },
      { point, canvas },
    );
    if (
      onCanvas &&
      (await page.evaluate(
        (point) => document.elementFromPoint(point.x, point.y)?.id === "case-graph",
        point,
      ))
    )
      return point;
  }
  throw Error("The camera gesture is covered by another element");
}
try {
  for (let attempt = 0; attempt < 60; attempt++) {
    try {
      if ((await fetch(base)).ok) break;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  browser = await chromium.launch({
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
    ...(process.env.BO_BROWSER_EXECUTABLE
      ? { executablePath: process.env.BO_BROWSER_EXECUTABLE }
      : {}),
  });
  page = await browser.newPage({ viewport: { width: 1536, height: 1050 } });
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 400) errors.push(response.status() + " " + response.url());
  });
  await page.route("**/case-viewer.mjs*", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 400));
    await route.continue();
  });
  for (const language of ["en", "zh-CN"]) {
    await page.goto(base + "/demo.html?lang=" + language);
    let child = await go("foundation");
    assert.equal(await child.evaluate(() => graphDebug.layoutAlgorithm), "cluster");
    assert.equal(await page.locator("[data-case-scene]").count(), 5);
    for (const title of await page.locator("h1,h2,h3").allTextContents())
      assert.ok(!/[.。]$/.test(title.trim()));
    assert.deepEqual(await boxIds(child), first.story.business.slice().sort());
    assert.equal(await child.evaluate(() => graphDebug.view.stage), "design");
    assert.equal(await page.locator(".case-application").isVisible(), false);
    assert.equal(await page.locator("#case-conversation [data-speaker]").count(), 1);
    assert.equal(await page.locator(".conversation-flow").count(), 0);
    for (let turn = 0; turn < 3; turn++) await page.click("#conversation-next");
    assert.equal(await page.locator('.conversation-flow[data-confirmed="false"]').count(), 1);
    assert.deepEqual(
      (
        await page
          .locator("[data-intent-node]")
          .evaluateAll((nodes) => nodes.map((node) => node.dataset.intentNode))
      ).sort(),
      first.story.business.slice().sort(),
    );
    await shot(language + "-proposed-flow");
    await page.click("#conversation-next");
    assert.equal(await page.locator('.conversation-flow[data-confirmed="true"]').count(), 1);
    await page.click("#conversation-next");
    child = await go("run");
    await page.click("#case-play");
    const area = await page.locator(".case-visual").boundingBox(),
      chat = await page.locator("#case-conversation").boundingBox(),
      app = await page.locator("#case-application").boundingBox();
    assert.ok(chat.x + chat.width <= area.x + 1);
    assert.ok(app.x >= area.x + area.width - 1);
    await page.click('[data-case-lens="states"]');
    await child.waitForFunction(
      (ids) => ids.every((id) => graphDebug.graph.boxes.some((box) => box.id === id)),
      first.story.states,
    );
    assert.ok(await child.evaluate(() => graphDebug.graph.edges.length > 0));
    await page.click('[data-case-lens="business"]');
    await child.waitForFunction(
      (count) => graphDebug.graph.boxes.length === count,
      first.story.business.length,
    );
    await page.click("#case-3d");
    await child.waitForFunction(() => graphDebug.spatial?.perspective && !graphDebug.layoutBusy);
    await page.waitForTimeout(350);
    const camera = () => child.evaluate(() => graphDebug.spatial.camera);
    const before = await camera(),
      { x, y } = await cameraPoint(child);
    await page.mouse.move(x, y);
    await page.mouse.down();
    await page.mouse.move(x + 110, y - 70, { steps: 16 });
    await page.mouse.up();
    await page.waitForTimeout(350);
    const rotated = await camera();
    assert.notDeepEqual(rotated.position, before.position);
    await page.mouse.move(x + 30, y - 20);
    const scroll = await page.evaluate(() => scrollY);
    await page.mouse.wheel(0, -180);
    await page.waitForTimeout(350);
    const zoomed = await camera(),
      distance = (value) => Math.hypot(...value.position.map((n, i) => n - value.target[i]));
    assert.ok(distance(zoomed) < distance(rotated));
    assert.equal(await page.evaluate(() => scrollY), scroll);
    await page.mouse.down({ button: "right" });
    await page.mouse.move(x + 95, y - 50, { steps: 12 });
    await page.mouse.up({ button: "right" });
    await page.waitForTimeout(350);
    assert.notDeepEqual((await camera()).target, zoomed.target);
    await shot(language + "-camera");
    await page.click('[data-case-lens="implementation"]');
    await child.waitForFunction(
      (id) => graphDebug.graph.boxes.some((box) => box.id === id),
      first.story.focus.inputs[0],
    );
    await page.click("#case-2d");
    await child.waitForFunction(() => !graphDebug.layers.enabled);
    await page.click('[data-case-lens="business"]');
    const viewport = await page.locator("#case-graph").boundingBox();
    await page.mouse.move(viewport.x + viewport.width / 2, viewport.y + viewport.height / 2);
    const oldScroll = await page.evaluate(() => scrollY);
    await page.mouse.wheel(0, 200);
    await page.waitForTimeout(200);
    assert.ok(await page.evaluate((old) => scrollY > old + 20, oldScroll));
    // Camera exploration changed the lens; re-enter the story's recorded path.
    await go("foundation");
    child = await go("run");
    await page.click('[data-scene-action="case.run"]');
    await child.waitForFunction(() => graphDebug.view.replay?.event?.id);
    const start = await child.evaluate(() => graphDebug.view.replay.index);
    await page.waitForTimeout(1100);
    assert.ok(await child.evaluate((start) => graphDebug.view.replay.index > start, start));
    // This case witnesses rule dependencies and data transfers, not invented
    // business causality between independent HTTP requests.
    await child.waitForFunction(
      () =>
        JSON.parse(document.querySelector("#renderer").dataset.animatedEdges || "[]").length > 0,
      null,
      { timeout: 30000 },
    );
    const motion = await child.locator("#viewport canvas").first().screenshot();
    await page.waitForTimeout(180);
    assert.notDeepEqual(motion, await child.locator("#viewport canvas").first().screenshot());
    await writeFile(path.join(output, language + "-motion.png"), motion);
    const raw = await child.evaluate(async () => (await (await fetch("/api/view")).json()).events);
    async function appAction(id, artifact = first) {
      const action = artifact.story.actions.find((action) => action.id === id);
      await page.click(`[data-app-action="${id}"]`);
      await child.waitForFunction(
        (ids) => ids.includes(graphDebug.view.replay?.event?.id),
        action.event_ids,
      );
      await page.waitForFunction(
        (ids) => ids.includes(document.querySelector("#case-application").dataset.eventId),
        action.event_ids,
      );
    }
    for (const id of ["download-before", "revoke", "download-after", "download-before"])
      await appAction(id);
    assert.ok(
      await child.evaluate(
        (eventId) => graphDebug.view.replay.event.id === eventId,
        first.story.actions[0].event_ids[0],
      ),
    );
    assert.deepEqual(
      await child.evaluate(async () => (await (await fetch("/api/view")).json()).events),
      raw,
    );
    child = await go("drill");
    await child.waitForFunction(
      (id) => graphDebug.view.replay?.event?.id === id,
      first.story.inspection_event,
    );
    await page.waitForFunction(() =>
      document.querySelector("#case-telemetry").textContent.includes("shared"),
    );
    assert.deepEqual(
      await page.locator("#case-telemetry strong").allTextContents(),
      first.story.telemetry.map((field) => String(inspection(first).outputs[field.field])),
    );
    await child.waitForFunction(
      (excerpt) => document.querySelector("#source-code").textContent.includes(excerpt),
      first.story.source_excerpt,
    );
    assert.ok(
      (await child.locator("#source-code mark").allTextContents()).join(" ").includes("revoke"),
    );
    const graphBounds = await child.locator("#viewport").boundingBox(),
      sourceBounds = await child.locator("#node-details").boundingBox();
    assert.ok(graphBounds.x + graphBounds.width <= sourceBounds.x + 2);
    const focused = await boxIds(child);
    assert.ok(focused.length <= 18);
    for (const id of first.story.focus.inputs) assert.ok(focused.includes(id));
    await page.locator("#case-application .app-frame").click();
    assert.ok(await page.locator(".app-capture-dialog").isVisible());
    await page.keyboard.press("Escape");
    await shot(language + "-source");
    await page.locator(".view-editor summary").click();
    const effect = first.story.focus.effects[0];
    await page.locator('[data-watch="effects"]').check();
    await child.waitForFunction(
      (id) => graphDebug.graph.boxes.some((box) => box.id === id),
      effect,
    );
    await page.locator('[data-watch="effects"]').uncheck();
    await child.waitForFunction(
      (id) => !graphDebug.graph.boxes.some((box) => box.id === id),
      effect,
    );
    await page.locator('[data-watch="effects"]').check();
    await child.waitForFunction(
      (id) => graphDebug.graph.boxes.some((box) => box.id === id),
      effect,
    );
    await page.locator('[data-watch="states"]').check();
    await child.waitForFunction(
      (id) => graphDebug.graph.boxes.some((box) => box.id === id),
      first.story.states[0],
    );
    await page.fill("#watch-name", "Alternate path");
    await page.click("#save-watch");
    await page.waitForFunction(() => document.body.dataset.savedView?.startsWith("custom-"));
    const alternate = await page.getAttribute("body", "data-saved-view");
    const name = language === "en" ? "Revocation analysis" : "取消共享排查";
    await page.fill("#watch-name", name);
    await page.click("#save-watch");
    await page.waitForFunction(
      (previous) => document.body.dataset.savedView !== previous,
      alternate,
    );
    const saved = await page.getAttribute("body", "data-saved-view"),
      savedNodes = await boxIds(child);
    assert.ok(savedNodes.length <= 30);
    assert.ok(await child.evaluate(() => graphDebug.graph.edges.length > 4));
    await child.waitForFunction(
      async (name) =>
        JSON.stringify((await (await fetch("/api/preferences")).json()).entries).includes(name),
      name,
    );
    child = await go("iterate");
    await child.waitForFunction(
      ({ saved, id }) =>
        document.querySelector("#analysis-view").value === saved &&
        graphDebug.view.replay?.event?.id === id,
      { saved, id: fixed.story.inspection_event },
    );
    await page.waitForFunction(() =>
      document.querySelector("#case-telemetry").textContent.includes("private"),
    );
    assert.deepEqual(
      await page.locator("#case-telemetry strong").allTextContents(),
      fixed.story.telemetry.map((field) => String(inspection(fixed).outputs[field.field])),
    );
    await page.click('[data-scene-action="case.repair"]');
    await child.waitForFunction(
      (excerpt) => document.querySelector("#source-code").textContent.includes(excerpt),
      fixed.story.source_excerpt,
    );
    assert.deepEqual(await boxIds(child), savedNodes);
    // Opening source must locate the relevant function even when a saved view
    // contains large expanded regions. The view membership itself is unchanged.
    await child.waitForFunction((id) => {
      const box = graphDebug.graph.byId.get(id),
        { scale, pan } = graphDebug.camera,
        viewport = document.querySelector("#viewport"),
        x = (box.x + box.w / 2) * scale + pan.x,
        y = (box.y + box.h / 2) * scale + pan.y;
      return x > 0 && y > 0 && x < viewport.clientWidth && y < viewport.clientHeight;
    }, fixed.story.inspection_node);
    await shot(language + "-repair");
    await page.reload();
    child = await go("iterate");
    await child.waitForFunction(
      (saved) => document.querySelector("#analysis-view").value === saved,
      saved,
    );
    assert.deepEqual(await boxIds(child), savedNodes);
    child = await go("verify");
    assert.equal(await child.getAttribute("body", "data-policy-comparison"), "true");
    assert.match(await page.locator(".rule-change").textContent(), /recipient|接收者/);
    await appAction("download-after", fixed);
    assert.equal(await child.evaluate(() => graphDebug.view.replay.event.outputs.allowed), false);
    await page.click("#case-tools");
    await child.click("#replay-live");
    for (const profile of [
      "business",
      "states",
      "functions",
      "permission",
      "data-operations",
      "database",
      "code",
      "api",
    ]) {
      await child.selectOption("#analysis-view", profile);
      await child.click("#expand");
      await child.waitForFunction(
        (profile) =>
          document.querySelector("#analysis-view").value === profile &&
          graphDebug.graph.boxes.length > 0 &&
          !graphDebug.layoutBusy,
        profile,
        { timeout: 45000 },
      );
      assert.ok(
        await child.evaluate(() => graphDebug.graph.edges.length > 0),
        "Missing relations: " + profile,
      );
    }
    await page.click('[data-case-lens="all"]');
    await page.waitForFunction(() => document.body.dataset.lensReady === "all");
    await child.waitForFunction(
      (count) => graphDebug.view.code_structure?.loaded_nodes === count && !graphDebug.layoutBusy,
      fixed.code.nodes.length,
    );
    await page.click("#case-3d");
    await child.waitForFunction(() => graphDebug.spatial?.perspective && !graphDebug.layoutBusy);
    const layers = await child.evaluate(() => graphDebug.spatial.layerPlanes);
    assert.deepEqual(
      layers.map((layer) => layer.id).sort(),
      [
        "api",
        "business",
        "state",
        "rules",
        "operations",
        "execution",
        "data",
        "project",
        "code",
      ].sort(),
    );
    await shot(language + "-all-layers");
    await page.click("#case-2d");
    await child.waitForFunction(() => !graphDebug.layers.enabled);
    await page.click("#case-tools");
    await page.setViewportSize({ width: 390, height: 844 });
    child = await go("drill");
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
    assert.equal(await page.locator("#drill .case-application").count(), 1);
    await shot(language + "-mobile");
    await page.click("#language");
    await page.waitForFunction((previous) => document.documentElement.lang !== previous, language);
    await go("drill");
    assert.equal(await page.locator("#drill .case-application").count(), 1);
    await page.click("#language");
    await go("drill");
    await page.setViewportSize({ width: 1536, height: 1050 });
    receipts.push({
      language,
      stages: 5,
      confirmed_nodes: first.story.business.length,
      focused_nodes: focused.length,
      saved_nodes: savedNodes.length,
      saved_view: saved,
      original_recording_preserved: true,
      real_motion: true,
      actual_source_and_capture: true,
      saved_across_builds_and_reload: true,
      rotate_zoom_pan: true,
      presets: 8,
      code_nodes: fixed.code.nodes.length,
      layers: layers.length,
      mobile: true,
    });
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(base + "/demo.html?lang=en");
  const child = await go("run");
  await page.waitForTimeout(600);
  assert.ok(!/Pause|暂停/.test(await child.locator("#replay-play").getAttribute("aria-label")));
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(output, "summary.json"),
    JSON.stringify({ passed: true, receipts, reduced_motion: true, errors }, null, 2),
  );
  console.log(JSON.stringify({ passed: true, receipts }));
} catch (error) {
  await page?.screenshot({ path: path.join(output, "failure.png") });
  const child = page?.frame({ url: /viewer\/index.html\?case=/ });
  const graph = await child?.evaluate(() => ({
    nodes: window.graphDebug?.graph?.boxes.map((box) => box.id),
    view: document.querySelector("#analysis-view")?.value,
    stage: window.graphDebug?.view?.stage,
    replay: window.graphDebug?.view?.replay?.id,
    layout_busy: window.graphDebug?.layoutBusy,
    record_choice: document.querySelector("#record-list")?.value,
    source_disabled: document.querySelector("#source")?.disabled,
  }));
  await writeFile(
    path.join(output, "failure.json"),
    JSON.stringify({ scene, error: String(error.stack), graph, errors }, null, 2),
  );
  throw error;
} finally {
  await browser?.close();
  server?.kill();
}
