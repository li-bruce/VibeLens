/** Verify compact changes through a real saved execution and native graph controls. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import { serveRecording } from "./recording_browser_fixture.mjs";

const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(process.env.BO_CHANGES_EVIDENCE || ".validation/compact-changes");
await mkdir(output, { recursive: true });
const source = "docs/review/recording-timeline/real-project-completion/v2-recording.json";
const fixture = await serveRecording(source);
const errors = [],
  checks = [];
let browser, page;
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
    args: ["--enable-unsafe-swiftshader"],
  });
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (error) => errors.push(String(error)));
  for (const language of ["en", "zh-CN"]) {
    await page.goto(fixture.url + "?lang=" + language);
    await page.waitForFunction(() => window.graphDebug?.graph && !graphDebug.layoutBusy);
    await page.selectOption("#record-list", fixture.recording.id);
    await page.selectOption("#replay-grain", "events");
    const candidates = await page
      .locator("#replay-events option")
      .evaluateAll((options) =>
        options.map((option) => ({ value: option.value, event: option.title })),
      );
    let selected;
    for (const candidate of candidates) {
      await page.selectOption("#replay-events", candidate.value);
      if ((await page.locator("#change-rows .change-row").count()) > 2) {
        selected = candidate;
        break;
      }
    }
    assert.ok(selected, "The real recording must contain a step with more than two changes");
    const rows = await page.locator("#change-rows .change-row").evaluateAll((elements) =>
      elements.map((element) => ({
        owner: element.dataset.owner,
        event: element.dataset.eventId,
        text: element.textContent,
      })),
    );
    assert.ok(rows.every((row) => row.event && row.owner));
    for (const mode of ["2D", "3D"]) {
      if ((await page.locator("#layered-toggle").innerText()) !== mode)
        await page.click("#layered-toggle");
      await page.waitForFunction(() => !graphDebug.layoutBusy);
      assert.equal(await page.locator("#change-rows .change-row:visible").count(), 2);
      const panel = await page.locator("#step-changes").boundingBox();
      assert.ok(panel.width <= 380 && panel.height <= 145);
      await page.click("#change-expand");
      assert.equal(await page.locator("#change-rows .change-row:visible").count(), rows.length);
      assert.deepEqual(
        await page.locator("#change-rows .change-row").evaluateAll((elements) =>
          elements.map((element) => ({
            owner: element.dataset.owner,
            event: element.dataset.eventId,
            text: element.textContent,
          })),
        ),
        rows,
      );
      await page.click("#change-expand");
      const before = await page.locator("#step-changes").boundingBox();
      const geometry = await page.evaluate(() =>
        graphDebug.graph.boxes.map(({ id, x, y }) => ({ id, x, y })),
      );
      const grip = await page.locator(".change-grip").boundingBox();
      await page.mouse.move(grip.x + grip.width / 2, grip.y + grip.height / 2);
      await page.mouse.down();
      await page.mouse.move(grip.x - 70, grip.y - 45, { steps: 8 });
      await page.mouse.up();
      const after = await page.locator("#step-changes").boundingBox();
      assert.ok(after.x < before.x - 25 && after.y < before.y - 20);
      assert.deepEqual(
        await page.evaluate(() => graphDebug.graph.boxes.map(({ id, x, y }) => ({ id, x, y }))),
        geometry,
      );
      await page.click("#change-collapse");
      assert.equal(await page.locator("#change-content").isVisible(), false);
      await page.selectOption("#replay-events", candidates.at(-1).value);
      assert.equal(
        await page.locator("#change-content").isVisible(),
        false,
        "New events preserve minimization",
      );
      await page.selectOption("#replay-events", selected.value);
      await page.click("#change-collapse");
      const target = page.locator("#change-rows .change-row:visible button").first();
      const owner = await target.evaluate((button) => button.parentElement.dataset.owner);
      await target.click();
      assert.equal(
        await page.locator(`#semantic [data-node-id="${owner}"]`).getAttribute("aria-pressed"),
        "true",
      );
      await page.screenshot({ path: path.join(output, `${language}-${mode}.png`) });
      checks.push({
        language,
        mode,
        event: selected.event,
        total: rows.length,
        preview: 2,
        drag: true,
        disclosure: true,
        locate: owner,
      });
    }
    await page.setViewportSize({ width: 720, height: 720 });
    // ResizeObserver constrains the dragged panel before the next paint; the
    // viewport protocol acknowledgement can arrive before that browser frame.
    await page.waitForFunction(
      () => {
        const bounds = document.getElementById("step-changes").getBoundingClientRect();
        return bounds.left >= 0 && bounds.right <= innerWidth;
      },
      null,
      { timeout: 1000 },
    );
    const compact = await page.locator("#step-changes").boundingBox();
    assert.ok(compact.x >= 0 && compact.x + compact.width <= 720);
    await page.setViewportSize({ width: 1440, height: 1000 });
  }
  assert.deepEqual(errors, []);
  assert.deepEqual(fixture.writes, [], "Observation controls make no application writes");
  assert.deepEqual(await readFile(source), fixture.bytes, "Recorded facts remain unchanged");
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify(
      {
        passed: true,
        fixture_sha256: createHash("sha256").update(fixture.bytes).digest("hex"),
        checks,
        errors,
      },
      null,
      2,
    ),
  );
  console.log(JSON.stringify({ passed: true, checks }));
} catch (error) {
  await page?.screenshot({ path: path.join(output, "failure.png") }).catch(() => {});
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify({ passed: false, checks, errors, error: String(error.stack) }, null, 2),
  );
  throw error;
} finally {
  await browser?.close();
  await fixture.close();
}
