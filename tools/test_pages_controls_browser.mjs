/** Test the published usage examples through their real embedded VibeLens viewer. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(
  process.env.BO_PAGES_CONTROL_EVIDENCE || ".validation/pages-controls/browser",
);
await mkdir(output, { recursive: true });
const base = (process.env.BO_SITE_URL || "http://127.0.0.1:8895").replace(/\/$/, "");
const python = path.resolve(
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const server = process.env.BO_SITE_URL
  ? null
  : spawn(
      python,
      ["-B", "-m", "http.server", "8895", "--bind", "127.0.0.1", "--directory", "docs/site"],
      { windowsHide: true, stdio: "ignore" },
    );
const artifact = JSON.parse(await readFile("docs/site/case-data/v1.json", "utf8"));
const plans = JSON.parse(await readFile("docs/site/control-plans.json", "utf8"));
let browser,
  page,
  passed = false;
const errors = [],
  receipts = [];
try {
  for (let i = 0; i < 50; i++) {
    try {
      if ((await fetch(base)).ok) break;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  browser = await chromium.launch({
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
    ...(process.env.BO_BROWSER_EXECUTABLE
      ? { executablePath: process.env.BO_BROWSER_EXECUTABLE }
      : {}),
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    permissions: ["clipboard-read", "clipboard-write"],
  });
  page = await context.newPage();
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("response", (response) => {
    if (response.status() >= 400) errors.push(response.status() + " " + response.url());
  });
  for (const language of ["en", "zh-CN"]) {
    await page.goto(base + "/index.html?lang=" + language + "#conversation-controls");
    await page.waitForFunction(
      () => document.querySelector("#conversation-controls").dataset.applied === "business",
    );
    let child = page.frames().find((frame) => frame.url().includes("controls=1"));
    assert.ok(child);
    await child.waitForFunction(
      () => graphDebug.graph?.boxes.length === 3 && !graphDebug.layoutBusy,
    );
    assert.deepEqual(
      await child.evaluate(() => graphDebug.graph.boxes.map((box) => box.id).sort()),
      ["publish", "review", "upload"],
    );
    assert.equal(await child.evaluate(() => graphDebug.graph.edges.length), 2);
    await page.waitForTimeout(500);
    assert.equal(
      await page
        .locator("#control-command")
        .textContent()
        .then((text) => text.startsWith("/vibelens")),
      true,
    );
    await page.click("#copy-control");
    assert.equal(
      (await page.evaluate(() => navigator.clipboard.readText())).replaceAll("\r\n", "\n"),
      await page.locator("#control-command").textContent(),
    );
    await page
      .locator("#conversation-controls")
      .screenshot({ path: path.join(output, language + "-business.png") });
    assert.equal(
      await page.locator("[data-control-preset]").count(),
      0,
      "Homepage keeps one example",
    );
    await page.locator("#install").scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
    assert.match(await page.locator("#install-prompt").textContent(), /^\$vibelens\n/);
    await page.click("#copy-prompt");
    assert.equal(
      (await page.evaluate(() => navigator.clipboard.readText())).replaceAll("\r\n", "\n"),
      await page.locator("#install-prompt").textContent(),
    );
    await page
      .locator("#install")
      .screenshot({ path: path.join(output, language + "-activation.png") });
    await page.goto(base + "/demo.html?lang=" + language + "#conversation-controls");
    await page.waitForFunction(
      () => document.querySelector("#conversation-controls").dataset.applied === "business",
    );
    child = page.frames().find((frame) => frame.url().includes("controls=1"));
    assert.equal(await page.locator("[data-control-preset]").count(), 3);
    await page.click('[data-control-preset="details"]');
    await page.waitForFunction(
      () => document.querySelector("#conversation-controls").dataset.applied === "details",
    );
    assert.ok(
      await child.evaluate(() =>
        [
          "review-policy",
          "field:review-policy:in:reviewed_version",
          "field:review-policy:in:current_version",
        ].every((id) => graphDebug.graph.boxes.some((box) => box.id === id)),
      ),
    );
    await page.click('[data-control-mode="3d"]');
    await child.waitForFunction(() => graphDebug.spatial?.perspective && !graphDebug.layoutBusy);
    await page.waitForTimeout(500);
    await page
      .locator("#conversation-controls")
      .screenshot({ path: path.join(output, language + "-details-3d.png") });
    await page.click('[data-control-mode="2d"]');
    await child.waitForFunction(() => !graphDebug.layers.enabled && !graphDebug.layoutBusy);
    await page.click('[data-control-preset="replay"]');
    await page.waitForFunction(
      () => document.querySelector("#conversation-controls").dataset.applied === "replay",
    );
    await child.waitForFunction(() =>
      /Pause|暂停/.test(document.querySelector("#replay-play").getAttribute("aria-label")),
    );
    const selected = plans.locales[language].replay.recording;
    assert.ok(selected.selected_events < selected.total_events);
    const before = await child.locator("#replay-range").inputValue();
    await page.waitForTimeout(1100);
    const after = await child.locator("#replay-range").inputValue();
    assert.notEqual(after, before, "Filtered replay advances through actual recorded events");
    assert.deepEqual(
      await child.evaluate(
        async (id) => (await (await fetch("/api/recordings/" + id)).json()).events,
        artifact.recording.id,
      ),
      artifact.recording.events,
    );
    await page
      .locator("#conversation-controls")
      .screenshot({ path: path.join(output, language + "-replay.png") });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator("#conversation-controls").scrollIntoViewIfNeeded();
    await page.click('[data-control-preset="business"]');
    await page.waitForFunction(
      () => document.querySelector("#conversation-controls").dataset.applied === "business",
    );
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 2));
    await page
      .locator("#conversation-controls")
      .screenshot({ path: path.join(output, language + "-mobile.png") });
    await page.click("#language");
    await page.waitForFunction((previous) => document.documentElement.lang !== previous, language);
    await page.waitForFunction(
      () => document.querySelector("#conversation-controls").dataset.applied === "business",
    );
    const localized = page.frames().find((frame) => frame.url().includes("controls=1"));
    assert.equal(
      await localized.evaluate(() => document.documentElement.lang),
      language === "en" ? "zh-CN" : "en",
    );
    receipts.push({
      language,
      original_relations: 2,
      business_nodes: 3,
      parameters_visible: true,
      native_3d: true,
      replay_events: selected.selected_events,
      total_events: selected.total_events,
      raw_events_unchanged: true,
      clipboard: true,
      mobile: true,
      language_switch: true,
    });
    await page.setViewportSize({ width: 1440, height: 1000 });
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(base + "/demo.html?lang=en#conversation-controls");
  await page.waitForFunction(
    () => document.querySelector("#conversation-controls").dataset.applied === "business",
  );
  await page.click('[data-control-preset="replay"]');
  await page.waitForFunction(
    () => document.querySelector("#conversation-controls").dataset.applied === "replay",
  );
  const child = page.frames().find((frame) => frame.url().includes("controls=1"));
  assert.ok(!/Pause|暂停/.test(await child.locator("#replay-play").getAttribute("aria-label")));
  assert.deepEqual(errors, []);
  passed = true;
} catch (error) {
  await page?.screenshot({ path: path.join(output, "failure.png") });
  await writeFile(
    path.join(output, "failure.json"),
    JSON.stringify({ error: String(error.stack), errors }, null, 2),
  );
  throw error;
} finally {
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify({ passed, receipts, errors }, null, 2),
  );
  await browser?.close();
  server?.kill();
}
console.log(
  "PASS: bilingual Pages activation, real controlled views, 2D/3D, filtered replay, clipboard, mobile and reduced motion",
);
