/** Display detail preserves source identities, old exclusions and causal paths. */
import assert from "node:assert/strict";
import {
  classifyNode,
  implementationFacets,
} from "../skills/vibelens/assets/stategraph-viewer/graph-classification.js";
import {
  cleanLayers,
  layerOf,
  layerSlice,
  savedLayerVisibility,
} from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";

const nodes = [
  { id: "api", code_role: "endpoint" },
  { id: "handler", kind: "function", api_role: "capture" },
  { id: "dir", code_role: "directory" },
  { id: "file", code_role: "file" },
  { id: "fn", code_role: "function" },
  { id: "arg", code_role: "parameter" },
  { id: "read", data_role: "query" },
  { id: "value", kind: "data", capture_owner_role: "query" },
  { id: "observed", kind: "function" },
];
assert.deepEqual(nodes.map(layerOf), [
  "entry",
  "symbols",
  "structure",
  "structure",
  "symbols",
  "symbols",
  "symbols",
  "symbols",
  "symbols",
]);
assert.ok(nodes.every((node) => classifyNode(node).layer === "implementation"));
const boxes = nodes.map((node) => ({ id: node.id, node }));
const rawEdges = [
  { id: "handles", from: "api", to: "fn", type: "maps", code_relation: "handles" },
  { id: "defines", from: "file", to: "fn", type: "maps", code_relation: "defines" },
  { id: "reads", from: "fn", to: "read", type: "reads" },
];
const graph = {
  boxes,
  all: new Map(nodes.map((node) => [node.id, node])),
  edges: rawEdges,
  rawEdges,
};
const original = JSON.stringify({ nodes, rawEdges });
function selected(config) {
  return layerSlice(graph, config)
    .boxes.map((box) => box.id)
    .sort();
}
for (let mask = 0; mask < 32; mask++) {
  const facets = implementationFacets.filter((_, i) => mask & (1 << i));
  const expected = nodes
    .filter((node) => facets.includes(classifyNode(node).facet))
    .map((node) => node.id)
    .sort();
  const migrated = cleanLayers({ schema: 3, visible: ["implementation"], facets });
  assert.deepEqual(selected(migrated), expected);
  assert.deepEqual(selected(cleanLayers({ visible: savedLayerVisibility(migrated) })), expected);
  assert.deepEqual(selected(cleanLayers({ visible: facets })), expected);
}
for (const visible of [["entry"], ["structure"], ["symbols"], ["entry", "symbols"]]) {
  const config = cleanLayers({ visible });
  assert.deepEqual(cleanLayers(config), config);
  assert.deepEqual(
    selected(cleanLayers({ visible: savedLayerVisibility(config) })),
    selected(config),
  );
}
assert.equal(JSON.stringify({ nodes, rawEdges }), original);
assert.deepEqual(layerSlice(graph, cleanLayers({ visible: ["implementation"] })).edges, rawEdges);
console.log(
  "PASS: three reading scales, canonical concern identity, all legacy facet subsets, no saved-view widening.",
);
