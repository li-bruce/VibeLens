/** The complete native tool is available only after an explicit request.
 * Prepared-story interaction is covered by test_product_story_browser.py;
 * this suite retains full inventory, presets, source, replay and 3D checks.
 */
import assert from "node:assert/strict";
import { startSite } from "./site_browser_fixture.mjs";
import { createRequire } from "node:module";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(
  process.env.BO_CASE_BROWSER_EVIDENCE || ".validation/file-story/browser",
);
await mkdir(output, { recursive: true });
const artifacts = await Promise.all(
  [1, 2].map(async (version) =>
    JSON.parse(await readFile(`docs/site/case-data/v${version}.json`, "utf8")),
  ),
);
const server = await startSite(),
  results = [],
  errors = [];
let browser, page;
try {
  browser = await chromium.launch({
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
    ...(process.env.BO_BROWSER_EXECUTABLE
      ? { executablePath: process.env.BO_BROWSER_EXECUTABLE }
      : {}),
  });
  for (const language of ["en", "zh-CN"]) {
    const context = await browser.newContext({ viewport: { width: 1536, height: 1050 } });
    page = await context.newPage();
    page.setDefaultTimeout(45000);
    page.on("pageerror", (error) => errors.push(error.message));
    const requests = [];
    page.on("request", (request) => requests.push(request.url()));
    await page.goto(`${server.url}/demo.html?lang=${language}#build`);
    await page.waitForFunction(() => document.body.dataset.sceneReady === "build");
    assert.equal(await page.locator("#case-graph").getAttribute("src"), "about:blank");
    assert.ok(!requests.some((url) => /case-preview\/v[12]\.json/.test(url)));
    await page.click("#case-tools");
    await page.waitForFunction(() => document.body.dataset.sceneReady === "build");
    let child = page.frame({ url: /viewer\/index.html\?case=/ });
    await child.waitForFunction(
      () => window.graphDebug?.view.code_structure?.loaded_nodes > 0 && !graphDebug.layoutBusy,
    );
    assert.equal(await child.locator("html").getAttribute("lang"), language);
    assert.equal(
      await child.evaluate(() => graphDebug.view.code_structure.loaded_nodes),
      artifacts[0].code.nodes.length,
    );
    // Every original artifact remains available through the existing adapter.
    const archived = await child.evaluate(
      async () => await (await fetch("/api/recordings")).json(),
    );
    assert.ok(JSON.stringify(archived).includes(artifacts[0].recording.id));
    const profiles = [
      "business",
      "states",
      "functions",
      "permission",
      "data-operations",
      "database",
      "code",
      "api",
    ];
    for (const profile of profiles) {
      await child.selectOption("#analysis-view", profile);
      await child.click("#expand");
      await child.waitForFunction(
        (profile) =>
          document.querySelector("#analysis-view").value === profile &&
          graphDebug.graph.boxes.length > 0 &&
          !graphDebug.layoutBusy,
        profile,
      );
      assert.ok(
        await child.evaluate(() => graphDebug.graph.edges.length > 0),
        `Missing relations: ${profile}`,
      );
      if (profile === "states") {
        const ids = await child
          .locator("#semantic [data-node-id]")
          .evaluateAll((nodes) => nodes.map((n) => n.dataset.nodeId));
        for (const id of ["state_empty", "state_private", "state_shared"])
          assert.ok(ids.includes(id), `Missing state ${id}`);
      }
    }
    await page.click('[data-case-lens="all"]');
    await page.waitForFunction(() => document.body.dataset.lensReady === "all");
    await child.waitForFunction(() => !graphDebug.layoutBusy);
    await page.click("#case-3d");
    await child.waitForFunction(() => graphDebug.spatial?.perspective && !graphDebug.layoutBusy);
    const layers = await child.evaluate(() =>
      graphDebug.spatial.layerPlanes.map((layer) => layer.id),
    );
    for (const id of ["business", "state", "rules", "entry", "structure", "symbols", "data"])
      assert.ok(layers.includes(id), `Missing layer ${id}`);
    await page.screenshot({ path: path.join(output, `${language}-full-tool.png`) });
    await page.click("#case-2d");
    await child.waitForFunction(() => !graphDebug.layers.enabled);
    // Source navigation still reads the original complete file in the native tool.
    await page.click('#case-chapters a[href="#drill"]');
    await page.waitForFunction(() => document.body.dataset.sceneReady === "drill");
    await page.click('[data-scene-action="case.drill"]');
    await child.locator("#source-code").waitFor({ state: "visible" });
    assert.ok(
      (await child.locator("#source-code").textContent()).includes(
        artifacts[0].story.source_excerpt,
      ),
    );
    // A new build must get its own complete archive, not a mixed v1/v2 graph.
    await page.click('#case-chapters a[href="#verify"]');
    await page.waitForFunction(() => document.body.dataset.sceneReady === "verify");
    child = page.frame({ url: /viewer\/index.html\?case=2/ });
    await child.waitForFunction(
      () => graphDebug.view.code_structure?.loaded_nodes > 0 && !graphDebug.layoutBusy,
    );
    assert.equal(
      await child.evaluate(() => graphDebug.view.code_structure.loaded_nodes),
      artifacts[1].code.nodes.length,
    );
    await page.click("#verify [data-capture-action]");
    await page.locator('[data-app-action="download-after"]:enabled').waitFor();
    await page.click('[data-app-action="download-after"]');
    await child.waitForFunction(
      (id) => graphDebug.view.replay?.event?.id === id,
      artifacts[1].story.actions.at(-1).event_ids[0],
    );
    assert.equal(await child.evaluate(() => graphDebug.view.replay.event.outputs.allowed), false);
    await page.click("#verify [data-capture-action]");
    await page.click("#case-tools");
    await page.locator("#case-prepared:not([hidden])").waitFor();
    assert.ok(await page.locator("#case-graph").isHidden());
    assert.ok(await page.locator("#case-loading").isHidden());
    assert.ok(Number(await page.locator("#case-prepared").getAttribute("data-switch-ms")) < 250);
    results.push({
      language,
      profiles: profiles.length,
      layers,
      full_source: true,
      denied_recording: true,
      lazy_inventory: true,
    });
    await context.close();
  }
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(output, "summary.json"),
    JSON.stringify({ passed: true, results, errors }, null, 2),
  );
  console.log(
    "PASS: explicit complete tool, eight native presets, complete states, code inventory, source, original recordings and 3D layers",
  );
} catch (error) {
  await page?.screenshot({ path: path.join(output, "failure.png") }).catch(() => {});
  await writeFile(
    path.join(output, "failure.json"),
    JSON.stringify({ error: error.stack, results, errors }, null, 2),
  );
  throw error;
} finally {
  await browser?.close();
  server.close();
}
