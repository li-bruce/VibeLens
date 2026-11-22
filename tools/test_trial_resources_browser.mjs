/** Verify the real application's initial assets, including its browser favicon. */
import assert from "node:assert/strict";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { observeResources } from "./browser_resource_diagnostics.mjs";

const [url, directory, readySelector = "body"] = process.argv.slice(2);
if (!url || !directory)
  throw new Error("Usage: node tools/test_trial_resources_browser.mjs URL OUTPUT [READY_SELECTOR]");
const out = path.resolve(directory);
await mkdir(out, { recursive: true });
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.BO_BROWSER_EXECUTABLE,
});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const resources = await observeResources(page);
const result = { passed: false, url, ...resources };
try {
  await page.goto(url, { waitUntil: "load" });
  await page.locator(readySelector).waitFor({ state: "visible" });
  // Capture the browser's default request itself, not a test-injected replacement.
  const favicon = await resources.waitForResponse(new URL("/favicon.ico", url).href);
  result.favicon = favicon;
  assert.equal(favicon?.status, 200, "Browser favicon request must succeed");
  assert.deepEqual(resources.failures, []);
  assert.deepEqual(resources.consoleErrors, []);
  assert.deepEqual(resources.pageErrors, []);
  await page.screenshot({ path: path.join(out, "application.png") });
  // A missing file must still fail; do not suppress arbitrary static-route errors.
  const negative = await page.request.get(
    new URL("/missing-static-negative-control.svg", url).href,
  );
  result.negative_control = { url: negative.url(), status: negative.status() };
  assert.equal(negative.status(), 404);
  result.passed = true;
} catch (error) {
  result.error = String(error.stack || error);
  await page.screenshot({ path: path.join(out, "failure.png"), timeout: 10000 }).catch(() => {});
  process.exitCode = 1;
} finally {
  await writeFile(path.join(out, "result.json"), JSON.stringify(result, null, 2));
  await browser.close();
}
console.log(
  JSON.stringify({ passed: result.passed, favicon: result.favicon, error: result.error, out }),
);
