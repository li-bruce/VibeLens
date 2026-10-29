/** Run the frontend/backend story and export only real observer recordings. */
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import zlib from "node:zlib";

const { chromium } = createRequire(import.meta.url)("playwright");
const repo = fileURLToPath(new URL("../", import.meta.url));
const python =
  process.env.BO_PYTHON ||
  path.join(repo, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const out = path.resolve(
  process.env.BO_CASE_EVIDENCE || ".validation/exhibition-case-" + Date.now(),
);
// Legacy regression exports belong to their evidence run, separate from Pages.
const exported = path.resolve(process.env.BO_CASE_EXPORT || path.join(out, "case-data"));
await mkdir(out, { recursive: true });
await mkdir(exported, { recursive: true });

/** Encode two visibly different real PNGs, with valid checksums and image data. */
function png(color) {
  function chunk(type, bytes) {
    const data = Buffer.concat([Buffer.from(type), bytes]);
    let crc = 0xffffffff;
    for (const byte of data) {
      crc ^= byte;
      for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
    }
    const header = Buffer.alloc(4),
      tail = Buffer.alloc(4);
    header.writeUInt32BE(bytes.length);
    tail.writeUInt32BE((crc ^ 0xffffffff) >>> 0);
    return Buffer.concat([header, data, tail]);
  }
  const head = Buffer.alloc(13);
  head.writeUInt32BE(240);
  head.writeUInt32BE(160, 4);
  head[8] = 8;
  head[9] = 2;
  const rows = [];
  for (let y = 0; y < 160; y++) {
    const row = Buffer.alloc(1 + 240 * 3);
    for (let x = 0; x < 240; x++)
      for (let c = 0; c < 3; c++)
        row[1 + x * 3 + c] = Math.min(255, color[c] + Math.floor((x + y) / 12));
    rows.push(row);
  }
  return Buffer.concat([
    Buffer.from("89504e470d0a1a0a", "hex"),
    chunk("IHDR", head),
    chunk("IDAT", zlib.deflateSync(Buffer.concat(rows))),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}
const first = png([36, 90, 155]),
  second = png([184, 92, 52]);
await writeFile(path.join(exported, "image-1.png"), first);
await writeFile(path.join(exported, "image-2.png"), second);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const reports = [];
const browser = await chromium.launch({
  headless: true,
  args: ["--enable-unsafe-swiftshader"],
  ...(process.env.BO_BROWSER_EXECUTABLE
    ? { executablePath: process.env.BO_BROWSER_EXECUTABLE }
    : {}),
});
try {
  for (const version of [1, 2]) {
    const root = path.join(out, "v" + version),
      port = 8893 + version,
      base = "http://127.0.0.1:" + port;
    const prepared = spawnSync(
      python,
      [
        "-B",
        "-X",
        "utf8",
        "examples/exhibition-review/prepare.py",
        "--root",
        root,
        "--version",
        String(version),
      ],
      { cwd: repo, encoding: "utf8", windowsHide: true },
    );
    await writeFile(path.join(out, `v${version}-prepare.txt`), prepared.stdout + prepared.stderr);
    assert.equal(prepared.status, 0, prepared.stderr);
    const server = spawn(
      python,
      [
        "-B",
        "-X",
        "utf8",
        path.join(root, "app.py"),
        "--root",
        root,
        "--skill",
        path.join(repo, "skills/vibelens"),
        "--port",
        String(port),
      ],
      { cwd: repo, windowsHide: true },
    );
    let logs = "";
    server.stdout.on("data", (part) => (logs += part));
    server.stderr.on("data", (part) => (logs += part));
    const page = await browser.newPage({ viewport: { width: 1440, height: 940 } });
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    async function api(route, body) {
      const response = await fetch(base + route, {
        signal: AbortSignal.timeout(10000),
        ...(body === undefined
          ? {}
          : {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(body),
            }),
      });
      const value = await response.json();
      assert.ok(response.ok, JSON.stringify(value));
      return value;
    }
    try {
      let ready = false;
      for (let i = 0; i < 45; i++) {
        try {
          await api("/api/bo/health");
          ready = true;
          break;
        } catch {
          await sleep(200);
        }
      }
      assert.ok(ready, logs);
      const health = await api("/api/bo/health");
      await page.goto(base + "/app");
      const start = await api("/api/recordings/start", {
        label: "Old preview, new upload · v" + version,
      });
      await page.setInputFiles("#image", {
        name: "light.png",
        mimeType: "image/png",
        buffer: first,
      });
      await page.click("#upload");
      await page.waitForFunction(() =>
        document.querySelector("#upload-result").textContent.includes('"image_version": 1'),
      );
      await page.click("#preview");
      await page.waitForFunction(
        () => document.querySelector("#review-version").textContent === "Opened version 1",
      );
      await page.waitForFunction(() => document.querySelector("#review-image").complete);
      await page.setInputFiles("#image", {
        name: "ember.png",
        mimeType: "image/png",
        buffer: second,
      });
      await page.click("#upload");
      await page.waitForFunction(() =>
        document.querySelector("#upload-result").textContent.includes('"image_version": 2'),
      );
      await page.click("#approve");
      await page.waitForFunction(() =>
        /displayed|stale_review/.test(document.querySelector("#review-result").textContent),
      );
      await page.waitForFunction(
        (version) =>
          document.querySelector("#public-version").textContent ===
          (version === 1 ? "Published version 2" : "Nothing published"),
        version,
      );
      if (version === 1)
        await page.waitForFunction(
          () =>
            document.querySelector("#public-image").complete &&
            document.querySelector("#public-image").naturalWidth > 0,
        );
      const staleResult = JSON.parse(await page.locator("#review-result").textContent());
      const database = await api("/app/public", {});
      await page.screenshot({
        path: path.join(out, `v${version}-stale-review.png`),
        fullPage: true,
      });
      assert.equal(staleResult.status, version === 1 ? "displayed" : "stale_review");
      assert.equal(database.published_version, version === 1 ? 2 : null);
      // An independent requirement is deliberately red for v1, green after the fix.
      const business = {
        case: "Reject a review of a replaced image",
        expected: "stale_review",
        actual: staleResult.status,
        passed: staleResult.status === "stale_review",
      };
      if (version === 2) {
        const before = await api("/app/public", {});
        assert.equal(
          (await api("/app/approve", { actor: "artist", reviewed_version: 2 })).status,
          "forbidden",
        );
        assert.deepEqual(
          await api("/app/public", {}),
          before,
          "Denied review must not change the database",
        );
        assert.equal(
          (
            await api("/app/upload", {
              actor: "artist",
              title: "invalid",
              image: Buffer.from("not a PNG").toString("base64"),
            })
          ).status,
          "invalid_image",
        );
        await page.click("#preview");
        await page.waitForFunction(
          () => document.querySelector("#review-version").textContent === "Opened version 2",
        );
        await page.click("#approve");
        await page.waitForFunction(
          () => document.querySelector("#public-version").textContent === "Published version 2",
        );
        await page.waitForFunction(
          () =>
            document.querySelector("#public-image").complete &&
            document.querySelector("#public-image").naturalWidth > 0,
        );
        await page.screenshot({
          path: path.join(out, "v2-reviewed-and-published.png"),
          fullPage: true,
        });
      }
      const stopped = await api("/api/recordings/stop", {});
      const recording = await api("/api/recordings/" + (stopped.id || start.id));
      const view = await api("/api/view");
      const code = await api("/api/code/graph?limit=1500&depth=3");
      const codeFocus = {};
      for (const focus of [
        "upload",
        "review",
        "publish",
        "exhibit",
        "review-policy",
        "choose-version",
      ])
        codeFocus[focus] = await api("/api/code/graph?focus=" + focus + "&limit=400&depth=1");
      const catalog = await api("/api/recordings");
      assert.equal(code.errors.length, 0, JSON.stringify(code.errors));
      const count = view.events.length;
      await api("/api/view");
      await api("/api/design");
      await api("/api/preferences");
      await api("/api/code/graph?limit=1500");
      assert.equal(
        (await api("/api/view")).events.length,
        count,
        "Observer actions must not record themselves",
      );
      assert.equal(view.health.errors, 0);
      assert.equal(view.binding_status.status, "current");
      assert.ok(
        view.runtime_frames.frames.length > 3,
        "State changes require actual retained frames",
      );
      for (const id of [
        "api.upload",
        "api.review",
        "api.publish",
        "api.exhibit",
        "upload",
        "review",
        "publish",
        "exhibit",
        "image-check",
        "review-policy",
        "choose-version",
        "read-artwork",
        "save-upload",
        "save-exhibition",
        "read-public",
        "read-image",
        "review-transaction",
      ])
        assert.ok(
          view.events.some((event) => event.node === id),
          "Mapped operation lacks runtime evidence: " + id,
        );
      assert.ok(
        view.events.some(
          (event) =>
            event.node === "review-policy" &&
            event.inputs.reviewed_version === 1 &&
            event.inputs.current_version === 2,
        ),
      );
      assert.ok(
        view.events.some((event) => event.node === "save-exhibition" && event.phase === "commit") ||
          view.events.some(
            (event) => event.node === "review-transaction" && event.phase === "commit",
          ),
      );
      const sources = recording.sources;
      for (const name of new Set(code.nodes.map((node) => node.source?.path).filter(Boolean)))
        if (!sources[name]) sources[name] = await readFile(path.join(root, name), "utf8");
      const artifact = {
        schema: "vibelens-case/v1",
        version,
        provenance: {
          kind: "real-local-execution",
          teaching_defect: version === 1,
          build_id: health.build_id,
        },
        view,
        recording,
        catalog,
        code,
        codeFocus,
        sources,
        business,
        staleResult,
        database,
      };
      await writeFile(path.join(exported, `v${version}.json`), JSON.stringify(artifact));
      const mapped = spawnSync(
        python,
        [
          "-B",
          "-X",
          "utf8",
          "tools/check_exhibition_case.py",
          "--root",
          root,
          "--artifact",
          path.join(exported, `v${version}.json`),
        ],
        { cwd: repo, encoding: "utf8", windowsHide: true },
      );
      await writeFile(
        path.join(out, `v${version}-mapping-check.txt`),
        mapped.stdout + mapped.stderr,
      );
      assert.equal(mapped.status, 0, mapped.stderr);
      await writeFile(
        path.join(out, `v${version}-business-check.json`),
        JSON.stringify(business, null, 2),
      );
      assert.equal(errors.length, 0, errors.join("\n"));
      reports.push({
        version,
        business,
        mapping: "passed",
        events: count,
        frames: view.runtime_frames.frames.length,
        source_nodes: code.nodes.length,
        source_edges: code.edges.length,
        observer_events: 0,
        build_id: health.build_id,
      });
    } finally {
      await page.close();
      server.kill();
      await writeFile(path.join(out, `v${version}-server.txt`), logs);
    }
  }
  assert.equal(reports[0].business.passed, false);
  assert.equal(reports[1].business.passed, true);
  await writeFile(
    path.join(exported, "receipt.json"),
    JSON.stringify({ schema: "vibelens-case-receipt/v1", runs: reports }, null, 2),
  );
  await writeFile(
    path.join(out, "summary.json"),
    JSON.stringify({ passed: true, reports }, null, 2),
  );
  console.log(JSON.stringify({ passed: true, output: out, reports }));
} finally {
  await browser.close();
}
