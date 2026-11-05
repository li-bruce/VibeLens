/** Exercise the bilingual product introduction and its separate sample walkthrough. */
import assert from "node:assert/strict";
import { startSite } from "./site_browser_fixture.mjs";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(process.env.BO_SITE_EVIDENCE || ".validation/site-browser");
const server = await startSite();
const base = server.url;
let browser;
const errors = [],
  checks = [];
await mkdir(output, { recursive: true });
try {
  browser = await chromium.launch({
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
    ...(process.env.BO_BROWSER_EXECUTABLE
      ? { executablePath: process.env.BO_BROWSER_EXECUTABLE }
      : {}),
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (error) => errors.push(error.message));
  for (const language of ["en", "zh-CN"]) {
    await page.goto(base + "/?lang=" + language);
    await page.waitForFunction(
      () =>
        document.querySelector("#hero-screenshot").complete &&
        document.querySelector("#hero-screenshot").naturalWidth > 1000,
    );
    assert.equal(await page.locator("html").getAttribute("lang"), language);
    assert.match(await page.locator(".brand").innerText(), /^VibeLens/);
    await page.waitForFunction(() =>
      [...document.querySelectorAll(".brand-mark")].every(
        (image) => image.complete && image.naturalWidth > 0,
      ),
    );
    const brand = await page.locator(".brand .brand-mark").getAttribute("src");
    assert.equal(brand, await page.locator('link[rel="icon"]').getAttribute("href"));
    assert.equal(
      await page
        .locator('header a[href="https://github.com/li-bruce/VibeLens"]')
        .getAttribute("href"),
      "https://github.com/li-bruce/VibeLens",
    );
    assert.match(await page.locator("#install-prompt").textContent(), /^\$vibelens\n/);
    for (const title of await page.locator("h1,h2,h3").allTextContents())
      assert.ok(!/[.。]$/.test(title.trim()), title);
    assert.equal(await page.locator("[data-control-preset]").count(), 0);
    assert.equal(await page.locator(".home-steps > li").count(), 3);
    assert.equal(await page.locator("[data-layer-tabs] [role=tab]").count(), 7);
    await page.screenshot({ path: path.join(output, language + "-hero.png") });
    await page.locator('[data-capture="layers"]').focus();
    await page.keyboard.press("Enter");
    assert.equal(
      await page.locator('[data-capture="layers"]').getAttribute("aria-pressed"),
      "true",
    );
    await page.waitForFunction(
      () =>
        document.querySelector("#hero-screenshot").src.includes("layers-") &&
        document.querySelector("#hero-screenshot").complete,
    );
    const previousImage = await page.locator("#hero-screenshot").getAttribute("src");
    await page.click("#language");
    await page.waitForFunction(
      (previous) => document.querySelector("#hero-screenshot").getAttribute("src") !== previous,
      previousImage,
    );
    assert.ok(!(await page.locator("#hero-screenshot").getAttribute("alt")).startsWith("home."));
    await page.click("#language");
    await page.locator("#workflow").scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    await page
      .locator("#workflow")
      .screenshot({ path: path.join(output, language + "-workflow.png") });
    await page.locator("#explore").scrollIntoViewIfNeeded();
    await page.waitForFunction(
      () => document.querySelector("#layer-explorer").dataset.webgl === "ready",
    );
    await page.waitForFunction(() =>
      [...document.querySelectorAll("[data-product-image]")].every(
        (image) => image.complete && image.naturalWidth > 1000,
      ),
    );
    await page.locator("#explore").screenshot({ path: path.join(output, language + "-depth.png") });
    await page.locator("#conversation-controls").scrollIntoViewIfNeeded();
    const link = await page.locator("#conversation-controls a").getAttribute("href");
    assert.ok(link.includes("demo.html"));
    await page
      .locator("#conversation-controls")
      .screenshot({ path: path.join(output, language + "-single-example.png") });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(base + "/?lang=" + language);
    await page.waitForFunction(() => document.querySelector("#hero-screenshot").complete);
    assert.ok(
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
      "Homepage overflows on mobile",
    );
    await page.locator("#workflow").scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    await page
      .locator("#workflow")
      .screenshot({ path: path.join(output, language + "-mobile-workflow.png") });
    await page.screenshot({ path: path.join(output, language + "-mobile.png"), fullPage: true });
    checks.push(
      language +
        ": problem/model/observation/iteration narrative, native screenshots, localized 2D/3D image switching, seven interactive display layers, demo link and mobile layout",
    );
    await page.setViewportSize({ width: 1440, height: 1000 });
  }
  await page.goto(base + "/practice.html?lang=zh-CN");
  await page.waitForURL(/demo\.html\?lang=zh-CN/);
  await page.waitForFunction(() => document.body.dataset.sceneReady === "foundation");
  assert.match(await page.locator(".brand").innerText(), /^VibeLens/);
  assert.equal(
    await page.locator(".case-footer a").first().getAttribute("href"),
    "https://github.com/li-bruce/VibeLens/tree/main/examples/file-sharing",
  );
  await page.locator("#run").scrollIntoViewIfNeeded();
  await page.waitForFunction(() => document.body.dataset.sceneReady === "run");
  const replay = page.frames().find((frame) => frame.url().includes("viewer/index.html?case="));
  await replay.waitForFunction(() => graphDebug.view.replay?.event?.id);
  if (/Pause|暂停/.test(await replay.locator("#replay-play").getAttribute("aria-label")))
    await page.click("#case-play");
  const recorded = await replay.evaluate(
    async () => (await (await fetch("/api/view")).json()).events,
  );
  await page.locator("#case-position").evaluate((node) => {
    node.value = "60";
    node.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await replay.waitForFunction(() => graphDebug.view.replay.index > 0);
  const later = await replay.evaluate(() => graphDebug.view.replay.index);
  await page.locator("#case-position").evaluate((node) => {
    node.value = "10";
    node.dispatchEvent(new Event("input", { bubbles: true }));
  });
  await replay.waitForFunction((later) => graphDebug.view.replay.index < later, later);
  assert.deepEqual(
    await replay.evaluate(async () => (await (await fetch("/api/view")).json()).events),
    recorded,
    "Replay cannot execute new business operations",
  );
  await page.screenshot({ path: path.join(output, "demo-replay.png"), fullPage: true });
  checks.push(
    "Legacy URL reaches the real case; recorded replay seeks backward without mutating business facts",
  );
  const quiet = await browser.newPage({ reducedMotion: "reduce" });
  await quiet.goto(base + "/?lang=en#explore");
  await quiet.waitForFunction(
    () => document.querySelector("#layer-explorer").dataset.webgl === "ready",
  );
  assert.equal(await quiet.locator("iframe").count(), 0);
  assert.ok(await quiet.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches));
  await quiet.close();
  checks.push("Reduced-motion homepage has no automatic replay");
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify({ passed: true, url: base, checks, errors }, null, 2),
  );
  console.log(
    "PASS: bilingual homepage, native captures, seven display layers, mobile layout and recorded walkthrough.",
  );
} catch (error) {
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify(
      { passed: false, url: base, checks, errors, error: String(error.stack) },
      null,
      2,
    ),
  );
  throw error;
} finally {
  await browser?.close();
  server.close();
}
