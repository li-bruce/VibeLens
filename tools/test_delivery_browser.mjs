/** Load the installed delivery viewer, including its complete 2D/3D import graph. */
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { cp, mkdir, mkdtemp, lstat, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const { chromium } = createRequire(import.meta.url)("playwright");
const output = path.resolve(process.env.BO_BROWSER_EVIDENCE || ".validation/delivery-browser");
await mkdir(output, { recursive: true });
await mkdir(path.join(root, ".validation"), { recursive: true });
const parent = path.resolve(root, ".validation");
assert.equal((await lstat(parent)).isSymbolicLink(), false);
const folder = await mkdtemp(path.join(parent, "delivery-browser-"));
const example = path.join(folder, "delivery");
const source = path.join(root, "examples/delivery");
const ignored = new Set([
  "scratch",
  "history",
  "dist",
  ".stategraph",
  "__pycache__",
  "node_modules",
]);
await cp(source, example, {
  recursive: true,
  filter: (name) =>
    !path
      .relative(source, name)
      .split(path.sep)
      .some((part) => ignored.has(part)),
});
const server = spawn(
  process.env.BO_PYTHON ||
    path.join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python"),
  ["-B", "-X", "utf8", "integrations/bo_server.py", "0"],
  { cwd: example, windowsHide: true },
);
let logs = "",
  browser,
  page;
const errors = [],
  missingAssets = [];
server.stderr.on("data", (data) => (logs += data));
try {
  const info = await new Promise((resolve, reject) => {
    let line = "";
    const timer = setTimeout(() => reject(Error("Delivery server did not start: " + logs)), 30000);
    server.once("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    server.once("exit", (code) => {
      clearTimeout(timer);
      reject(Error("Delivery exited before startup: " + code + " " + logs));
    });
    server.stdout.on("data", (data) => {
      line += data;
      if (!line.includes("\n")) return;
      clearTimeout(timer);
      try {
        resolve(JSON.parse(line.split("\n")[0]));
      } catch (error) {
        reject(error);
      }
    });
  });
  browser = await chromium.launch({
    headless: true,
    executablePath: process.env.BO_BROWSER_EXECUTABLE,
  });
  page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (error) => errors.push(String(error)));
  page.on("response", (response) => {
    if (!response.ok() && /\.(js|mjs|wasm)$/.test(new URL(response.url()).pathname))
      missingAssets.push(response.url());
  });
  await page.goto(info.url + "/graph?lang=en");
  await page.waitForFunction(() => window.graphDebug?.graph?.boxes.length > 0);
  await page.screenshot({ path: path.join(output, "delivery-2d.png") });
  await page.click("#layered-toggle");
  await page.waitForFunction(() => graphDebug.spatial?.webgl && !graphDebug.layoutBusy);
  await page.screenshot({ path: path.join(output, "delivery-3d.png") });
  const view = await page.evaluate(() => fetch("/api/view").then((response) => response.json()));
  assert.equal(view.binding_status.status, "current");
  assert.deepEqual(missingAssets, []);
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(output, "result.json"),
    JSON.stringify({ passed: true, build_id: info.build_id, missingAssets, errors }, null, 2),
  );
  console.log(
    "PASS: installed delivery viewer loads every module and renders both 2D and genuine 3D.",
  );
} catch (error) {
  await page?.screenshot({ path: path.join(output, "failure.png") }).catch(() => {});
  await writeFile(
    path.join(output, "failure.json"),
    JSON.stringify({ error: String(error.stack), missingAssets, errors }, null, 2),
  );
  throw error;
} finally {
  await browser?.close();
  if (server.pid && server.exitCode === null && server.signalCode === null) {
    const exited = new Promise((resolve) => server.once("exit", resolve));
    assert.ok(server.kill(), "The owned test server could not be stopped");
    await exited;
  }
  await writeFile(path.join(output, "server.log"), logs);
  assert.equal(path.dirname(path.resolve(folder)), parent);
  assert.equal((await lstat(folder)).isSymbolicLink(), false);
  await rm(folder, { recursive: true, force: true });
}
