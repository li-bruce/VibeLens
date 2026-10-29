/** Exercise the bilingual product introduction and its separate sample walkthrough. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = createRequire(import.meta.url)("playwright");
const root = fileURLToPath(new URL("../", import.meta.url));
const plans = JSON.parse(await readFile(path.join(root, "docs/site/control-plans.json"), "utf8"));
const output = path.resolve(process.env.BO_SITE_EVIDENCE || ".validation/site-browser");
const python =
  process.env.BO_PYTHON ||
  path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const base = (
  process.env.BO_SITE_URL || "http://127.0.0.1:" + (process.env.BO_SITE_PORT || "8873")
).replace(/\/$/, "");
// A supplied URL tests the deployed introduction; the default starts a local copy.
const server = process.env.BO_SITE_URL
  ? null
  : spawn(
      python,
      [
        "-B",
        "-m",
        "http.server",
        new URL(base).port,
        "--bind",
        "127.0.0.1",
        "--directory",
        "docs/site",
      ],
      { cwd: root, windowsHide: true, stdio: "ignore" },
    );
let browser;
const errors = [],
  checks = [];
await mkdir(output, { recursive: true });
try {
  for (let attempt = 0; attempt < 80; attempt++) {
    try {
      if ((await fetch(base)).ok) break;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
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
      await page.locator("a.github").getAttribute("href"),
      "https://github.com/li-bruce/VibeLens",
    );
    assert.match(await page.locator("#install-prompt").textContent(), /^\$vibelens\n/);
    for (const title of await page.locator("h1,h2,h3").allTextContents())
      assert.ok(!/[.。]$/.test(title.trim()), title);
    assert.equal(await page.locator("[data-control-preset]").count(), 0);
    assert.equal(await page.locator(".development-loop > li").count(), 3);
    assert.equal(await page.locator(".depth-key > div").count(), 3);
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
    await page.waitForFunction(() =>
      [...document.querySelectorAll("[data-product-image]")].every(
        (image) => image.complete && image.naturalWidth > 1000,
      ),
    );
    await page.locator("#explore").screenshot({ path: path.join(output, language + "-depth.png") });
    await page.locator("#conversation-controls").scrollIntoViewIfNeeded();
    await page.waitForFunction(
      () => document.querySelector("#conversation-controls").dataset.applied === "business",
    );
    const frame = page.frames().find((frame) => frame.url().includes("controls=1"));
    assert.deepEqual(
      await frame.evaluate(() => graphDebug.graph.boxes.map((box) => box.id).sort()),
      plans.locales[language].business.node_ids.slice().sort(),
    );
    assert.ok(await frame.evaluate(() => graphDebug.graph.edges.length > 0));
    const link = await page
      .locator(
        'a[href*="demo.html#conversation-controls"],a[href*="demo.html?lang="][href$="#conversation-controls"]',
      )
      .getAttribute("href");
    assert.ok(link.includes("demo.html") && link.endsWith("#conversation-controls"));
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
        ": problem/approach/iteration narrative, native screenshots, localized 2D/3D image switching, one focused graph with real relations, demo link and mobile layout",
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
  await quiet.goto(base + "/?lang=en#conversation-controls");
  await quiet.waitForFunction(
    () => document.querySelector("#conversation-controls").dataset.applied === "business",
  );
  const quietFrame = quiet.frames().find((frame) => frame.url().includes("controls=1"));
  assert.ok(
    !/Pause|暂停/.test(await quietFrame.locator("#replay-play").getAttribute("aria-label")),
  );
  await quiet.close();
  checks.push("Reduced-motion homepage has no automatic replay");
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify({ passed: true, url: base, checks, errors }, null, 2),
  );
  console.log(
    "PASS: bilingual homepage narrative, real captures, single-example controls, mobile layout and independent recording walkthrough.",
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
  if (server?.exitCode === null) server.kill();
}
