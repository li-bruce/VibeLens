/** Build separately replaceable routing libraries; never inline the LGPL Wasm. */
import { build } from "esbuild";
import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
const output = new URL("../../skills/vibelens/assets/stategraph-viewer/", import.meta.url);
await mkdir(output, { recursive: true });
await build({
  stdin: {
    contents:
      'export {default as RBush} from "rbush"; export {hierarchy,stratify} from "d3-hierarchy"; export {line,curveBundle} from "d3-shape"; export {Delaunay} from "d3-delaunay"; export {default as createGraph} from "ngraph.graph"; export {aGreedy} from "ngraph.path";',
    resolveDir: fileURLToPath(new URL(".", import.meta.url)),
  },
  outfile: fileURLToPath(new URL("routing-tools.vendor.js", output)),
  bundle: true,
  format: "esm",
  minify: true,
  legalComments: "eof",
  target: "es2022",
});
for (const [source, target] of [
  ["index.js", "routing-libavoid.vendor.js"],
  ["libavoid.wasm", "libavoid.wasm"],
  ["index.js.map", "index.js.map"],
])
  await copyFile(
    new URL(`node_modules/libavoid-js/dist/${source}`, import.meta.url),
    new URL(target, output),
  );
const packages = [
  "libavoid-js",
  "d3-hierarchy",
  "d3-shape",
  "d3-path",
  "rbush",
  "quickselect",
  "d3-delaunay",
  "delaunator",
  "robust-predicates",
  "ngraph.graph",
  "ngraph.path",
  "ngraph.events",
];
const notices = await Promise.all(
  packages.map(
    async (name) =>
      `${name}\n${await readFile(new URL(`node_modules/${name}/LICENSE`, import.meta.url), "utf8")}`,
  ),
);
await writeFile(new URL("ROUTING-LICENSES.txt", output), notices.join("\n\n----------------\n\n"));
