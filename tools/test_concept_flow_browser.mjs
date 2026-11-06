/** Exercise compound directional layout through real viewer controls and storage.
 * Input is an immutable recording; the fixture only accepts preference writes.
 */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { serveRecording } from "./recording_browser_fixture.mjs";

const { chromium } = createRequire(import.meta.url)("playwright");
const recording = process.argv[2];
if (!recording)
  throw Error("Pass a saved recording containing expanded conceptual regions");
const output = path.resolve(
  process.argv[3] || ".validation/concept-flow-browser",
);
await mkdir(output, { recursive: true });
let fixture = await serveRecording(recording);
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.BO_BROWSER_EXECUTABLE,
  args: ["--enable-unsafe-swiftshader"],
});
const checks = [],
  errors = [];
let page;
let failureGraph;
const wait = () =>
  page.waitForFunction(() => graphDebug.graph && !graphDebug.layoutBusy);
async function select(id) {
  await page.locator("#semantic [data-node-id]").evaluateAll((elements, id) => {
    const element = elements.find((item) => item.dataset.nodeId === id);
    if (!element) throw Error("Not visible: " + id);
    element.click();
  }, id);
  await page.locator("#viewport").focus();
}
const positions = (mode) =>
  page.evaluate(
    (mode) =>
      mode === "3D"
        ? graphDebug.spatialPositions
        : Object.fromEntries(
            graphDebug.graph.boxes.map((box) => [
              box.id,
              { x: box.x, y: box.y },
            ]),
          ),
    mode,
  );
try {
  for (const mode of ["2D", "3D"]) {
    // Each renderer starts without the previous mode's persisted pin toggle.
    if (mode === "3D") {
      assert.deepEqual(fixture.writes, []);
      await fixture.close();
      fixture = await serveRecording(recording);
    }
    page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
    page.on("pageerror", (error) => errors.push(error.message));
    await page.goto(fixture.url + "?lang=en");
    await wait();
    await page.selectOption("#analysis-view", "rules");
    if ((await page.locator("#layered-toggle").innerText()) !== mode) {
      await page.click("#layered-toggle");
      await wait();
    }
    await page.click("#collapse");
    await wait();
    const id = await page.evaluate(
      () =>
        graphDebug.graph.boxes.find(
          (box) => graphDebug.graph.children.get(box.id)?.length > 2,
        )?.id,
    );
    assert.ok(id, "recording needs a compound rule network");
    await select(id);
    await page.keyboard.press("Enter");
    await wait();
    const expanded = await positions(mode);
    assert.ok(Object.keys(expanded).length > 3);
    const direction = await page.evaluate(
      async ({ mode, id }) => {
        const { conceptOrderEdges } = await import("/concept-flow-layout.js");
        const { ancestorsToReveal } = await import("/layout.js");
        // Expansion retains outside coordinates; only the fresh subtree is reflowed.
        const internal = (node) =>
          ancestorsToReveal(graphDebug.graph.all, node).includes(id);
        const edges = conceptOrderEdges(graphDebug.graph).filter(
          (edge) => internal(edge.from) && internal(edge.to),
        );
        const points =
          mode === "3D"
            ? graphDebug.spatialPositions
            : Object.fromEntries(
                graphDebug.graph.boxes.map((box) => [box.id, box]),
              );
        return {
          edges: edges.length,
          backwards: edges
            .filter((edge) => points[edge.from].x >= points[edge.to].x)
            .map((edge) => edge.id),
        };
      },
      { mode, id },
    );
    assert.ok(direction.edges > 0);
    assert.equal(direction.backwards.length, 0, JSON.stringify(direction));
    const child = await page.evaluate(
      (id) => graphDebug.graph.children.get(id)[0],
      id,
    );
    await select(child);
    await page.keyboard.press("ArrowRight");
    await page.keyboard.press("p");
    const moved = (await positions(mode))[child];
    assert.ok(Math.abs(moved.x - expanded[child].x - 20) < 0.01);
    await page.click("#arrange");
    await wait();
    const pinned = (await positions(mode))[child];
    assert.equal(
      pinned.x,
      moved.x,
      "Arrange must preserve the pinned coordinate",
    );
    assert.equal(
      mode === "3D" ? pinned.z : pinned.y,
      mode === "3D" ? moved.z : moved.y,
    );
    await select(id);
    await page.keyboard.press("Enter");
    await wait();
    await select(id);
    await page.keyboard.press("Enter");
    await wait();
    assert.equal(
      (await positions(mode))[child].x,
      moved.x,
      "Reopen must preserve the pin",
    );
    await page.click("#fit");
    await page.screenshot({ path: path.join(output, mode + "-flow.png") });
    // Wait for the preference API, then verify persisted coordinates in a reload.
    await page.waitForFunction(() =>
      document.body.textContent.includes("View saved"),
    );
    await page.reload();
    await wait();
    assert.equal(
      (await positions(mode))[child].x,
      moved.x,
      "Reload must preserve the pin",
    );
    checks.push({
      mode,
      root: id,
      child,
      direction,
      expanded: Object.keys(expanded).length,
      pin: moved,
    });
    await page.close();
  }
  assert.deepEqual(fixture.writes, []);
  assert.deepEqual(errors, []);
  console.log(JSON.stringify({ passed: true, checks: checks.length }));
} catch (error) {
  errors.push(error.stack);
  failureGraph = await page?.evaluate(() => ({
    nodes: graphDebug.graph.boxes.map((box) => ({
      id: box.id,
      parent: box.node.parent,
      layer: box.node.layer,
      kind: box.node.kind,
      x: box.x,
      y: box.y,
    })),
    edges: graphDebug.graph.edges,
  }));
  await page?.screenshot({ path: path.join(output, "failure.png") });
  throw error;
} finally {
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify(
      {
        passed: !errors.length,
        checks,
        errors,
        failureGraph,
        writes: fixture.writes,
      },
      null,
      2,
    ) + "\n",
  );
  await browser.close();
  await fixture.close();
}
