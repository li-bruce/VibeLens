/** Real bundled ELK regression: typed routes, compound groups and shared XY/XZ. */
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { performance } from "node:perf_hooks";
import {
  calculateLayout,
  emptyLayout,
  applyLayout,
  conceptExpansion,
  placeIncremental,
} from "../skills/vibelens/assets/stategraph-viewer/layout.js";
import { conceptOrderEdges } from "../skills/vibelens/assets/stategraph-viewer/concept-flow-layout.js";
import { planarSeeds } from "../skills/vibelens/assets/stategraph-viewer/spatial-model.js";
import { solveSpatial } from "../skills/vibelens/assets/stategraph-viewer/spatial-layout.js";

const sandbox = { module: { exports: {} }, console, setTimeout, clearTimeout };
sandbox.exports = sandbox.module.exports;
vm.createContext(sandbox);
vm.runInContext("global = this;", sandbox);
vm.runInContext(
  fs.readFileSync(
    "skills/vibelens/assets/stategraph-viewer/elk.bundled.js",
    "utf8",
  ),
  sandbox,
);
vm.runInContext("elk = new module.exports();", sandbox);
const elk = {
  layout(input) {
    sandbox.inputJson = JSON.stringify(input);
    return vm.runInContext("elk.layout(JSON.parse(inputJson))", sandbox);
  },
};

function graphFor(ids, pairs, layer = "business", contained = false) {
  const nodes = ids.map((id) => ({
    id,
    label: id,
    kind:
      layer === "state" ? "state" : layer === "rules" ? "decision" : "action",
    layer,
    ...(contained ? { parent: "group" } : {}),
  }));
  if (contained)
    nodes.unshift({ id: "group", label: "Workflow", kind: "action", layer });
  const boxes = nodes.map((node) => ({
    id: node.id,
    node,
    type: layer,
    x: 0,
    y: 0,
    w: 150,
    h: 80,
  }));
  const edges = pairs.map(([from, to, type], i) => ({
    id: "edge:" + i,
    from,
    to,
    type:
      type ||
      (layer === "state" ? "transition" : layer === "rules" ? "guard" : "flow"),
  }));
  return {
    boxes,
    edges,
    byId: new Map(boxes.map((box) => [box.id, box])),
    all: new Map(nodes.map((node) => [node.id, node])),
  };
}

const report = [];
async function verify(
  name,
  graph,
  { cycle = false, state = emptyLayout() } = {},
) {
  const original = JSON.stringify({
    nodes: [...graph.all.values()],
    edges: graph.edges,
  });
  const started = performance.now();
  const positions = await calculateLayout(elk, graph, state, "cluster");
  const elapsed_ms = Math.round(performance.now() - started);
  assert.equal(Object.keys(positions).length, graph.boxes.length);
  for (const point of Object.values(positions))
    assert.ok(Number.isFinite(point.x) && Number.isFinite(point.y));
  const backward = conceptOrderEdges(graph).filter(
    (edge) => positions[edge.from].x >= positions[edge.to].x,
  );
  if (!cycle)
    assert.equal(
      backward.length,
      0,
      name + ": " + backward.map((edge) => edge.id),
    );
  assert.equal(
    JSON.stringify({ nodes: [...graph.all.values()], edges: graph.edges }),
    original,
  );
  const again = await calculateLayout(elk, graph, state, "cluster");
  assert.deepEqual(again, positions, "identical graph must be deterministic");
  applyLayout(graph, state, positions);
  for (const region of graph.regions)
    assert.ok(Number.isFinite(region.radius) && region.radius > 0);
  const planar = planarSeeds(graph, positions);
  const spatial = solveSpatial({
    nodes: graph.boxes.map((box) => ({ id: box.id, layer: box.node.layer })),
    edges: graph.edges,
    layers: [...new Set(graph.boxes.map((box) => box.node.layer))].map(
      (id) => ({ id }),
    ),
    gap: 240,
    planar,
    arrange: true,
  });
  for (const [id, point] of Object.entries(planar)) {
    assert.equal(spatial[id].x, point.x);
    assert.equal(spatial[id].z, point.z);
    assert.ok(Number.isFinite(spatial[id].y));
  }
  report.push({
    name,
    nodes: graph.boxes.length,
    edges: graph.edges.length,
    elapsed_ms,
    backward: backward.length,
  });
  return { positions, state };
}

const ids = Array.from(
  { length: 12 },
  (_, i) => `step-${String(i).padStart(2, "0")}`,
);
const chain = ids.slice(1).map((id, i) => [ids[i], id]);
await verify("chain", graphFor(ids, chain));
const nested = graphFor(ids, chain, "business", true);
await verify("expanded-chain", nested);
await verify(
  "shared-fork-join",
  graphFor(
    ["a", "b", "c", "d", "e", "f"],
    [
      ["a", "b"],
      ["b", "c"],
      ["b", "d"],
      ["c", "e"],
      ["d", "e"],
      ["e", "f"],
    ],
  ),
);
await verify(
  "state-cycle",
  graphFor(
    ["idle", "running", "done"],
    [
      ["idle", "running"],
      ["running", "done"],
      ["done", "idle"],
    ],
    "state",
  ),
  { cycle: true },
);
await verify(
  "shared-rule",
  graphFor(
    ["fact", "predicate", "decisionA", "decisionB"],
    [
      ["fact", "predicate"],
      ["predicate", "decisionA"],
      ["predicate", "decisionB"],
    ],
    "rules",
  ),
);
const businessContext = graphFor(
  ["a", "b", "guard"],
  [
    ["a", "b"],
    ["guard", "a", "guard"],
  ],
);
assert.equal(
  conceptOrderEdges(businessContext).length,
  1,
  "business guards are not sequence",
);
const inverted = graphFor(
  ["fact", "decision"],
  [["decision", "fact", "depends_on"]],
  "rules",
);
assert.equal(conceptOrderEdges(inverted)[0].from, "fact");
await verify("dependency-orientation", inverted);
const mixedParts = [
  graphFor(
    ["b0", "b1", "b2"],
    [
      ["b0", "b1"],
      ["b1", "b2"],
    ],
  ),
  graphFor(
    ["s0", "s1", "s2"],
    [
      ["s0", "s1"],
      ["s1", "s2"],
    ],
    "state",
  ),
  graphFor(
    ["r0", "r1", "r2"],
    [
      ["r0", "r1"],
      ["r1", "r2"],
    ],
    "rules",
  ),
];
const mixed = {
  boxes: mixedParts.flatMap((part) => part.boxes),
  edges: mixedParts.flatMap((part, i) =>
    part.edges.map((edge) => ({ ...edge, id: `${i}:${edge.id}` })),
  ),
  byId: new Map(mixedParts.flatMap((part) => [...part.byId])),
  all: new Map(mixedParts.flatMap((part) => [...part.all])),
};
await verify("three-concept-planes", mixed);
const pinned = graphFor(ids, chain, "business", true),
  state = emptyLayout();
state.positions[ids[3]] = { x: 150, y: 320, pinned: true };
state.positions[ids[8]] = { x: 800, y: 320, pinned: true };
const pinResult = await calculateLayout(elk, pinned, state, "cluster");
assert.deepEqual(pinResult[ids[3]], state.positions[ids[3]]);
assert.deepEqual(pinResult[ids[8]], state.positions[ids[8]]);
const freshState = emptyLayout();
freshState.positions.group = { x: 700, y: 400, pinned: true };
placeIncremental(nested, freshState);
const opened = await conceptExpansion(
  elk,
  nested,
  freshState,
  "group",
  new Set(["group"]),
);
assert.ok(opened[ids[11]].x > opened[ids[0]].x);
assert.equal(opened.group, undefined);
const largeIds = Array.from(
  { length: 960 },
  (_, i) => `route-${Math.floor(i / 12)}-step-${i % 12}`,
);
const largeEdges = largeIds.flatMap((id, i) =>
  i % 12 < 11 ? [[id, largeIds[i + 1]]] : [],
);
await verify("80-routes-960-nodes", graphFor(largeIds, largeEdges));
assert.ok(
  report.at(-1).elapsed_ms < 30000,
  "layout exceeded the worker deadline",
);
if (process.env.BO_FLOW_REPORT)
  fs.writeFileSync(
    process.env.BO_FLOW_REPORT,
    JSON.stringify(report, null, 2) + "\n",
  );
console.log(JSON.stringify(report, null, 2));
