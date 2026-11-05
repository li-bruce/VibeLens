/** Read-only diagnosis of the existing layout strategies on small directed graphs.
 * This probe measures horizontal direction, not visual acceptance or a new solver.
 * Run from any directory: node path/to/probe-layout.mjs
 */
import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { calculateLayout, emptyLayout } from "../../../skills/vibelens/assets/stategraph-viewer/layout.js";

const viewer = new URL("../../../skills/vibelens/assets/stategraph-viewer/", import.meta.url);
const sandbox = { module: { exports: {} }, console, setTimeout, clearTimeout };
sandbox.exports = sandbox.module.exports;
vm.createContext(sandbox);
vm.runInContext("global = this;", sandbox);
vm.runInContext(fs.readFileSync(new URL("elk.bundled.js", viewer), "utf8"), sandbox);
vm.runInContext("elk = new module.exports();", sandbox);
const elk = {
  layout(input) {
    sandbox.inputJson = JSON.stringify(input);
    return vm.runInContext("elk.layout(JSON.parse(inputJson))", sandbox);
  },
};

/** Use the viewer's actual graph input without injecting runtime evidence. */
function graphFor(ids, pairs, contained = false) {
  const nodes = ids.map((id) => ({
    id,
    label: id,
    layer: "business",
    kind: "action",
    ...(contained ? { parent: "network" } : {}),
  }));
  if (contained)
    nodes.unshift({ id: "network", label: "Workflow", layer: "business", kind: "action" });
  const boxes = nodes.map((node) => ({
    id: node.id,
    node,
    type: "business",
    x: 0,
    y: 0,
    w: 150,
    h: 80,
  }));
  const edges = pairs.map(([from, to], i) => ({ id: `flow-${i}`, from, to, type: "flow" }));
  if (contained)
    for (const id of ids)
      edges.push({ id: `contains-${id}`, from: "network", to: id, type: "contains" });
  return {
    boxes,
    edges,
    byId: new Map(boxes.map((box) => [box.id, box])),
    all: new Map(nodes.map((node) => [node.id, node])),
  };
}

/** Direction alone deliberately does not grade loops, routing, labels or groups. */
function measure(graph, positions) {
  const flow = graph.edges.filter((edge) => edge.type === "flow");
  const backward = flow.filter((edge) => positions[edge.to].x < positions[edge.from].x - 1);
  const level = flow.filter(
    (edge) => Math.abs(positions[edge.to].x - positions[edge.from].x) <= 1,
  );
  assert.equal(Object.keys(positions).length, graph.boxes.length);
  assert.ok(
    Object.values(positions).every((point) => Number.isFinite(point.x) && Number.isFinite(point.y)),
  );
  return {
    flow_edges: flow.length,
    backward_edges: backward.map((edge) => edge.id),
    nonadvancing_edges: level.map((edge) => edge.id),
    positions,
  };
}

const chain = Array.from({ length: 12 }, (_, i) => `step-${String(i + 1).padStart(2, "0")}`);
const pairs = chain.slice(1).map((id, i) => [chain[i], id]);
const fixtures = [
  { id: "flat-chain", graph: graphFor(chain, pairs) },
  { id: "expanded-chain", graph: graphFor(chain, pairs, true) },
  {
    id: "shared-prefix-branch-join",
    graph: graphFor(
      ["a-start", "b-check", "c-left", "d-right", "e-left-end", "f-right-end", "g-join", "h-end"],
      [
        ["a-start", "b-check"],
        ["b-check", "c-left"],
        ["b-check", "d-right"],
        ["c-left", "e-left-end"],
        ["d-right", "f-right-end"],
        ["e-left-end", "g-join"],
        ["f-right-end", "g-join"],
        ["g-join", "h-end"],
      ],
    ),
  },
];
const report = {
  scope: "Synthetic headless diagnosis of current cluster and layered strategies; no product changes or browser acceptance.",
  fixture_semantics: "Edges denote possible directed progression; the fork/join fixture does not assert XOR or AND semantics.",
  bundled_elk_version: "0.12.0",
  limitations: [
    "The existing layered strategy flattens input boxes, so its results are only a directional comparison, not a compound-layout solution.",
    "No actual application, branch conditions, cycle handling, labels, cross-layer routing or recorded execution was tested.",
  ],
  fixtures: [],
};
const knownOptions = await vm.runInContext("elk.knownLayoutOptions()", sandbox);
const candidates = [
  "org.eclipse.elk.hierarchyHandling",
  "org.eclipse.elk.partitioning.activate",
  "org.eclipse.elk.partitioning.partition",
  "org.eclipse.elk.layered.considerModelOrder.strategy",
  "org.eclipse.elk.layered.priority.direction",
  "org.eclipse.elk.layered.crossingMinimization.semiInteractive",
];
report.registered_options = Object.fromEntries(
  candidates.map((id) => [id, knownOptions.some((option) => option.id === id)]),
);
for (const { id, graph } of fixtures) {
  const original = JSON.stringify({ nodes: [...graph.all.values()], edges: graph.edges });
  const results = {};
  for (const algorithm of ["cluster", "layered"]) {
    const positions = await calculateLayout(elk, graph, emptyLayout(), algorithm);
    results[algorithm] = measure(graph, positions);
  }
  assert.equal(JSON.stringify({ nodes: [...graph.all.values()], edges: graph.edges }), original);
  report.fixtures.push({ id, nodes: graph.boxes.length, results });
}
fs.writeFileSync(new URL("layout-probe.json", import.meta.url), JSON.stringify(report, null, 2) + "\n");
console.log(
  JSON.stringify(
    report.fixtures.map(({ id, results }) => ({
      id,
      cluster_backward: results.cluster.backward_edges.length,
      cluster_level: results.cluster.nonadvancing_edges.length,
      layered_backward: results.layered.backward_edges.length,
      layered_level: results.layered.nonadvancing_edges.length,
      flow_edges: results.cluster.flow_edges,
    })),
    null,
    2,
  ),
);
