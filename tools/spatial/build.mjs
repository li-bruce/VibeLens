import { build } from "esbuild";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { join, resolve } from "node:path";
const output = resolve(
  process.env.VIBELENS_SPATIAL_BUILD_DIR ||
    fileURLToPath(new URL("../../skills/vibelens/assets/stategraph-viewer/", import.meta.url)),
);
await mkdir(output, { recursive: true });
for (const [name, source] of Object.entries({
  "spatial-three.vendor.js":
    'export * from "three"; export { OrbitControls } from "three/addons/controls/OrbitControls.js"; export { LineSegments2 } from "three/addons/lines/LineSegments2.js"; export { LineSegmentsGeometry } from "three/addons/lines/LineSegmentsGeometry.js"; export { LineMaterial } from "three/addons/lines/LineMaterial.js";',
  "spatial-force.vendor.js": 'export * from "d3-force-3d";',
})) {
  await build({
    stdin: { contents: source, resolveDir: fileURLToPath(new URL(".", import.meta.url)) },
    outfile: join(output, name),
    bundle: true,
    format: "esm",
    minify: true,
    legalComments: "eof",
    target: "es2022",
  });
}
const packages = [
  "three",
  "d3-force-3d",
  "d3-dispatch",
  "d3-timer",
  "d3-binarytree",
  "d3-quadtree",
  "d3-octree",
];
const notices = await Promise.all(
  packages.map(
    async (name) =>
      name +
      "\n" +
      (await readFile(new URL(`node_modules/${name}/LICENSE`, import.meta.url), "utf8")),
  ),
);
await writeFile(join(output, "SPATIAL-LICENSES.txt"), notices.join("\n\n----------------\n\n"));
