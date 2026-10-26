/** Replay an unchanged real recording. This fixture server executes no business code. */
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { createRequire } from "node:module";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import { timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";

const { chromium } = createRequire(import.meta.url)("playwright");
const root = fileURLToPath(new URL("../", import.meta.url));
const assets = path.join(root, "skills/vibelens/assets/stategraph-viewer");
const output = path.resolve(
  process.env.BO_BROWSER_EVIDENCE || "docs/review/spatial-ruler/replay-browser",
);
await mkdir(output, { recursive: true });
const bytes = await readFile(path.join(root, "docs/review/spatial-workspace/replay-fixture.json"));
const recording = JSON.parse(bytes);
const items = timeline(recording);
const commits = recording.runtime_frames.frames.map((f) =>
  items.findIndex((e) => e.id === f.event_id),
);
assert.equal(commits.length, 4);
let preferences = {
  schema: 1,
  project_id: recording.context.model.project_id,
  revision: 0,
  entries: {},
  conflicts: [],
};
const server = createServer(async (request, response) => {
  const route = new URL(request.url, "http://fixture").pathname;
  const json = (data, code = 200) => {
    response.writeHead(code, { "Content-Type": "application/json", "Cache-Control": "no-store" });
    response.end(JSON.stringify(data));
  };
  try {
    if (route === "/api/preferences") {
      if (request.method === "POST") {
        let body = "";
        for await (const chunk of request) body += chunk;
        preferences = { ...JSON.parse(body), revision: preferences.revision + 1 };
      }
      return json(preferences);
    }
    if (request.method !== "GET") return json({ error: "Read-only recorded fixture" }, 405);
    // The recording stores its model/manifest once in context; final is a delta.
    if (route === "/api/view")
      return json({ ...recording.context, ...recording.final, events: recording.events });
    if (route === "/api/design") return json({ available: false });
    if (route === "/api/recordings")
      return json({
        active: null,
        recordings: [{ ...recording, events: recording.events.length }],
      });
    if (route === "/api/recordings/" + recording.id) return json(recording);
    if (route.startsWith("/api/")) return json({ error: "Not provided by replay fixture" }, 404);
    const name =
      route === "/graph" || route === "/" ? "index.html" : decodeURIComponent(route.slice(1));
    const file = path.resolve(assets, name);
    if (!file.startsWith(assets + path.sep)) return json({ error: "Unknown asset" }, 404);
    const body = await readFile(file);
    const type =
      { ".js": "text/javascript", ".css": "text/css", ".html": "text/html" }[path.extname(file)] ||
      "application/octet-stream";
    response.writeHead(200, { "Content-Type": type, "Cache-Control": "no-store" });
    response.end(body);
  } catch (error) {
    json({ error: String(error) }, 404);
  }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
let browser, page;
const errors = [],
  checks = [];
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on("pageerror", (error) => errors.push(String(error)));
  await page.goto(`http://127.0.0.1:${server.address().port}/graph?lang=en`);
  await page.waitForFunction(() => window.graphDebug?.graph);
  await page.selectOption("#record-list", recording.id);
  await page.waitForSelector("#replay", { state: "visible" });
  await page.selectOption("#analysis-view", "states");
  for (const mode of ["2D", "3D"]) {
    if (mode === "3D") await page.click("#layered-toggle");
    await page.waitForFunction(() => !graphDebug.layoutBusy);
    const rows = [];
    for (const [i, raw] of commits.entries()) {
      await page.selectOption("#replay-events", String(raw));
      const changes = await page
        .locator('#change-rows .change-row[data-kind="business"]')
        .evaluateAll((nodes) =>
          nodes.map((node) => ({
            event: node.dataset.eventId,
            owner: node.dataset.owner,
            owners: JSON.parse(node.dataset.owners || "[]"),
            text: node.textContent,
          })),
        );
      assert.equal(changes.length, 1, `${mode}: one actual commit has one displayed flow change`);
      assert.equal(changes[0].owners.length, i ? 2 : 1);
      const expected = ["pending", "in_progress", "awaiting_confirmation", "completed"][i];
      assert.equal(
        await page
          .locator(`#semantic [data-node-id="${changes[0].owner}"]`)
          .getAttribute("data-node-id"),
        "repair." + expected,
      );
      for (const owner of changes[0].owners) {
        const attached = JSON.parse(
          await page.locator(`#semantic [data-node-id="${owner}"]`).getAttribute("data-changes"),
        );
        assert.ok(attached.some((change) => change.kind === "business"));
      }
      await page.locator('#change-rows .change-row[data-kind="business"] button').click();
      assert.equal(
        await page
          .locator(`#semantic [data-node-id="${changes[0].owner}"]`)
          .getAttribute("aria-pressed"),
        "true",
      );
      rows.push(changes[0]);
    }
    checks.push({ mode, rows });
    await page.screenshot({ path: path.join(output, `single-change-${mode.toLowerCase()}.png`) });
  }

  const interactionChecks = [];
  for (const mode of ["3D", "2D"]) {
    if ((await page.locator("#layered-toggle").innerText()) !== mode)
      await page.click("#layered-toggle");
    await page.selectOption("#replay-grain", "events");
    await page.selectOption("#replay-events", String(commits[1]));
    await page.selectOption("#replay-speed", "300");
    await page.click("#replay-play");
    await page.waitForTimeout(150);
    await page.click("#replay-play");
    const paused = await page.locator("#replay-position").getAttribute("data-raw-index");
    const epoch = Number(await page.locator("#renderer").getAttribute("data-animation-epoch"));
    await page.waitForTimeout(1850);
    assert.equal(
      await page.locator("#replay-position").getAttribute("data-raw-index"),
      paused,
      "Paused replay never advances snapshots",
    );
    assert.ok(
      Number(await page.locator("#renderer").getAttribute("data-animation-epoch")) >= epoch + 2,
      "Paused replay repeats the same animation",
    );
    assert.equal(await page.locator("#renderer").getAttribute("data-replay-held"), "true");
    await page.click("#replay-steps-toggle");
    await page.selectOption("#replay-loop-from", items[commits[1]].id);
    await page.selectOption("#replay-loop-to", items[commits[1] + 3].id);
    await page
      .locator(`#replay-step-list input[data-event-id="${items[commits[1] + 1].id}"]`)
      .uncheck();
    await page
      .locator(`#replay-step-list input[data-event-id="${items[commits[1] + 2].id}"]`)
      .uncheck();
    await page.check("#replay-loop");
    const included = await page
      .locator("#replay-events option")
      .evaluateAll((options) => options.map((el) => +el.value));
    assert.deepEqual(included, [commits[1], commits[1] + 3]);
    await page.click("#replay-play");
    const seen = [];
    for (let i = 0; i < 12; i++) {
      seen.push(Number(await page.locator("#replay-position").getAttribute("data-raw-index")));
      await page.waitForTimeout(90);
    }
    await page.click("#replay-play");
    assert.ok(
      included.every((raw) => seen.includes(raw)),
      "Small loop visits both endpoints and wraps",
    );
    assert.ok(
      seen.every((raw) => included.includes(raw)),
      "Skipped steps never appear in playback",
    );
    await page.uncheck("#replay-loop");
    await page.click("#replay-include-all");
    await page.click("#replay-steps-toggle");
    await page.selectOption("#replay-grain", "view");
    await page.selectOption("#replay-events", String(commits.at(-1)));
    if (mode === "3D") {
      const badge = page.locator('[data-spatial-label="repair.completed"] .node-badges');
      assert.equal(await badge.getAttribute("data-run-state"), "active");
    }
    const node = await page
      .locator('#semantic [data-node-type="state"]')
      .first()
      .getAttribute("data-node-id");
    await page.locator(`#semantic [data-node-id="${node}"]`).evaluate((el) => el.click());
    await page.locator("#viewport").focus();
    await page.keyboard.press("f");
    await page.waitForTimeout(180);
    // A real canvas click must leave an earlier text input before Delete.
    await page.locator("#node-search").focus();
    await page.waitForFunction((id) => {
      const el = [...document.querySelectorAll("#semantic [data-node-id]")].find(
        (n) => n.dataset.nodeId === id,
      );
      return (
        el &&
        Number.isFinite(Number(el.dataset.screenX)) &&
        Number.isFinite(Number(el.dataset.screenY)) &&
        el.dataset.screenX !== undefined
      );
    }, node);
    const point = await page
      .locator(`#semantic [data-node-id="${node}"]`)
      .evaluate((el) => ({ x: +el.dataset.screenX, y: +el.dataset.screenY }));
    await page.mouse.click(point.x, point.y);
    assert.equal(await page.evaluate(() => document.activeElement.id), "viewport");
    await page.keyboard.press("Delete");
    assert.equal(
      await page.locator(`#semantic [data-node-id="${node}"]`).count(),
      0,
      "Delete hides selected node",
    );
    await page.click("#show-all");
    const edge = await page
      .locator("#semantic-edges [data-edge-id]")
      .first()
      .getAttribute("data-edge-id");
    await page
      .locator("#semantic-edges [data-edge-id]")
      .first()
      .evaluate((el) => el.click());
    await page.locator("#viewport").focus();
    await page.keyboard.press("Delete");
    assert.equal(
      await page.locator(`#semantic-edges [data-edge-id="${edge}"]`).count(),
      0,
      "Delete hides selected relation",
    );
    await page.click("#show-all");
    const layerCanvas = await page.locator("#layer-controls canvas").boundingBox();
    const layerOrder = await page.evaluate(() => graphDebug.layers.order);
    await page.mouse.click(
      layerCanvas.x + 70,
      layerCanvas.y + 40 + layerOrder.indexOf("state") * 34 + 17,
    );
    await page.keyboard.press("Delete");
    assert.ok(
      !(await page.evaluate(() => graphDebug.layers.visible)).includes("state"),
      "Delete hides selected layer",
    );
    await page.locator("#layers-all").evaluate((el) => el.click());
    await page.selectOption("#analysis-view", "states");
    interactionChecks.push({ mode, paused, included, seen, deleteNodeEdgeLayer: true });
    await page.screenshot({ path: path.join(output, `controls-${mode.toLowerCase()}.png`) });
  }
  assert.equal(
    createHash("sha256")
      .update(await readFile(path.join(root, "docs/review/spatial-workspace/replay-fixture.json")))
      .digest("hex"),
    createHash("sha256").update(bytes).digest("hex"),
  );
  checks.push({ interactions: interactionChecks, rawRecordingUnchanged: true });
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify(
      {
        passed: true,
        kind: "read-only actual recording replay",
        fixture_sha256: createHash("sha256").update(bytes).digest("hex"),
        checks,
        errors,
      },
      null,
      2,
    ),
  );
  console.log(
    "PASS: actual recording shows one fact per transition in 2D/3D, both endpoints retain changes and selection focuses the target.",
  );
} catch (error) {
  await page?.screenshot({ path: path.join(output, "failure.png") }).catch(() => {});
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify({ passed: false, checks, errors, error: String(error.stack) }, null, 2),
  );
  throw error;
} finally {
  await browser?.close();
  await new Promise((resolve) => server.close(resolve));
}
