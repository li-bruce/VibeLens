/** Verify the complete inventory before any visual filtering or collapsing. */
import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { graphInventory } from "../skills/vibelens/assets/stategraph-viewer/graph-inventory.js";
import { mergeGraph } from "../skills/vibelens/assets/stategraph-viewer/graph-links.js";
import { layerOf, layers } from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";

const [folder, target] = process.argv.slice(2);
const read = async (name) => JSON.parse(await readFile(`${folder}/${name}.json`, "utf8"));
const view = await read("view"),
  code = await read("code");
view.model = mergeGraph(view.model, code);
const { all, rawEdges } = graphInventory(view);
// Parent membership is a real model relation even when the renderer expresses
// it as an enclosing region instead of an extra containment arrow.
rawEdges.push(
  ...[...all.values()]
    .filter((node) => node.parent && all.has(node.parent))
    .map((node) => ({ from: node.parent, to: node.id, type: "contains" })),
);
const layer = (id) => (all.has(id) ? layerOf(all.get(id)) : null);
const records = layers.map(({ id }) => {
  const nodes = [...all.values()].filter((node) => layerOf(node) === id);
  const links = rawEdges.filter((edge) => layer(edge.from) === id || layer(edge.to) === id);
  const crossing = links.filter(
    (edge) => layer(edge.from) && layer(edge.to) && layer(edge.from) !== layer(edge.to),
  );
  assert.ok(nodes.length, `${id} must contain actual declarations`);
  assert.ok(links.length, `${id} must retain its relationships`);
  assert.ok(crossing.length, `${id} must connect to the rest of the project`);
  return {
    id,
    nodes: nodes.length,
    edges: links.length,
    crossing: crossing.length,
    samples: nodes
      .slice(0, 3)
      .map((node) => ({ id: node.id, label: node.label, source: node.source })),
  };
});
// Independently required business operations must not disappear inside a type filter.
for (const id of ["login", "upload", "share", "revoke", "view", "download"])
  assert.ok(all.has(id), `Missing implemented feature: ${id}`);
assert.ok(code.nodes.some((node) => node.code_role === "endpoint"));
assert.ok(code.edges.some((edge) => edge.code_relation === "handles"));
assert.ok(code.edges.some((edge) => edge.code_relation === "defines"));
const result = {
  valid: true,
  layers: records,
  nodes: all.size,
  edges: rawEdges.length,
};
if (target) await writeFile(target, JSON.stringify(result, null, 2) + "\n");
console.log(JSON.stringify(result));
