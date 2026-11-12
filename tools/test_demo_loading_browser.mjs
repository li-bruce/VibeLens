/** Delay and fail real transports: the conversation stays usable and retry restores the graph. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile, stat } from "node:fs/promises";
import path from "node:path";
import { startSite } from "./site_browser_fixture.mjs";
const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(process.env.BO_LOADING_EVIDENCE || ".validation/demo-loading");
await mkdir(output, { recursive: true });
const server = await startSite(),
  results = [];
let browser;
try {
  browser = await chromium.launch({ headless: true, args: ["--enable-unsafe-swiftshader"] });
  for (const language of ["en", "zh-CN"]) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    page.setDefaultTimeout(45000);
    const requests = [],
      errors = [];
    page.on("request", (request) =>
      requests.push({ url: request.url(), parent: request.frame() === page.mainFrame() }),
    );
    page.on("pageerror", (error) => errors.push(error.message));
    let release, requested;
    const held = new Promise((resolve) => (release = resolve)),
      started = new Promise((resolve) => (requested = resolve));
    await page.route("**/case-preview/v1.json", async (route) => {
      requested();
      await held;
      await route.continue();
    });
    try {
      await page.goto(server.url + "/demo.html?lang=" + language, {
        waitUntil: "domcontentloaded",
      });
      await page.locator("#foundation").waitFor();
      await started;
      const shellMs = await page.evaluate(() => performance.now());
      assert.equal(await page.locator("html").getAttribute("lang"), language);
      assert.equal(await page.locator("#case-loading").getAttribute("data-phase"), "data");
      await page.locator('#case-chapters a[href="#foundation"]').click();
      for (let i = 0; i < 3; i++) await page.locator("#conversation-next").click();
      assert.equal(await page.locator(".confirmation-tabs button").count(), 3);
      assert.ok(
        await page.locator(".conversation-flow").isVisible(),
        "Model confirmation works while recording is delayed",
      );
      assert.ok(
        !requests.some((r) => /case-data\/v[12]\.json/.test(r.url)),
        "No full artifact in the parent or child",
      );
      assert.ok(
        !requests.some((r) => /case-preview\/v2\.json/.test(r.url)),
        "The repaired build is deferred",
      );
      await page.locator("#run").evaluate((el) => el.scrollIntoView({ behavior: "instant" }));
      await page.screenshot({ path: path.join(output, language + "-loading.png") });
      release();
      await page.waitForFunction(() => document.body.dataset.sceneReady === "run");
      assert.ok(await page.locator("#case-loading").isHidden());
      const frame = page.frame({ url: /viewer\/index.html/ });
      await page.locator('[data-case-lens="rules"]').click();
      await page.waitForFunction(() => document.body.dataset.lensReady === "rules");
      const rules = await frame.evaluate(() => ({
        nodes: [...graphDebug.presentation.glyphs],
        edges: graphDebug.presentation.edges.length,
      }));
      assert.ok(rules.nodes.length >= 6 && rules.edges > 0, "Rules remain a connected native lens");
      await page.screenshot({ path: path.join(output, language + "-rules.png") });
      assert.deepEqual(errors, []);
      results.push({ language, shell_ms: Math.round(shellMs), delayed_recording: true, rules });
    } finally {
      release();
      await page.close();
    }
  }
  // A real HTTP failure must expose a retry action, not an indefinitely blank canvas.
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.setDefaultTimeout(45000);
  let fail = true;
  await page.route("**/case-preview/v1.json", async (route) => {
    if (fail) {
      fail = false;
      await route.fulfill({ status: 503, body: "Unavailable" });
    } else await route.continue();
  });
  await page.goto(server.url + "/demo.html?lang=zh-CN#run", { waitUntil: "domcontentloaded" });
  await page.waitForFunction(
    () => document.querySelector("#case-loading").dataset.phase === "error",
  );
  await page.screenshot({ path: path.join(output, "retry.png") });
  await page.locator("#case-retry").click();
  await page.waitForFunction(() => document.body.dataset.sceneReady === "run");
  assert.ok(await page.locator("#case-loading").isHidden());
  results.push({ http_failure_retry: true });
  await page.close();
  const sizes = {};
  for (const file of [
    "case-data/v1.json",
    "case-data/v2.json",
    "case-preview/story.json",
    "case-preview/v1.json",
    "case-preview/v2.json",
  ])
    sizes[file] = (await stat("docs/site/" + file)).size;
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify(
      {
        valid: true,
        results,
        sizes,
        boundary: "Local Chromium; delayed and failed HTTP responses, not public-network timing.",
      },
      null,
      2,
    ) + "\n",
  );
  console.log(
    "PASS: immediate bilingual conversation, delayed graph feedback, native rules, lazy versions and HTTP retry",
  );
} catch (error) {
  await writeFile(
    path.join(output, "failure.json"),
    JSON.stringify({ valid: false, results, error: error.stack }, null, 2) + "\n",
  );
  throw error;
} finally {
  await browser?.close();
  server.close();
}
