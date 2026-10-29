/** Inspect compositor frames during story scrolling, including viewport resizes. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(
  process.env.BO_TRANSITION_EVIDENCE || ".validation/step-flash/acceptance",
);
const base = (process.env.BO_SITE_URL || "http://127.0.0.1:8899").replace(/\/$/, "");
const python =
  process.env.BO_PYTHON ||
  path.resolve(".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const server = process.env.BO_SITE_URL
  ? null
  : spawn(
      python,
      ["-B", "-m", "http.server", "8899", "--bind", "127.0.0.1", "--directory", "docs/site"],
      { windowsHide: true, stdio: "ignore" },
    );
await mkdir(output, { recursive: true });
let browser, failure;
let passed = false;
const errors = [],
  receipts = [];
try {
  for (let attempt = 0; attempt < 60; attempt++) {
    try {
      if ((await fetch(base)).ok) break;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  browser = await chromium.launch({
    headless: true,
    args: ["--enable-unsafe-swiftshader"],
    ...(process.env.BO_BROWSER_EXECUTABLE
      ? { executablePath: process.env.BO_BROWSER_EXECUTABLE }
      : {}),
  });
  // Decode captured frames in a separate page so measurement never changes the UI.
  const decoder = await browser.newPage();
  for (const language of ["en", "zh-CN"])
    for (const mode of ["2d", "3d"]) {
      const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("console", (message) => {
        if (message.type() === "error") errors.push(message.text());
      });
      page.on("response", (response) => {
        if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`);
      });
      await page.goto(`${base}/demo.html?lang=${language}`);
      await page.waitForFunction(() => document.body.dataset.sceneReady === "foundation");
      await page.locator("#run").scrollIntoViewIfNeeded();
      await page.waitForFunction(() => document.body.dataset.sceneReady === "run");
      if (mode === "3d") {
        await page.click("#case-3d");
        await page
          .frame({ url: /viewer\/index.html/ })
          .waitForFunction(() => graphDebug.spatial?.perspective);
      }
      let stage = "run";
      const frames = [],
        client = await page.context().newCDPSession(page);
      client.on("Page.screencastFrame", (event) => {
        frames.push({ stage, data: event.data });
        client.send("Page.screencastFrameAck", { sessionId: event.sessionId }).catch(() => {});
      });
      await client.send("Page.startScreencast", {
        format: "png",
        maxWidth: 1440,
        maxHeight: 1000,
        everyNthFrame: 1,
      });
      const stages = ["run", "drill", "iterate", "verify", "iterate", "drill", "run", "foundation"];
      const sizes = [];
      for (const id of stages) {
        stage = id;
        await page.locator("#" + id).scrollIntoViewIfNeeded();
        await page.waitForFunction((id) => document.body.dataset.sceneReady === id, id);
        await page.waitForTimeout(200);
        sizes.push({ stage: id, ...(await page.locator("#case-graph").boundingBox()) });
      }
      await client.send("Page.stopScreencast");
      const metrics = [];
      for (let index = 0; index < frames.length; index++) {
        const frame = frames[index];
        const blackFraction = await decoder.evaluate(async (data) => {
          const image = new Image();
          image.src = "data:image/png;base64," + data;
          await image.decode();
          const canvas = document.createElement("canvas");
          canvas.width = image.width;
          canvas.height = image.height;
          const context = canvas.getContext("2d");
          context.drawImage(image, 0, 0);
          // This central rectangle stays within the sticky graph in every step.
          const pixels = context.getImageData(420, 300, 650, 450).data;
          let black = 0;
          for (let pixel = 0; pixel < pixels.length; pixel += 4)
            if (Math.max(pixels[pixel], pixels[pixel + 1], pixels[pixel + 2]) < 35) black++;
          return black / (pixels.length / 4);
        }, frame.data);
        metrics.push({ frame: index, stage: frame.stage, blackFraction });
        if (blackFraction > 0.1)
          await writeFile(
            path.join(output, `${language}-${mode}-black-${index}.png`),
            Buffer.from(frame.data, "base64"),
          );
      }
      const receipt = {
        language,
        mode,
        transitions: stages.length,
        frames: metrics.length,
        black_frames: metrics.filter((frame) => frame.blackFraction > 0.1).length,
        worst_black_fraction: Math.max(...metrics.map((frame) => frame.blackFraction)),
        sizes,
      };
      receipts.push(receipt);
      await writeFile(
        path.join(output, `${language}-${mode}-frames.json`),
        JSON.stringify(metrics, null, 2),
      );
      await page.screenshot({ path: path.join(output, `${language}-${mode}-after.png`) });
      assert.ok(
        frames.length > stages.length,
        "Capture must include intermediate compositor frames",
      );
      for (const id of new Set(stages))
        assert.ok(
          metrics.some((frame) => frame.stage === id),
          `No captured transition for ${id}`,
        );
      assert.ok(
        new Set(sizes.map((size) => size.height)).size > 1,
        "Playback must actually resize the graph",
      );
      assert.equal(receipt.black_frames, 0, JSON.stringify(receipt));
      await page.close();
    }
  assert.equal(errors.length, 0, errors.join("\n"));
  passed = true;
  console.log(JSON.stringify({ passed: true, receipts }));
} catch (error) {
  failure = String(error.stack);
  throw error;
} finally {
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify({ passed, receipts, errors, failure }, null, 2),
  );
  await browser?.close();
  server?.kill();
}
