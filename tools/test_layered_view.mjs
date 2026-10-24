import { sourceLines } from "../skills/vibelens/assets/stategraph-viewer/source-view.js";
import assert from "node:assert/strict";
import {
  captureFields,
  capturedValue,
  nodeExplanation,
} from "../skills/vibelens/assets/stategraph-viewer/capture-fields.js";
import { dataLines } from "../skills/vibelens/assets/stategraph-viewer/data-layer.js";
import {
  cleanLayers,
  layerSlice,
  layerOf,
} from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
import {
  spatialModel,
  containmentVolumes,
} from "../skills/vibelens/assets/stategraph-viewer/spatial-model.js";
import { solveSpatial } from "../skills/vibelens/assets/stategraph-viewer/spatial-layout.js";
import {
  runtimeOwners,
  mergeGraph,
} from "../skills/vibelens/assets/stategraph-viewer/graph-links.js";
import {
  relationStyle,
  emptyFilters,
  presentationGraph,
  refreshHierarchy,
} from "../skills/vibelens/assets/stategraph-viewer/layout.js";

assert.equal(layerOf({ kind: "wait" }), "state");
assert.equal(layerOf({ kind: "function", execution_role: "join" }), "rules");
assert.equal(layerOf({ kind: "function", execution_role: "resource" }), "rules");
const owner = {
  id: "tx",
  label: "Publish transaction",
  data_role: "query",
  capture: {
    in: { parameters: { picture: { id: "number" } } },
    out: {
      status: "string",
      committed: "boolean",
      duration_ms: "number",
      targets: ["string"],
      result: {},
    },
  },
};
const fields = captureFields(owner);
assert.equal(fields.nodes.find((n) => n.field === "duration_ms").analysis_level, "advanced");
assert.equal(fields.nodes.find((n) => n.field === "status").analysis_level, undefined);
const picture = fields.nodes.find((n) => n.label === "picture"),
  id = fields.nodes.find((n) => n.label === "id");
assert.equal(id.parent, picture.id);
assert.deepEqual(capturedValue(id, { parameters: { picture: { id: 7 } } }), {
  present: true,
  value: 7,
});
assert.equal(capturedValue(id, { parameters: { picture: {} } }).present, false);
assert.match(
  nodeExplanation(id, new Map([[owner.id, owner]])).join(" "),
  /inputs.parameters.picture.id/,
);
assert.match(nodeExplanation(id, new Map([[owner.id, owner]])).join(" "), /collection owner/);
const database = {
  data_role: "dataset",
  data_origin: "database",
  data_coverage: "complete",
  data_metadata: { kind: "table", status: "matched" },
};
assert.doesNotMatch(
  dataLines(database)
    .map((r) => r.text)
    .join(" "),
  /Actual structure|Complete scope|matches/,
);
assert.match(
  dataLines(database, {}, {}, false, true)
    .map((r) => r.text)
    .join(" "),
  /Actual structure/,
);
for (const type of [
  "call",
  "data",
  "reads",
  "writes",
  "transforms",
  "code-calls",
  "code-parameter",
])
  assert.equal(relationStyle({ type }).dash.length, 0, type);
for (const type of ["guard", "flow", "transition", "maps", "references", "contains"])
  assert.ok(relationStyle({ type }).dash.length, type);
assert.equal(relationStyle(fields.edges[0]).label, "Recorded field");
assert.ok(relationStyle(fields.edges[0]).dash.length);

const nodes = [
  { id: "publish", kind: "action", layer: "business", label: "Publish" },
  { id: "fn", kind: "function", parent: "publish", label: "Store" },
  { id: "state", kind: "state", layer: "state", label: "Published" },
];
const boxes = nodes.map((node, i) => ({
  id: node.id,
  node,
  type: i === 0 ? "business" : i === 1 ? "function" : "state",
  x: i * 260,
  y: i * 50,
  w: 190,
  h: 135,
  kids: i === 0 ? ["fn"] : [],
  open: i === 0,
}));
const rawEdges = [{ id: "calls", from: "publish", to: "fn", type: "call" }];
const graph = {
  all: new Map(nodes.map((n) => [n.id, n])),
  boxes,
  byId: new Map(boxes.map((b) => [b.id, b])),
  edges: rawEdges,
  rawEdges,
  children: new Map([["publish", ["fn"]]]),
};
refreshHierarchy(graph);
const before = JSON.stringify(graph.boxes);
assert.equal(layerSlice(graph, { enabled: false }), graph);
const model = spatialModel(graph, presentationGraph(graph, emptyFilters()));
const positions = solveSpatial({ ...model, gap: 260 });
assert.equal(JSON.stringify(graph.boxes), before, "3D coordinates cannot mutate 2D preferences");
assert.notEqual(positions.fn.y, positions.publish.y);
assert.notEqual(positions.fn.z, positions.publish.z);
assert.ok(Object.values(positions).every((p) => [p.x, p.y, p.z].every(Number.isFinite)));
const volumes = containmentVolumes(model, positions, 260);
assert.ok(volumes.some((v) => v.id === "publish" && v.layer === "execution" && v.projection));
const saved = { ...positions, fn: { ...positions.fn, x: 712, z: 231, pinned: true } };
assert.equal(solveSpatial({ ...model, positions: saved, gap: 260, arrange: true }).fn.x, 712);
assert.equal(solveSpatial({ ...model, positions: saved, gap: 260 }).fn.z, 231);
const merged = mergeGraph(
  { nodes: [{ id: "a" }], edges: [] },
  {
    nodes: [
      { id: "f", code_role: "function" },
      { id: "p", code_role: "parameter", parent: "f" },
      { id: "api", code_role: "endpoint" },
    ],
    edges: [
      { id: "map", from: "a", to: "f", code_relation: "maps" },
      { id: "handle", from: "api", to: "f", code_relation: "handles" },
    ],
  },
);
assert.deepEqual(runtimeOwners(merged, "p"), ["a"]);
assert.deepEqual(runtimeOwners(merged, "api"), ["a"]);
assert.equal(mergeGraph(merged, { nodes: [], edges: merged.edges }).edges.length, 2);
const single = layerSlice(graph, cleanLayers({ enabled: true, only: "execution" }));
assert.deepEqual(
  single.boxes.map((b) => b.id),
  ["fn"],
);
assert.equal(single.edges.length, 0);
assert.equal(cleanLayers({ gap: NaN, camera: "__proto__" }).camera, "angled");
console.log(
  "PASS: capture provenance, nested values, quiet captions, edge meaning, real 3D layout, containment projections, stable positions and cross-layer runtime anchors.",
);

const file = "// rows in a comment\nfunction f(rows, other) { return rows; }\n// end of full file";
const marked = sourceLines(file, {
  selection: { line: 2, column: 11, end_line: 2, end_column: 15 },
});
assert.equal(marked.length, 3);
assert.equal(marked[1].parts.find((p) => p.marked).text, "rows");
assert.equal(marked[0].active, false);
assert.equal(marked[2].text, "// end of full file");
