/** Replay the discovery-only trial's actual camera and layout with canonical assets. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";

const { chromium } = createRequire(import.meta.url)("playwright");
const out = path.resolve(process.env.BO_CAPTION_EVIDENCE || ".validation/caption-bounds");
const source = "docs/review/execution-lanes-20261031/caption-fixture";
const project = path.join(out, "project");
await mkdir(path.join(project, "bo_stategraph/config/views"), {
  recursive: true,
});
await copyFile(path.join(source, "discovery.json"), path.join(project, "discovery.json"));
await copyFile(
  path.join(source, "local.json"),
  path.join(project, "bo_stategraph/config/views/local.json"),
);
const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
const original = hash(await readFile(path.join(source, "discovery.json")));
const server = spawn(
  path.resolve(".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python"),
  [
    "-B",
    "-X",
    "utf8",
    "skills/vibelens/scripts/bo_web.py",
    "serve",
    "--root",
    project,
    "--port",
    "0",
  ],
  { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] },
);
let browser, page;
const errors = [],
  results = [];
try {
  const url = await new Promise((resolve, reject) => {
    let output = "",
      error = "";
    const timeout = setTimeout(
      () => reject(Error("Design host did not print its URL: " + error)),
      15000,
    );
    server.stderr.on("data", (chunk) => (error += chunk));
    server.stdout.on("data", (chunk) => {
      output += chunk;
      if (output.includes("\n")) {
        clearTimeout(timeout);
        resolve(output.split("\n")[0].trim().split(" ").at(-1));
      }
    });
    server.once("exit", (code) => {
      clearTimeout(timeout);
      reject(Error(`Design host exited ${code}: ${error}`));
    });
  });
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  page.on("pageerror", (error) => errors.push(String(error.stack)));
  await page.goto(url + "?lang=zh-CN");
  await page.waitForFunction(() => graphDebug?.planarCaptions?.length && !graphDebug.layoutBusy);
  const geometry = () =>
    page.evaluate(() => ({
      nodes: graphDebug.graph.boxes.map((b) => [b.id, b.x, b.y]),
      camera: graphDebug.camera,
    }));
  const before = await geometry();
  assert.ok(Math.abs(before.camera.scale - 0.40779422018348793) < 1e-6);
  async function check(label) {
    const captions = await page.evaluate(() => graphDebug.planarCaptions);
    assert.ok(captions.length >= 8);
    for (const a of captions) {
      assert.ok(
        a.x >= a.node.x - 0.1 && a.x + a.w <= a.node.x + a.node.w + 0.1,
        a.id + " exceeds horizontal bounds",
      );
      assert.ok(a.y + a.h <= a.limitBottom + 0.1, a.id + " exceeds vertical bounds");
      for (const b of captions) {
        if (a.id >= b.id) continue;
        const overlaps = a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
        assert.equal(overlaps, false, `${a.id} overlaps ${b.id}`);
      }
    }
    const pair = captions.filter((c) => ["upload_file", "privileged_access"].includes(c.id));
    assert.equal(pair.length, 2);
    assert.ok(
      pair.some((c) => c.text !== c.raw),
      "Actual long caption should wrap or truncate",
    );
    results.push({ label, camera: (await geometry()).camera, captions });
  }
  await check("Original discovery camera, explained names");
  await page.screenshot({ path: path.join(out, "discovery-2d.png") });
  await page.click("#name-mode");
  await check("Source names");
  assert.deepEqual(await geometry(), before);
  await page.click("#name-mode");
  assert.deepEqual(await geometry(), before);
  // Native wheel zoom must retain the same bounded-caption policy.
  const canvas = page.locator("#viewport canvas").first();
  const box = await canvas.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.wheel(0, -170);
  await page.waitForFunction(
    (scale) => graphDebug.camera.scale > scale && !graphDebug.layoutBusy,
    before.camera.scale,
  );
  await check("Zoomed discovery");
  while ((await geometry()).camera.scale > 0.27) {
    const prior = await page.evaluate(() => ({
      scale: graphDebug.camera.scale,
      frame: graphDebug.metrics.drawCount,
    }));
    await page.mouse.wheel(0, 100);
    await page.waitForFunction(
      (prior) =>
        graphDebug.camera.scale < prior.scale &&
        graphDebug.metrics.drawCount > prior.frame &&
        !graphDebug.layoutBusy,
      prior,
    );
  }
  await check("Overview around 26 percent retains node captions");
  await page.screenshot({ path: path.join(out, "overview-26-percent.png") });
  const caption = await page.evaluate(() =>
      graphDebug.planarCaptions.find((c) => c.id === "upload_file"),
    ),
    camera = (await geometry()).camera;
  assert.ok(caption.y + caption.h > caption.node.y + caption.node.h);
  const captionY =
    (Math.max(caption.y, caption.node.y + caption.node.h) + caption.y + caption.h) / 2;
  const currentCanvas = await canvas.boundingBox();
  await page.mouse.click(
    currentCanvas.x + camera.pan.x + (caption.x + caption.w / 2) * camera.scale,
    currentCanvas.y + camera.pan.y + captionY * camera.scale,
  );
  await page.waitForSelector('#semantic [data-node-id="upload_file"][aria-pressed="true"]');
  assert.deepEqual((await geometry()).nodes, before.nodes);
  assert.equal(hash(await readFile(path.join(project, "discovery.json"))), original);
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify({ valid: true, sourceSHA256: original, results, errors }, null, 2) + "\n",
  );
  console.log(JSON.stringify({ valid: true, out, checks: results.length }));
} catch (error) {
  await page?.screenshot({ path: path.join(out, "failure.png") }).catch(() => {});
  await writeFile(
    path.join(out, "result.json"),
    JSON.stringify({ valid: false, error: String(error.stack), results, errors }, null, 2) + "\n",
  );
  throw error;
} finally {
  await browser?.close();
  server.kill();
}
