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
  process.env.BO_BROWSER_EVIDENCE || "docs/review/spatial-workspace/replay-browser",
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
