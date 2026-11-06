/** Real observer HTTP + node details in both renderers; optional real AI provider.
 * No browser routes, application responses or graph evidence are replaced.
 */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(process.env.BO_CONCEPT_EVIDENCE || ".validation/node-details-browser");
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.BO_BROWSER_EXECUTABLE,
  args: ["--enable-unsafe-swiftshader"],
});
const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
const errors = [],
  checks = [];
page.on("pageerror", (error) => errors.push(error.message));
async function select(id) {
  await page.locator("#semantic [data-node-id]").evaluateAll((elements, identity) => {
    const element = elements.find((item) => item.dataset.nodeId === identity);
    assertElement(element, identity);
    function assertElement(item, value) {
      if (!item) throw Error("Node is not visible: " + value);
    }
    element.click();
  }, id);
  await page.locator("#viewport").focus();
  await page.keyboard.press("Shift+F10");
  await page.click("#details");
}
try {
  await page.goto(process.env.BO_CONCEPT_URL);
  await page.waitForFunction(() => window.graphDebug?.graph && !window.graphDebug.layoutBusy);
  if (await page.locator("#recording-timeline").isVisible()) await page.click("#replay-timeline");
  const initialEvents = await page.evaluate(() => graphDebug.view.events.length);
  for (const mode of ["2D", "3D"]) {
    if ((await page.locator("#layered-toggle").innerText()) !== mode)
      await page.click("#layered-toggle");
    await page.selectOption("#analysis-view", "states");
    await page.click("#expand");
    await page.click("#arrange");
    await page.waitForFunction(() => !graphDebug.layoutBusy);
    await page.click("#fit");
    const state = await page.evaluate(
      () =>
        [...graphDebug.graph.all.values()].find(
          (node) => node.concept_kind === "state" && node.value === "active",
        )?.id,
    );
    assert.ok(state);
    await select(state);
    await page.waitForSelector(".node-facts");
    const text = await page.locator("#detail-rows").innerText();
    assert.ok(text.includes("revoke"), text);
    assert.ok(text.includes("inactive"), text);
    await page.screenshot({ path: path.join(output, `state-detail-${mode}.png`) });
    checks.push({ mode, state, details: text });
    await page.click("#close-detail");
  }
  await page.selectOption("#analysis-view", "business");
  await page.click("#expand");
  await page.click("#arrange");
  await page.waitForFunction(() => !graphDebug.layoutBusy);
  await page.click("#fit");
  const business = await page.evaluate(
    () => [...graphDebug.graph.all.values()].find((n) => n.id === "share")?.id,
  );
  assert.ok(business);
  await select(business);
  const businessFacts = await page.locator(".node-facts").innerText();
  assert.equal(
    businessFacts.includes("Read the selected recipient's grant before an authorization decision."),
    false,
  );
  assert.equal(businessFacts.includes("Open one application database connection"), false);
  checks.push({ business_neighbors_exclude_internal_calls: true });
  await page.click("#explain-node");
  await page.waitForFunction(
    () =>
      ["complete", "error"].includes(document.getElementById("node-explanation").dataset.status),
    null,
    { timeout: 150000 },
  );
  const response = await page.locator("#node-explanation").evaluate((element) => ({
    status: element.dataset.status,
    provider: element.dataset.provider,
    text: element.textContent,
  }));
  checks.push({ ai: response });
  // Presence in the DOM is insufficient: the completed answer must actually be
  // readable without discovering a hidden scroll position in the detail panel.
  await page.waitForFunction(() => {
    const answer = document.getElementById("node-explanation").getBoundingClientRect();
    const panel = document.getElementById("node-details").getBoundingClientRect();
    return answer.height > 0 && answer.top >= panel.top && answer.top + 35 <= panel.bottom;
  });
  checks.push({ answer_visible_in_panel: true });
  await page.screenshot({ path: path.join(output, "in-panel-explanation.png") });
  if (process.env.BO_REQUIRE_LIVE_AI === "1")
    assert.equal(response.status, "complete", response.text);
  else assert.ok(["complete", "error"].includes(response.status));
  const finalEvents = await page.evaluate(() => graphDebug.view.events.length);
  assert.equal(finalEvents, initialEvents, "Inspection and explanation create no business events");
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(output, "node-details-browser.json"),
    JSON.stringify({ valid: true, checks, errors, initialEvents, finalEvents }, null, 2) + "\n",
  );
  console.log(
    JSON.stringify({
      valid: true,
      renderers: 2,
      ai: response.status,
      observerEvents: finalEvents - initialEvents,
    }),
  );
} catch (error) {
  await page.screenshot({ path: path.join(output, "node-details-failure.png") }).catch(() => {});
  await writeFile(
    path.join(output, "node-details-browser.json"),
    JSON.stringify({ valid: false, error: error.stack, checks, errors }, null, 2),
  );
  throw error;
} finally {
  await browser.close();
}
