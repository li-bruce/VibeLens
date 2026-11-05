/** Capture real viewer states for the product page, with their original evidence. */
import assert from "node:assert/strict";
import { startSite } from "./site_browser_fixture.mjs";
import { createRequire } from "node:module";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
const { chromium } = createRequire(import.meta.url)("playwright");
const artifact = JSON.parse(await readFile("docs/site/case-data/v1.json", "utf8"));
const anchor = artifact.view.model.nodes.find((node) => node.id === artifact.story.inspection_node);
const output = "docs/site/images";
await mkdir(output, { recursive: true });
const server = await startSite();
const base = server.url;
let browser;
const captures = [];
try {
  browser = await chromium.launch({
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
    ...(process.env.BO_BROWSER_EXECUTABLE
      ? { executablePath: process.env.BO_BROWSER_EXECUTABLE }
      : {}),
  });
  for (const locale of ["en", "zh-CN"]) {
    const page = await browser.newPage({
      viewport: { width: 1100, height: 560 },
      deviceScaleFactor: 1.5,
    });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    await page.addInitScript(() =>
      addEventListener("message", (event) => {
        if (event.source !== window) return;
        if (event.data.type === "vibelens-case-ready") window.captureTransportReady = true;
        if (event.data.type === "vibelens-case-error") window.captureError = event.data.error;
      }),
    );
    await page.goto(base + "/viewer/index.html?case=1&lang=" + locale);
    await page.waitForFunction(() => window.captureTransportReady);
    await page.evaluate(() => {
      addEventListener("message", (event) => {
        if (event.source === window && event.data.type === "vibelens-scene-ready")
          document.body.dataset.captureReady = event.data.scene;
      });
      postMessage(
        {
          type: "vibelens-case",
          scene: "drill",
          mode: "2d",
          compact: true,
          options: { inputs: true, effects: false, states: false },
        },
        location.origin,
      );
    });
    await page.waitForFunction(() => document.body.dataset.captureReady === "drill");
    await page.waitForFunction(
      (symbol) =>
        [...document.querySelectorAll("#source-code mark")].some((mark) =>
          mark.textContent.includes(symbol),
        ),
      anchor.source.symbol.split(".").at(-1),
    );
    await page.waitForTimeout(300);
    const two = `${output}/source-${locale}.png`;
    await page.screenshot({ path: two });
    const source = await page.locator("#source-code").textContent();
    assert.ok(source.includes(artifact.story.source_excerpt));
    await page.evaluate(() => {
      document.body.dataset.captureReady = "";
      postMessage(
        {
          type: "vibelens-case",
          scene: "watch",
          mode: "3d",
          compact: true,
          options: { inputs: true, effects: false, states: true },
        },
        location.origin,
      );
    });
    await page.waitForFunction(
      () =>
        document.body.dataset.captureReady === "watch" &&
        graphDebug.spatial?.perspective &&
        !graphDebug.layoutBusy,
    );
    await page.mouse.move(520, 290);
    await page.mouse.down();
    await page.mouse.move(655, 195, { steps: 18 });
    await page.mouse.up();
    // Keep the chosen angle and leave room for the lower plane's labels.
    await page.mouse.move(550, 280);
    await page.mouse.wheel(0, 180);
    await page.mouse.move(5, 5);
    await page.waitForTimeout(500);
    const three = `${output}/layers-${locale}.png`;
    await page.screenshot({ path: three });
    const evidence = await page.evaluate(() => ({
      build: graphDebug.view.manifest.build_id,
      nodes: graphDebug.graph.boxes.map((node) => node.id),
      camera: graphDebug.spatial.camera,
      event: graphDebug.view.replay?.event?.id,
    }));
    assert.ok(evidence.nodes.includes(artifact.story.inspection_node));
    assert.deepEqual(errors, []);
    captures.push({
      locale,
      evidence,
      files: await Promise.all(
        [two, three].map(async (file) => ({
          file,
          sha256: createHash("sha256")
            .update(await readFile(file))
            .digest("hex"),
        })),
      ),
    });
    await page.close();
  }
  await writeFile(
    `${output}/capture-proof.json`,
    JSON.stringify(
      {
        source: "case-data/v1.json",
        method: "Native viewer controls and unmodified browser screenshots",
        captures,
      },
      null,
      2,
    ) + "\n",
  );
} finally {
  await browser?.close();
  server.close();
}
console.log("PASS: captured real bilingual source and 3D views");
