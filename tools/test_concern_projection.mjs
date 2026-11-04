/** Concern consolidation preserves definitions, exclusions and bounded path proofs. */
import assert from "node:assert/strict";
import { performance } from "node:perf_hooks";
import {
  layers,
  layerOf,
  cleanLayers,
  savedLayerVisibility,
  layerSlice,
} from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
import {
  implementationFacet,
  classifyNode,
} from "../skills/vibelens/assets/stategraph-viewer/graph-classification.js";
import { graphInventory } from "../skills/vibelens/assets/stategraph-viewer/graph-inventory.js";
import { visualType } from "../skills/vibelens/assets/stategraph-viewer/graph-classification.js";
import { captureDetailRows } from "../skills/vibelens/assets/stategraph-viewer/capture-fields.js";
import {
  emptyFilters,
  cleanFilters,
  filterNode,
  relationStyle,
} from "../skills/vibelens/assets/stategraph-viewer/layout.js";
import { transferEdges } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import { projectHiddenPaths } from "../skills/vibelens/assets/stategraph-viewer/hidden-paths.js";
import { profileFor } from "../skills/vibelens/assets/stategraph-viewer/analysis.js";

const source = { path: "service.py", symbol: "download" };
const nodes = [
  { id: "a", kind: "action", layer: "business", label: "Download", source },
  { id: "f", kind: "function", label: "download", source },
  { id: "r", kind: "decision", label: "Allowed" },
  { id: "d", kind: "data", data_role: "dataset", label: "Files" },
  { id: "z", kind: "action", layer: "business", label: "Show file" },
];
const rawEdges = [
  {
    id: "af",
    from: "a",
    to: "f",
    type: "data",
    code_relation: "maps",
    origin: "code-index",
  },
  { id: "fr", from: "f", to: "r", type: "guard" },
  { id: "rd", from: "r", to: "d", type: "data" },
  { id: "dz", from: "d", to: "z", type: "flow" },
];
function graphOf(ns = nodes, es = rawEdges) {
  const boxes = ns.map((node) => ({
    id: node.id,
    node,
    type: visualType(node),
    kids: [],
    x: 0,
    y: 0,
    w: 190,
    h: 135,
  }));
  return {
    all: new Map(ns.map((node) => [node.id, node])),
    boxes,
    byId: new Map(boxes.map((b) => [b.id, b])),
    rawEdges: es,
    edges: es,
    regions: [],
  };
}
const graph = graphOf(),
  original = JSON.stringify({ nodes, rawEdges });
assert.equal(layerOf(nodes[1]), "implementation");
assert.equal(layerOf({ kind: "function", origin: "source-ast" }), "implementation");
assert.equal(implementationFacet({ code_role: "file" }), "project");
assert.equal(layerOf({ kind: "data", execution_role: "resource" }), "state");
assert.equal(layerOf({ kind: "decision", execution_role: "join" }), "state");
assert.equal(layerOf({ kind: "data", origin: "policy-definition" }), "rules");
assert.equal(classifyNode({ kind: "mystery" }).diagnostic, "Unclassified node");
assert.equal(visualType({ code_role: "mystery" }), "unknown");
assert.equal(
  visualType({ kind: "action" }),
  "function",
  "A declared technical action remains valid",
);
for (const facet of ["execution", "code", "api", "project", "operations"]) {
  const prior = {
    order: ["rules", facet, "business"],
    orderMode: "custom",
    visible: ["business", facet],
  };
  const next = cleanLayers(prior);
  assert.equal(next.facets.join(), facet);
  assert.deepEqual(next.order.slice(0, 3), ["rules", "implementation", "business"]);
  assert.deepEqual(cleanLayers(next), next);
  assert.deepEqual(cleanLayers({ visible: savedLayerVisibility(next) }).facets, [facet]);
}
for (const id of ["business", "states", "rules", "implementation", "project", "api", "data-access"])
  assert.ok(profileFor(id).nodes.length, id);
const filters = cleanFilters();
const field = {
  id: "field:f:out:answer",
  kind: "data",
  field: "answer",
  event_node: "f",
};
assert.equal(filterNode(field, new Map([[field.id, field]]), filters), false);
assert.equal(filterNode(field, new Map([[field.id, field]]), emptyFilters()), true);
assert.equal(
  filterNode(field, new Map([[field.id, field]]), {
    ...filters,
    promotedFields: [field.id],
  }),
  true,
);
assert.match(
  captureDetailRows({ capture: { out: { answer: "number" } } }, { outputs: { answer: 42 } })[0]
    .text,
  /42/,
);
const inventory = graphInventory({
  model: {
    nodes: [{ ...nodes[1], capture: { out: { answer: "number" } } }],
    edges: [],
    machine: { values: [], transitions: [] },
  },
  machine: {},
  manifest: { bindings: {} },
});
assert.ok(inventory.all.has(field.id), "Default presentation does not delete captured fields");

const oldPlanes = [
  "business",
  "state",
  "rules",
  "api",
  "execution",
  "project",
  "code",
  "operations",
  "data",
];
for (let mask = 0; mask < 512; mask++) {
  const config = cleanLayers({
    visible: oldPlanes.filter((_, i) => mask & (1 << i)),
  });
  const accepts = (n) =>
    config.visible.includes(layerOf(n)) &&
    (layerOf(n) !== "implementation" || config.facets.includes(implementationFacet(n)));
  const result = layerSlice(graph, config);
  const visible = nodes.filter(accepts).map((n) => n.id);
  assert.deepEqual(
    result.boxes.map((b) => b.id),
    visible,
  );
  for (let i = 0; i < nodes.length; i++) {
    if (!accepts(nodes[i])) continue;
    let j = i + 1;
    while (j < nodes.length && !accepts(nodes[j])) j++;
    if (j >= nodes.length) continue;
    const found = result.edges.filter((e) => e.from === nodes[i].id && e.to === nodes[j].id);
    assert.equal(found.length, 1, "Exactly the next visible boundary is connected");
    assert.equal(!!found[0].derived, j > i + 1);
  }
}
let reduced = layerSlice(graph, { visible: ["business", "data"] });
assert.deepEqual(reduced.edges.find((e) => e.derived).witnesses[0].edges, ["af", "fr", "rd"]);
assert.equal(reduced.edges.find((e) => e.derived).observed, false);
assert.ok(relationStyle(reduced.edges.find((e) => e.derived)).dash.length);
assert.deepEqual(
  transferEdges(
    {
      id: "e",
      node: "d",
      phase: "return",
      depends: [{ event: "p", type: "data" }],
    },
    [{ id: "p", node: "a" }],
    reduced.edges.filter((e) => e.derived),
    graph.all,
  ),
  [],
);
for (const exclusions of [
  { hiddenNodes: ["f"] },
  { hiddenEdges: ["fr"] },
  { edgeTypes: ["code-maps", "data", "flow"] },
  { nodeAllowed: (n) => n.id !== "r" },
])
  assert.equal(
    layerSlice(graph, { visible: ["business", "data"] }, exclusions).edges.filter((e) => e.derived)
      .length,
    0,
  );
assert.equal(
  layerSlice(graph, { visible: ["business"] }).edges[0].to,
  "z",
  "Same-plane endpoints work through hidden concerns",
);
const direct = { id: "ad", from: "a", to: "d", type: "call" };
reduced = layerSlice(graphOf(nodes, [...rawEdges, direct]), {
  visible: ["business", "data"],
});
assert.equal(reduced.edges.filter((e) => e.from === "a" && e.to === "d").length, 2);
assert.ok(reduced.edges.some((e) => e.id === "ad" && !e.derived));
const bounded = projectHiddenPaths(graph, {
  visibleIds: new Set(["a", "d"]),
  accepts: (n) => ["a", "d"].includes(n.id),
  maxWork: 1,
});
assert.equal(bounded.search_complete, false);
const cyclic = graphOf(nodes, [...rawEdges, { id: "rf", from: "r", to: "f", type: "call" }]);
assert.ok(layerSlice(cyclic, { visible: ["business", "data"] }).projection.work < 30);
const changed = graphOf(
  nodes,
  rawEdges.map((e) => (e.id === "fr" ? { ...e, conditions: ["fresh"] } : e)),
);
assert.notEqual(
  layerSlice(changed, { visible: ["business", "data"] }).projection.graph_revision,
  reduced.projection.graph_revision,
);
assert.equal(JSON.stringify({ nodes, rawEdges }), original);

// A large hidden hub cannot trigger an unbounded transitive-closure expansion.
const many = Array.from({ length: 10000 }, (_, i) => ({
  id: "n" + i,
  kind: "function",
}));
const chain = many
  .slice(1)
  .map((n, i) => ({ id: "e" + i, from: many[i].id, to: n.id, type: "call" }));
const large = graphOf(
  [nodes[0], ...many, nodes[3]],
  [
    { id: "entry", from: "a", to: "n0", type: "call" },
    ...chain,
    { id: "end", from: "n9999", to: "d", type: "writes" },
  ],
);
const started = performance.now();
const limited = layerSlice(large, { visible: ["business", "data"] });
assert.equal(limited.projection.search_complete, false);
assert.ok(limited.projection.work <= 25001);
console.log(
  JSON.stringify({
    passed: true,
    subsets: 512,
    planes: layers.map((l) => l.id),
    large_ms: performance.now() - started,
    large_work: limited.projection.work,
  }),
);
