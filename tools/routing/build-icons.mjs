/** Select a small licensed icon vocabulary; ship no font, CDN or complete icon pack. */
import { readFile, writeFile } from "node:fs/promises";
import { svgPathProperties } from "svg-path-properties";
import svgpath from "svgpath";
const root = new URL("../../skills/vibelens/assets/stategraph-viewer/", import.meta.url);
const names = {
  business: "route",
  state: "circle-dot",
  decision: "git-branch",
  function: "function",
  data: "variable",
  resource: "stack-2",
  wait: "hourglass",
  effect: "check",
  store: "database",
  dataset: "table",
  column: "table-column",
  query: "database-search",
  transform: "transform",
  "code-endpoint": "api",
  "code-file": "file-code",
  "code-class": "cube",
  "code-function": "code",
  "code-parameter": "brackets",
  "code-unresolved": "question-mark",
};
const nodes = JSON.parse(
  await readFile(new URL("node_modules/@tabler/icons/tabler-nodes-outline.json", import.meta.url)),
);
const paths = {};
// Tabler uses path/line/rect/circle/polyline primitives. Convert them at build
// time so Pixi and the real volumetric meshes consume identical centerlines.
for (const [type, name] of Object.entries(names)) {
  if (!nodes[name]) throw Error("Missing pinned icon: " + name);
  const commands = nodes[name].flatMap(([tag, a]) => {
    if (a.stroke === "none") return [];
    if (tag === "path") return [a.d];
    if (tag === "line") return [`M${a.x1} ${a.y1} L${a.x2} ${a.y2}`];
    if (tag === "circle")
      return [
        `M${+a.cx + +a.r} ${a.cy} a${a.r} ${a.r} 0 1 0 ${-2 * a.r} 0 a${a.r} ${a.r} 0 1 0 ${2 * a.r} 0`,
      ];
    if (tag === "rect") return [`M${a.x} ${a.y} h${a.width} v${a.height} h${-a.width} Z`];
    if (tag === "polyline" || tag === "polygon")
      return ["M" + a.points + (tag === "polygon" ? "Z" : "")];
    throw Error("Unreviewed SVG primitive: " + tag);
  });
  const strokes = commands
    .flatMap((d) => svgpath(d).abs().toString().split(/(?=M)/).filter(Boolean))
    .map((d) => {
      const curve = new svgPathProperties(d),
        length = curve.getTotalLength();
      const count = Math.max(1, Math.ceil(length / 0.7));
      return Array.from({ length: count + 1 }, (_, i) => {
        const p = curve.getPointAtLength((length * i) / count);
        return [Math.round((p.x - 12) * 1000) / 1000, Math.round((p.y - 12) * 1000) / 1000];
      });
    });
  paths[type] = { name, strokes };
}
await writeFile(
  new URL("node-icons.js", root),
  "// Generated from @tabler/icons 3.49.0 (MIT). Run tools/routing/build-icons.mjs.\nexport const nodeIcons = " +
    JSON.stringify(paths) +
    ";\nexport const iconFor = (type) => nodeIcons[type] || nodeIcons.function;\n",
);
await writeFile(
  new URL("NODE-ICONS-LICENSE.txt", root),
  "Tabler Icons 3.49.0\nhttps://github.com/tabler/tabler-icons\nSelected vectors are sampled into shared 2D strokes and volumetric 3D meshes.\n\n" +
    (await readFile(new URL("node_modules/@tabler/icons/LICENSE", import.meta.url), "utf8")),
);
