/** Concept definitions and their source bindings survive every view projection. */
import assert from "node:assert/strict";
import { graphInventory } from "../skills/vibelens/assets/stategraph-viewer/graph-inventory.js";
import {
  layoutGraph,
  relationType,
} from "../skills/vibelens/assets/stategraph-viewer/graph-core.js";
import { profileFor, matchingNodes } from "../skills/vibelens/assets/stategraph-viewer/analysis.js";
import { layerOf, layerSlice } from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
import { visualType } from "../skills/vibelens/assets/stategraph-viewer/graph-classification.js";
import {
  emptyFilters,
  cleanFilters,
  refreshHierarchy,
  presentationGraph,
  renderRevision,
  relationStyle,
} from "../skills/vibelens/assets/stategraph-viewer/layout.js";
import {
  graphVersion,
  recordingMatches,
} from "../skills/vibelens/assets/stategraph-viewer/view-lifecycle.js";
import { buildTraceIndex } from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import { frame, timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";

const concept = (id, layer, conceptKind, kind) => ({
  id,
  label: id,
  layer,
  concept_kind: conceptKind,
  kind,
  origin: "concept-design",
  capture: {},
});
const nodes = [
  concept("share", "business", "action", "action"),
  concept("object:grant", "business", "object", "data"),
  concept("event:share", "state", "event", "data"),
  concept("transition:grant", "state", "transition", "action"),
  concept("state:active", "state", "state", "state"),
  concept("decision:share", "rules", "rule_operation", "decision"),
  concept("fact:owner", "rules", "fact", "data"),
];
const edge = (id, from, to, type) => ({
  id,
  from,
  to,
  type,
  label: type,
  origin: "concept-design",
  evidence_kind: "conceptual",
});
const edges = [
  edge("request", "share", "event:share", "action_requests_event"),
  edge("trigger", "event:share", "transition:grant", "requests_transition"),
  edge("guard", "transition:grant", "decision:share", "transition_guarded_by"),
  edge("read", "decision:share", "fact:owner", "decision_reads_fact"),
  edge("target", "transition:grant", "state:active", "declares_target"),
  edge("fact", "object:grant", "fact:owner", "describes_fact"),
];
const native = {
  id: "source:share",
  label: "share_file",
  kind: "function",
  source: { path: "sharing.py", symbol: "share_file" },
};
const view = {
  model: {
    nodes: [native],
    edges: [],
    machine: { values: [], transitions: [] },
  },
  concept_structure: {
    nodes,
    edges: [
      ...edges,
      {
        id: "binding",
        from: "share",
        to: native.id,
        type: "maps",
        origin: "concept-binding",
        mapping_role: "implements",
      },
    ],
    revision: "confirmed-1",
  },
  manifest: { build_id: "build-1", model_hash: "native-1", bindings: {} },
  machine: { configurations: [], journal: [] },
  events: [],
  authority: { parameters: {}, basis: {} },
  binding_status: { status: "current" },
};
const before = JSON.stringify(view);
const inventory = graphInventory(view);
assert.equal(inventory.all.size, 8);
assert.equal(inventory.rawEdges.length, 7);
for (const node of nodes) assert.equal(layerOf(node), node.layer, node.id);
assert.equal(visualType(nodes.find((node) => node.id === "transition:grant")), "state");
for (const relation of edges) {
  assert.equal(relationType(relation), relation.type);
  assert.ok(emptyFilters().edges.includes(relation.type));
  assert.ok(relationStyle(relation).dash.length);
}
assert.ok(cleanFilters({ edges: ["other"] }).edges.includes("requests_transition"));
assert.deepEqual(cleanFilters({ edges: ["call"] }).edges, ["call"]);
for (const [preset, concern] of [
  ["business", "business"],
  ["states", "state"],
  ["rules", "rules"],
]) {
  const profile = profileFor(preset);
  const graph = layoutGraph(
    view,
    new Set(nodes.map((node) => node.id)),
    new Set(),
    new Map(),
    "latest",
    "latest",
    {
      match: (all, events, status, relations) =>
        matchingNodes(all, view, events, profile, status, relations),
    },
  );
  refreshHierarchy(graph);
  const shown = presentationGraph(graph, profile);
  for (const node of nodes.filter((node) => node.layer === concern))
    assert.ok(shown.glyphs.has(node.id), preset + " preserves " + node.id);
  for (const relation of edges.filter((relation) =>
    [relation.from, relation.to].every(
      (id) => nodes.find((node) => node.id === id)?.layer === concern,
    ),
  ))
    assert.ok(
      shown.edges.some((drawn) => drawn.members.some((member) => member.id === relation.id)),
      "Typed peer relationship remains visible: " + relation.id,
    );
}
const graph = layoutGraph(view);
const slice = layerSlice(graph, { visible: ["business", "rules"] });
const path = slice.edges.find(
  (relation) => relation.derived && relation.from === "share" && relation.to === "decision:share",
);
assert.deepEqual(path.witnesses[0].types, [
  "action_requests_event",
  "requests_transition",
  "transition_guarded_by",
]);
assert.equal(path.observed, false);
assert.equal(relationType(path), "indirect");
refreshHierarchy(slice);
assert.ok(
  presentationGraph(slice, {
    ...emptyFilters(),
    edges: ["indirect"],
  }).edges.some((relation) => relation.derived),
  "The indirect relation filter works after compound-edge projection",
);
assert.equal(
  layerSlice(graph, {
    visible: ["business", "rules"],
    projections: false,
  }).edges.some((relation) => relation.derived),
  false,
);
const changed = {
  ...view,
  concept_structure: { ...view.concept_structure, revision: "confirmed-2" },
};
assert.notEqual(graphVersion(changed), graphVersion(view));
assert.notEqual(renderRevision(changed), renderRevision(view));
const recording = {
  id: "r",
  status: "stopped",
  context: view,
  final: { machine: view.machine },
  events: [],
  commands: [],
  started_at: "2026-11-04T00:00:00Z",
  ended_at: "2026-11-04T00:00:01Z",
};
assert.equal(recordingMatches(recording, changed), false);
assert.equal(frame(recording, 0).concept_structure.revision, "confirmed-1");
const trace = buildTraceIndex(recording, timeline(recording), inventory.all);
assert.equal(
  [...trace.rows.values()].flatMap((row) => row.slices).length,
  0,
  "A design map creates no invocation or duration",
);
assert.equal(
  JSON.stringify(view),
  before,
  "All projections preserve source and concept identities",
);
console.log(
  "PASS: peer design views, typed crosslinks, source binding, indirect witnesses, revision isolation and no fabricated lifecycle.",
);
