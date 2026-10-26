/** Exercise the bilingual product introduction and its separate sample walkthrough. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const { chromium } = createRequire(import.meta.url)("playwright");
const root = fileURLToPath(new URL("../", import.meta.url));
const output = path.resolve(process.env.BO_SITE_EVIDENCE || ".validation/site-browser");
const python = process.env.BO_PYTHON || path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const base = (process.env.BO_SITE_URL || "http://127.0.0.1:" + (process.env.BO_SITE_PORT || "8873")).replace(/\/$/, "");
// A supplied URL tests the deployed introduction; the default starts a local copy.
const server = process.env.BO_SITE_URL ? null : spawn(python, ["-B", "-m", "http.server", new URL(base).port, "--bind", "127.0.0.1", "--directory", "docs/site"], {cwd: root, windowsHide: true, stdio: "ignore"});
let browser;
const errors = [], checks = [];
await mkdir(output, {recursive: true});
try {
  for (let attempt = 0; attempt < 80; attempt++) {
    try { if ((await fetch(base)).ok) break; } catch {}
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  browser = await chromium.launch({headless: true, ...(process.env.BO_BROWSER_EXECUTABLE ? {executablePath: process.env.BO_BROWSER_EXECUTABLE} : {})});
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
  page.on("pageerror", error => errors.push(error.message));
  for (const language of ["en", "zh-CN"]) {
    await page.goto(base + "/?lang=" + language);
    await page.waitForSelector("#concept-graph svg");
    assert.equal(await page.locator("html").getAttribute("lang"), language);
    assert.match(await page.locator(".brand").innerText(), /^VibeLens/);
    assert.equal(await page.locator("a.github").getAttribute("href"), "https://github.com/li-bruce/VibeLens");
    assert.match(await page.locator("#install-prompt").textContent(), /\$vibelens/);
    for (const title of await page.locator('h1,h2,h3').allTextContents()) assert.ok(!/[.。]$/.test(title.trim()), title);
    assert.equal(await page.locator("[data-view]").count(), 7);
    await page.screenshot({path:path.join(output,language+'-hero.png')});
    await page.keyboard.press('PageDown');
    await page.waitForFunction(()=>scrollY>100);
    await page.locator('#workflow').scrollIntoViewIfNeeded();
    assert.equal(await page.locator('.workflow-steps > li').count(), 4);
    assert.equal(await page.locator('.workflow-schematic circle').count(), 4);
    await page.waitForTimeout(750);
    await page.locator('#workflow').screenshot({path:path.join(output,language+'-foundation.png')});
    assert.ok(await page.locator('.scroll-scene').count() >= 6);
    checks.push(language+': native keyboard scrolling and progressive product sections');
    assert.equal(await page.locator('[data-depth-view]').count(),4);
    for (const level of ['business','state','function','source']) {
      await page.locator('#depth-'+level).scrollIntoViewIfNeeded();
      await page.waitForFunction((level)=>document.querySelector('#explore').dataset.depth===level && document.querySelector('#tab-'+level).getAttribute('aria-selected')==='true', level);
    }
    await page.locator('#explore .depth-visual').screenshot({path:path.join(output,language+'-scroll-depth.png')});
    checks.push(language+': four scroll-driven depths share one sticky graph');
    await page.locator('#viewer-tour').scrollIntoViewIfNeeded();
    await page.click('#tour-next');
    assert.equal(await page.locator('#tour-play').getAttribute('aria-pressed'), 'false');
    for (const step of ['note', 'record', 'replay', 'overview', 'expand']) {
      await page.click('#tour-next');
      assert.equal(await page.locator('#viewer-tour').getAttribute('data-step'), step);
      assert.ok((await page.locator('#tour-caption').textContent()).length > 10);
    }
    await page.locator('#viewer-tour').screenshot({path:path.join(output, language+'-viewer-tour.png')});
    const tourCaption = await page.locator('#tour-caption').textContent();
    await page.click('#language');
    assert.notEqual(await page.locator('#tour-caption').textContent(), tourCaption);
    await page.click('#language');
    checks.push(language + ': controllable five-step viewer animation and translated captions');
    for (const view of ["business", "state", "decision", "function", "data", "source", "mixed"]) {
      await page.click("#tab-" + view);
      assert.equal(await page.locator("#tab-" + view).getAttribute("aria-selected"), "true");
      const description = (await page.locator("#level-body").textContent()).trim();
      assert.ok(description && !description.startsWith("level."), "View description is missing");
      assert.ok(await page.locator("#concept-graph [data-node]").count());
    }
    await page.click("#tab-data");
    await page.locator("#explore").screenshot({path: path.join(output, language + "-data.png")});
    await page.click("#tab-source");
    await page.locator("#explore").screenshot({path: path.join(output, language + "-source.png")});
    const before = await page.locator("#level-body").textContent();
    await page.click("#language");
    assert.notEqual(await page.locator("#level-body").textContent(), before);
    await page.click("#language");
    checks.push(language + ": seven connected views and language switch");
    await page.setViewportSize({width: 390, height: 844});
    await page.goto(base + "/?lang=" + language);
    await page.waitForSelector("#concept-graph svg");
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), "Page overflows on mobile");
    await page.screenshot({path: path.join(output, language + "-mobile.png"), fullPage: true});
    await page.setViewportSize({width: 1440, height: 1000});
  }
  await page.goto(base + "/practice.html?lang=zh-CN");
  assert.match(await page.locator(".brand").innerText(), /^VibeLens/);
  assert.equal(await page.locator("a.github").getAttribute("href"), "https://github.com/li-bruce/VibeLens");
  await page.click("#stage-record");
  await page.click("#start");
  await page.click("#upload");
  await page.click("#approve");
  await page.click("#stop");
  assert.equal(await page.locator("#play").isDisabled(), false);
  await page.locator("#replay").fill("1");
  assert.ok((await page.locator("#change-detail").innerText()).length > 15);
  await page.screenshot({path: path.join(output, "demo-replay.png"), fullPage: true});
  checks.push("Separate sample walkthrough: record, upload, approve, stop and inspect replay");
  const quiet = await browser.newPage({reducedMotion:'reduce'});
  await quiet.goto(base+'/?lang=en');
  await quiet.locator('#viewer-tour').scrollIntoViewIfNeeded();
  await quiet.waitForTimeout(3000);
  assert.equal(await quiet.locator('#viewer-tour').getAttribute('data-step'),'overview');
  assert.equal(await quiet.locator('#tour-play').getAttribute('aria-pressed'),'false');
  await quiet.close();
  checks.push('Reduced-motion tour stays paused until explicitly played');
  assert.deepEqual(errors, []);
  await writeFile(path.join(output, "result.json"), JSON.stringify({passed: true, url: base, checks, errors}, null, 2));
  console.log("PASS: bilingual seven-view introduction, 390px layout and independent recording walkthrough.");
} catch (error) {
  await writeFile(path.join(output, "result.json"), JSON.stringify({passed: false, url: base, checks, errors, error: String(error.stack)}, null, 2));
  throw error;
} finally {
  await browser?.close();
  if (server?.exitCode === null) server.kill();
}
