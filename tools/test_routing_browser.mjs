/** Real Wasm/worker/WebGL acceptance. Synthetic geometry is not business evidence. */
import assert from "node:assert/strict";
import { createServer } from "node:http";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";
const { chromium } = createRequire(import.meta.url)("playwright");
const assets = new URL("../skills/vibelens/assets/stategraph-viewer/", import.meta.url);
const output = pathToFileURL(
  path.resolve(process.env.BO_BROWSER_EVIDENCE || "docs/review/spatial-routing/engine") + path.sep,
);
await mkdir(output, { recursive: true });
const server = createServer(async (req, res) => {
  try {
    const name = req.url.slice(1).split("?")[0];
    if (!name) {
      res.writeHead(200, { "content-type": "text/html" });
      return res.end(
        '<body style="margin:0;background:#f6f8fa;font-family:Segoe UI"><main id="gallery"></main></body>',
      );
    }
    if (name.includes("..")) throw Error("Invalid asset");
    const data = await readFile(new URL(name, assets));
    res.writeHead(200, {
      "content-type": name.endsWith(".wasm") ? "application/wasm" : "text/javascript",
    });
    res.end(data);
  } catch {
    res.writeHead(404);
    res.end();
  }
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.BO_BROWSER_EXECUTABLE,
});
const errors = [],
  results = {};
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto("http://127.0.0.1:" + server.address().port);
  results.geometry = await page.evaluate(async () => {
    const { AvoidLib } = await import("/routing-libavoid.vendor.js");
    await AvoidLib.load(new URL("/libavoid.wasm", location.href).href);
    const { routeScene } = await import("/routing-engine.js"),
      { ObstacleIndex } = await import("/routing-geometry.js");
    const obstacles = [{ key: "wall", id: "wall", kind: "glyph", x: 100, y: 0, r: 40, level: 0 }];
    const edges = [
      {
        id: "one",
        from: "a",
        to: "b",
        type: "call",
        a: { x: 0, y: 0, level: 0 },
        b: { x: 200, y: 0, level: 0 },
      },
    ];
    const cache = new Map(),
      scene = { style: "orthogonal", obstacles, edges, parents: [] };
    const initial = await routeScene(scene, AvoidLib.getInstance(), cache);
    const moved = {
      ...scene,
      obstacles: [{ ...obstacles[0], x: 30, y: initial.routes.get("one")[1].y }],
    };
    const after = await routeScene(moved, AvoidLib.getInstance(), cache);
    const clear = (snapshot, answer) =>
      snapshot.edges.every(
        (e) =>
          answer.routes.has(e.id) &&
          new ObstacleIndex(snapshot.obstacles).clear(answer.routes.get(e.id), e),
      );
    const bundleEdges = Array.from({ length: 6 }, (_, i) => ({
      id: "bundle" + i,
      from: "s" + i,
      to: "t" + i,
      type: "call",
      a: { x: 0, y: i * 12, level: 0 },
      b: { x: 600, y: i * 12, level: 0 },
    }));
    const bundled = await routeScene(
      { style: "bus", obstacles: [], parents: [], edges: bundleEdges },
      AvoidLib.getInstance(),
    );
    const multi = {
      ...scene,
      spatial: true,
      obstacles: [obstacles[0], { ...obstacles[0], key: "middle", x: 100, level: 100 }],
      edges: [{ ...edges[0], b: { x: 200, y: 0, level: 200 } }],
    };
    const cross = await routeScene(multi, AvoidLib.getInstance());
    return {
      initial: initial.stats,
      after: after.stats,
      clear: clear(scene, initial) && clear(moved, after),
      paths: [...initial.routes],
      moved: [...after.routes],
      bundles: bundled.stats,
      bundledPaths: [...bundled.routes],
      cross: [...cross.routes],
    };
  });
  assert.equal(
    results.geometry.clear,
    true,
    "Actual routed segments avoid obstacles before and after unrelated obstacle movement",
  );
  assert.ok(
    results.geometry.initial.wasm > 0,
    "The real browser Wasm engine handled a blocked route",
  );
  assert.ok(
    results.geometry.bundles.bundles > 0 && results.geometry.bundles.routed === 6,
    "Different source nodes share a typed trunk without losing edge IDs",
  );
  assert.equal(results.geometry.cross.length, 1);
  results.icons = await page.evaluate(async () => {
    const { nodeTypes } = await import("/graph-core.js"),
      { legendGlyph } = await import("/glyphs.js"),
      { nodeGeometry, spatialLegend } = await import("/spatial-geometry.js");
    const images = spatialLegend(nodeTypes),
      results = [];
    const gallery = document.querySelector("#gallery");
    gallery.style.cssText =
      "display:grid;grid-template-columns:repeat(5,1fr);gap:24px;padding:36px";
    for (const [type, style] of Object.entries(nodeTypes)) {
      const geometry = nodeGeometry(type),
        dense = nodeGeometry(type, true),
        card = document.createElement("article");
      card.style.cssText =
        "border-bottom:1px solid #dce3e9;padding:16px;display:flex;align-items:center;gap:12px";
      const icon = legendGlyph(type, style);
      icon.style.cssText = "width:42px;height:42px";
      const image = new Image();
      image.src = images.get(type);
      image.width = image.height = 56;
      const title = document.createElement("span");
      title.textContent = style.label;
      card.append(icon, image, title);
      gallery.append(card);
      geometry.computeBoundingBox();
      results.push({
        type,
        icon: geometry.userData.icon,
        object: geometry.userData.object,
        family: geometry.userData.family,
        vertices: geometry.attributes.position.count,
        denseVertices: dense.attributes.position.count,
        thickness: geometry.boundingBox.max.y - geometry.boundingBox.min.y,
        finite: [...geometry.attributes.position.array].every(Number.isFinite),
      });
      geometry.dispose();
      dense.dispose();
    }
    await Promise.all([...document.images].map((img) => img.decode()));
    return results;
  });
  assert.equal(results.icons.length, 19);
  assert.ok(results.icons.every((n) => n.family === "VibeLens solids"));
  assert.equal(results.icons.find((n) => n.type === "store").object, "tiered-database");
  assert.equal(results.icons.find((n) => n.type === "resource").object, "stacked-crates");
  assert.ok(
    new Set(results.icons.map((n) => n.icon)).size >= 18,
    "Semantic silhouettes distinguish node types",
  );
  assert.ok(
    results.icons.every((n) => n.finite && n.thickness > 0.1 && n.denseVertices < n.vertices),
    "Real volumetric meshes offer reduced detail for dense graphs",
  );
  await page.screenshot({ path: fileURLToPath(new URL("icons.png", output)) });
  assert.deepEqual(errors, []);
  results.passed = true;
} catch (error) {
  results.error = String(error.stack || error);
  throw error;
} finally {
  await writeFile(new URL("results.json", output), JSON.stringify({ ...results, errors }, null, 2));
  await browser.close();
  server.close();
}
console.log(
  "PASS: real libavoid, obstacle invalidation, typed bundles, cross-layer route and 19 matched 2D/3D icons.",
);
