/** Verify one localized viewer navigation per fresh demo entry, then its native story handoff. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";

const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(process.env.BO_DEMO_STARTUP_EVIDENCE || ".validation/demo-startup");
await mkdir(output, { recursive: true });
const localPython = path.resolve(
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const python = process.env.BO_PYTHON || (existsSync(localPython) ? localPython : "python");
const server = process.env.BO_SITE_URL
  ? null
  : spawn(
      python,
      ["-u", "-m", "http.server", "0", "--bind", "127.0.0.1", "--directory", "docs/site"],
      { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] },
    );
let browser;
const results = [];
const report = { valid: false, results };
try {
  const base = process.env.BO_SITE_URL
    ? process.env.BO_SITE_URL.replace(/\/$/, "")
    : await new Promise((resolve, reject) => {
        let stdout = "",
          stderr = "";
        const timeout = setTimeout(
          () => reject(Error("Static host did not start: " + stderr)),
          15000,
        );
        server.once("error", (error) => {
          clearTimeout(timeout);
          reject(error);
        });
        server.stderr.on("data", (chunk) => (stderr += chunk));
        server.stdout.on("data", (chunk) => {
          stdout += chunk;
          const port = /port (\d+)/.exec(stdout)?.[1];
          if (port) {
            clearTimeout(timeout);
            resolve("http://127.0.0.1:" + port);
          }
        });
      });
  browser = await chromium.launch({
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
    ...(process.env.BO_BROWSER_EXECUTABLE
      ? { executablePath: process.env.BO_BROWSER_EXECUTABLE }
      : {}),
  });
  report.browser = browser.version();
  report.base = base;
  for (const language of ["en", "zh-CN"]) {
    for (let iteration = 1; iteration <= 3; iteration++) {
      const context = await browser.newContext({ viewport: { width: 1440, height: 1050 } });
      const page = await context.newPage();
      const result = {
        language,
        iteration,
        fresh_context: true,
        errors: [],
        failed_requests: [],
        navigations: [],
      };
      let releaseData, signalData;
      const heldData = new Promise((resolve) => (releaseData = resolve));
      const dataRequested = new Promise((resolve) => (signalData = resolve));
      // Keep the real child response in flight until the parent has selected its
      // first scene. This exercises startup ordering without synthetic events or sleeps.
      await page.route("**/case-preview/v1.json", async (route) => {
        if (route.request().frame() !== page.mainFrame()) {
          signalData();
          await heldData;
        }
        await route.continue();
      });
      results.push(result);
      page.on("pageerror", (error) =>
        result.errors.push({ message: error.message, stack: error.stack }),
      );
      page.on("requestfailed", (request) =>
        result.failed_requests.push({ url: request.url(), failure: request.failure()?.errorText }),
      );
      page.on("request", (request) => {
        if (request.isNavigationRequest() && /\/viewer\/index\.html\?case=/.test(request.url()))
          result.navigations.push(request.url());
      });
      try {
        const response = await page.goto(base + "/demo.html?lang=" + language, {
          waitUntil: "domcontentloaded",
        });
        assert.equal(response.status(), 200);
        await page.locator("#foundation").scrollIntoViewIfNeeded();
        await page.waitForFunction(() => document.body.dataset.chapter === "0");
        await page.waitForFunction(() => document.body.dataset.sceneReady === "foundation");
        assert.equal(result.navigations.length, 0, "The prepared demo does not start a viewer");
        await page.click("#case-tools");
        let requestTimeout;
        try {
          await Promise.race([
            dataRequested,
            new Promise((resolve, reject) => {
              requestTimeout = setTimeout(
                () => reject(Error("The chosen viewer did not request its real case data")),
                30000,
              );
            }),
          ]);
        } finally {
          clearTimeout(requestTimeout);
        }
        assert.equal(result.navigations.length, 1, "only the chosen localized viewer starts");
        result.delayed_case_data = true;
        releaseData();
        await page.waitForFunction(() => document.body.dataset.sceneReady === "foundation");
        let frame = page.frame({ url: /viewer\/index.html\?case=/ });
        assert.ok(frame);
        await frame.waitForFunction(
          () => window.graphDebug?.graph?.boxes.length > 0 && !graphDebug.layoutBusy,
        );
        assert.equal(await frame.locator("html").getAttribute("lang"), language);
        result.foundation = await frame.evaluate(() => ({
          nodes: graphDebug.graph.boxes.length,
          edges: graphDebug.graph.edges.length,
        }));
        await page.locator('#case-chapters a[href="#run"]').click();
        await page.waitForFunction(() => document.body.dataset.sceneReady === "run");
        await page.click("#run [data-capture-action]");
        await page.locator('[data-app-action="revoke"]:enabled').waitFor();
        await page.click('[data-app-action="revoke"]');
        frame = page.frame({ url: /viewer\/index.html\?case=/ });
        await frame.waitForFunction(
          () => graphDebug.view.replay?.event?.id && !graphDebug.layoutBusy,
        );
        result.run = await frame.evaluate(() => ({
          nodes: graphDebug.graph.boxes.length,
          edges: graphDebug.graph.edges.length,
          event: graphDebug.view.replay.event.id,
        }));
        assert.ok(result.foundation.nodes > 0 && result.foundation.edges > 0);
        assert.ok(result.run.nodes > 0 && result.run.edges > 0 && result.run.event);
        // The first localized viewer is reused across the foundation/run boundary.
        // A second document request used to abort its still-loading case-data fetch.
        assert.equal(
          result.navigations.length,
          1,
          "initial viewer must not be replaced while loading",
        );
        assert.equal(new URL(result.navigations[0]).searchParams.get("lang"), language);
        assert.deepEqual(result.errors, []);
        assert.deepEqual(result.failed_requests, []);
        if (iteration === 1)
          await page.screenshot({ path: path.join(output, language + "-run.png") });
        result.valid = true;
      } catch (error) {
        result.error = error.stack;
        result.valid = false;
      } finally {
        releaseData();
        await context.close();
      }
    }
  }
  report.valid = results.length === 6 && results.every((result) => result.valid);
} catch (error) {
  report.error = error.stack;
} finally {
  await browser?.close();
  server?.kill();
  await writeFile(path.join(output, "result.json"), JSON.stringify(report, null, 2) + "\n");
}
console.log(JSON.stringify({ valid: report.valid, cases: results.length, output }));
assert.ok(report.valid, "localized demo startup and native foundation/run transition must pass");
