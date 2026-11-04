/** Isolate reload ordering with real controls and a deliberately held preference POST. */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { serveRecording } from "../../../../../tools/recording_browser_fixture.mjs";

const { chromium } = createRequire(import.meta.url)("playwright");
const out = path.dirname(fileURLToPath(import.meta.url));
await mkdir(out, { recursive: true });
const source = path.resolve("docs/review/spatial-workspace/replay-fixture.json");
const originalHash = createHash("sha256")
  .update(await readFile(source))
  .digest("hex");
const fixture = await serveRecording(source);
const checks = {};
const result = { checks, preferencePosts: [], errors: [] };
let browser;
let release;
try {
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (error) => result.errors.push(String(error.stack)));
  await page.goto(fixture.url + "?lang=en");
  await page.waitForFunction(() => window.graphDebug?.graph);
  await page.selectOption("#record-list", fixture.recording.id);
  await page.waitForSelector("#recording-timeline", { state: "visible" });
  const savedTimeline = (expected, afterRevision = -1) =>
    page
      .waitForResponse(async (response) => {
        if (
          new URL(response.url()).pathname !== "/api/preferences" ||
          response.request().method() !== "POST" ||
          response.status() !== 200
        )
          return false;
        const saved = await response.json();
        const raw = Object.entries(saved.entries).find(([key]) => key.endsWith(":analysis"))?.[1];
        const timeline = raw && JSON.parse(raw).timeline;
        return (
          saved.revision > afterRevision &&
          timeline &&
          Object.entries(expected).every(([key, value]) => timeline[key] === value)
        );
      })
      .then(async (response) => {
        const saved = await response.json();
        const raw = Object.entries(saved.entries).find(([key]) => key.endsWith(":analysis"))[1];
        return { revision: saved.revision, timeline: JSON.parse(raw).timeline };
      });
  const initialSave = savedTimeline({ scope: "all", visible: true });
  await page.selectOption(".trace-scope", "all");
  const initial = await initialSave;
  const closedSave = savedTimeline({ scope: "all", visible: false }, initial.revision);
  await page.click(".trace-close");
  const closed = await closedSave;
  result.closedAcknowledgment = closed;

  let hold = true;
  let entered;
  const requested = new Promise((resolve) => {
    entered = resolve;
  });
  const held = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/api/preferences", async (route) => {
    const request = route.request();
    if (request.method() === "POST") {
      const body = request.postDataJSON();
      const raw = Object.entries(body.entries).find(([key]) => key.endsWith(":analysis"))?.[1];
      const timeline = raw && JSON.parse(raw).timeline;
      result.preferencePosts.push({ timeline, revision: body.revision });
      if (hold && timeline?.visible === true) {
        entered();
        await held;
      }
    }
    await route.continue().catch(() => {});
  });
  await page.click("#replay-timeline");
  assert.equal(await page.locator("#recording-timeline").isVisible(), true);
  await requested;
  const stale = await page.evaluate(async () => {
    const saved = await (await fetch("/api/preferences")).json();
    const raw = Object.entries(saved.entries).find(([key]) => key.endsWith(":analysis"))?.[1];
    const timeline = raw && JSON.parse(raw).timeline;
    return {
      revision: saved.revision,
      timeline,
      originalScopeOnlyPredicate: timeline?.scope === "all",
    };
  });
  result.beforeReload = stale;
  checks.originalPredicatePassesWithoutReopenAcknowledgment =
    stale.originalScopeOnlyPredicate && stale.timeline.visible === false;
  assert.equal(checks.originalPredicatePassesWithoutReopenAcknowledgment, true);
  await page.reload();
  await page.waitForFunction(() => window.graphDebug?.graph);
  await page.selectOption("#record-list", fixture.recording.id);
  checks.reloadRestoresLastAcknowledgedHiddenState = !(await page
    .locator("#recording-timeline")
    .isVisible());
  assert.equal(checks.reloadRestoresLastAcknowledgedHiddenState, true);
  await page.screenshot({ path: path.join(out, "controlled-old-barrier-failure.png") });

  hold = false;
  release();
  await page.unroute("**/api/preferences");
  const reopenedSave = savedTimeline(
    { scope: "all", visible: true, height: closed.timeline.height },
    closed.revision,
  );
  await page.click("#replay-timeline");
  assert.equal(await page.locator("#recording-timeline").isVisible(), true);
  const reopened = await reopenedSave;
  checks.reopenAcknowledgmentAdvancesRevision = reopened.revision > closed.revision;
  assert.equal(checks.reopenAcknowledgmentAdvancesRevision, true);
  result.reopenedAcknowledgment = reopened;
  await page.reload();
  await page.waitForFunction(() => window.graphDebug?.graph);
  await page.selectOption("#record-list", fixture.recording.id);
  await page.waitForSelector("#recording-timeline", { state: "visible" });
  assert.equal(await page.locator(".trace-scope").inputValue(), "all");
  assert.equal(
    Number(await page.locator(".trace-resize").getAttribute("aria-valuenow")),
    closed.timeline.height,
  );
  checks.acknowledgedReopenSurvivesReload = true;
  await page.screenshot({ path: path.join(out, "controlled-new-barrier-pass.png") });
  checks.noBusinessWrites = fixture.writes.length === 0;
  checks.recordingBytesUnchanged =
    originalHash ===
    createHash("sha256")
      .update(await readFile(source))
      .digest("hex");
  assert.ok(Object.values(checks).every(Boolean));
  assert.deepEqual(result.errors, []);
  result.valid = true;
} catch (error) {
  result.valid = false;
  result.error = String(error.stack);
  throw error;
} finally {
  release?.();
  await browser?.close();
  await fixture.close();
  await writeFile(
    path.join(out, "controlled-acknowledgment-proof.json"),
    JSON.stringify(result, null, 2),
  );
  console.log(JSON.stringify(result, null, 2));
}
