/** Folded nodes cannot change the layer or identity of a real relation. */
import assert from "node:assert/strict";
import { layoutGraph } from "../skills/vibelens/assets/stategraph-viewer/graph-core.js";
import { graphInventory } from "../skills/vibelens/assets/stategraph-viewer/graph-inventory.js";
import { namedView } from "../skills/vibelens/assets/stategraph-viewer/graph-names.js";
import {
  layerSlice,
  displayChildren,
} from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
import { sameBoundRelation } from "../skills/vibelens/assets/stategraph-viewer/bound-relations.js";
import {
  relationIds,
  relationExcluded,
  originalRelations,
} from "../skills/vibelens/assets/stategraph-viewer/edge-identities.js";
import {
  emptyFilters,
  placeIncremental,
  setPosition,
  settleExpansion,
  presentationGraph,
} from "../skills/vibelens/assets/stategraph-viewer/layout.js";
import { fitVisibleHierarchy } from "../skills/vibelens/assets/stategraph-viewer/containment-view.js";
import { spatialModel } from "../skills/vibelens/assets/stategraph-viewer/spatial-model.js";
import { transferEdges } from "../skills/vibelens/assets/stategraph-viewer/recording.js";

// Static product previews can provide boxes without the runtime inventory.
// Their counts still use the shared helper and respect an explicit empty slice.
const preview = { boxes: [{ id: "group", kids: ["child"] }] };
assert.deepEqual(displayChildren(preview, "group"), ["child"]);
assert.deepEqual(displayChildren({ ...preview, expansionChildren: new Map() }, "group"), []);
assert.deepEqual(displayChildren(undefined, "group"), []);

const native = {
  id: "upload-share",
  from: "upload",
  to: "share",
  type: "flow",
  label: "Choose recipient",
  evidence: "Confirmed dialogue",
};
const concept = {
  id: "concept-relation:upload-share",
  from: "upload",
  to: "share",
  type: "flow",
  label: "Choose recipient",
  origin: "concept-design",
  evidence_kind: "conceptual",
  source_refs: ["answer:share"],
};
const view = {
  model: {
    nodes: [
      { id: "root", kind: "action", layer: "business" },
      { id: "upload", kind: "action", layer: "business", parent: "root" },
      { id: "share", kind: "action", layer: "business", parent: "root" },
      { id: "revoke", kind: "action", layer: "business", parent: "root" },
      {
        id: "connect",
        kind: "function",
        layer: "execution",
        parent: "upload",
        source: { path: "app.py", symbol: "connect" },
      },
      { id: "table", kind: "data", data_role: "dataset", layer: "data" },
    ],
    edges: [
      native,
      {
        id: "static-read",
        from: "revoke",
        to: "connect",
        type: "flow",
        origin: "source-ast",
        callsite: { line: 20 },
      },
      { id: "access", from: "connect", to: "table", type: "writes" },
    ],
    machine: { values: [], transitions: [] },
  },
  concept_structure: {
    nodes: [],
    edges: [concept],
    stage: "bound",
    relation_occurrences: { "upload-share": concept.id },
  },
  machine: { configurations: [], journal: [] },
  manifest: { build_id: "fixture", bindings: {} },
  authority: { basis: {}, parameters: {} },
  binding_status: { status: "current" },
  events: [],
};
const original = JSON.stringify(view);
const inventory = graphInventory(view);
const single = inventory.rawEdges.find((e) => e.id === native.id);
assert.equal(inventory.rawEdges.filter((e) => e.from === "upload" && e.to === "share").length, 1);
assert.deepEqual(relationIds(single).sort(), [native.id, concept.id].sort());
assert.equal(originalRelations(single)[1].source_refs[0], "answer:share");
for (const id of [native.id, concept.id]) assert.equal(relationExcluded(single, [id]), true);
for (const explained of [false, true]) {
  const edges = graphInventory(namedView(view, explained)).rawEdges;
  assert.equal(
    edges.filter((e) => e.from === "upload" && e.to === "share").length,
    1,
    "Names do not determine identity",
  );
}
// Equal text/endpoints do not merge distinct assertions, calls, conditions or scopes.
for (const change of [
  { type: "call" },
  { from: "revoke" },
  { to: "revoke" },
  { conditions: ["owner"] },
  { unless: ["owner"] },
  { arguments: { file: "other" } },
  { scope: "another-request" },
  { callsite: { line: 21 } },
  { future_semantic_field: "unknown" },
  { origin: "source-ast" },
])
  assert.equal(sameBoundRelation(concept, { ...native, ...change }), false, JSON.stringify(change));
const parallel = structuredClone(view);
parallel.model.edges.push({ ...native, id: "another-business-relation" });
assert.equal(
  graphInventory(parallel).rawEdges.filter((e) => e.from === "upload" && e.to === "share").length,
  2,
);
const missingProof = structuredClone(view);
delete missingProof.concept_structure.relation_occurrences;
assert.equal(
  graphInventory(missingProof).rawEdges.filter((e) => e.from === "upload" && e.to === "share")
    .length,
  2,
);

const positions = {
  root: { x: 0, y: 0 },
  upload: { x: 50, y: 50 },
  share: { x: 200, y: 50 },
  revoke: { x: 200, y: 110 },
  connect: { x: 900, y: 900 },
  table: { x: 1400, y: 600 },
};
function display(
  expanded,
  visible = ["business"],
  state = { positions: structuredClone(positions) },
  input = view,
) {
  const graph = layoutGraph(input, new Set(expanded));
  placeIncremental(graph, state);
  const sliced = layerSlice(graph, { visible });
  const result = fitVisibleHierarchy(sliced, presentationGraph(sliced, emptyFilters()));
  return { ...result, complete: graph, state };
}
const closed = display(["root"]),
  opened = display(["root", "upload"]);
const edgeSignature = (result) =>
  result.presentation.edges.map((e) => [e.from, e.to, e.type, ...e.members.map((m) => m.id)]);
assert.deepEqual(
  edgeSignature(opened),
  edgeSignature(closed),
  "Hidden function calls cannot appear/disappear as business calls",
);
assert.equal(closed.presentation.edges.length, 1);
assert.equal(
  closed.presentation.edges[0].members.length,
  1,
  "One bound business assertion, no false x2",
);
assert.deepEqual(
  displayChildren(closed.graph, "upload"),
  [],
  "Hidden children do not advertise a useless expansion",
);
assert.deepEqual(
  displayChildren(closed.graph, "root").sort(),
  ["upload", "share", "revoke"].sort(),
);
assert.equal(
  spatialModel(closed.graph, closed.presentation).edges.length,
  1,
  "3D shares the same edge projection",
);
assert.ok(!opened.presentation.glyphs.has("connect"));
// Actual hidden-layer paths still exist and disclose their original witness.
const data = display(["root"], ["business", "data"]);
const indirect = data.presentation.edges.find(
  (e) => e.from === "revoke" && e.to === "table" && e.derived,
);
assert.ok(indirect);
assert.deepEqual(indirect.members[0].witness.nodes, ["revoke", "connect", "table"]);
assert.equal(indirect.observed, false);
const all = display(["root", "upload"], ["business", "symbols", "data"]);
assert.ok(
  all.presentation.edges.some((e) => e.from === "revoke" && e.to === "connect"),
  "Actual source endpoints reappear when their layer is shown",
);
assert.deepEqual(displayChildren(all.graph, "upload"), ["connect"]);

// Opening a node is not an Arrange request. Close neighbors keep their saved
// coordinates, including unpinned edits and hidden descendants after a drag.
const saved = structuredClone(positions),
  known = new Set(Object.keys(saved));
const moved = display(["root"], ["business", "symbols", "data"], { positions: saved });
setPosition(moved.complete, moved.state, "upload", 120, 85);
assert.equal(moved.state.positions.connect.x, 970);
assert.equal(moved.state.positions.connect.y, 935);
const beforeOpen = JSON.stringify(moved.state.positions);
for (let i = 0; i < 4; i++) {
  const round = display(["root", "upload"], ["business", "symbols", "data"], moved.state);
  settleExpansion(round.graph, round.state, "upload", known);
  assert.equal(
    JSON.stringify(round.state.positions),
    beforeOpen,
    "Reopening does not rearrange saved siblings",
  );
}
// A grandchild on a displayed layer remains expandable through a hidden parent.
const nested = structuredClone(view);
nested.model.nodes.push({
  id: "state",
  kind: "state",
  layer: "state",
  value: "ready",
  parent: "connect",
});
const nestedResult = display(["root"], ["business", "state"], undefined, nested);
assert.deepEqual(displayChildren(nestedResult.graph, "upload"), ["state"]);

// Recorded dependencies still select the one visible line under either ID.
const actualEvents = [
  { id: "a", node: "upload", phase: "read", depends: [] },
  { id: "b", node: "share", phase: "read", depends: [{ event: "a", type: "control" }] },
];
assert.equal(
  transferEdges(actualEvents[1], actualEvents, closed.presentation.edges, closed.complete.all)
    .length,
  1,
);
assert.equal(JSON.stringify(view), original, "Canonical declarations and events are unchanged");
console.log(
  "PASS: scoped folding, stable expansion, bound relation identity, original aliases and 2D/3D parity.",
);
