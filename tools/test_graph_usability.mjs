/** Layer identity, parallel lifetimes and explicit event nesting stay independent. */
import assert from "node:assert/strict";
import {
  layerPalette,
  defaultLayerOrder,
} from "../skills/vibelens/assets/stategraph-viewer/layer-style.js";
import { layers, layerColor } from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
import {
  packTracks,
  rowMetrics,
} from "../skills/vibelens/assets/stategraph-viewer/trace-tracks.js";
import { stepHierarchy } from "../skills/vibelens/assets/stategraph-viewer/step-hierarchy.js";
import { stateResidencies } from "../skills/vibelens/assets/stategraph-viewer/trace-residencies.js";
import { withCodeGraph } from "../skills/vibelens/assets/stategraph-viewer/code-layer.js";
import { configurationScopeMatches } from "../skills/vibelens/assets/stategraph-viewer/trace-evidence.js";
import { buildTraceIndex } from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import { timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";

assert.deepEqual(
  layers.map((layer) => layer.id),
  defaultLayerOrder,
);
assert.equal(new Set(layers.map((layer) => layer.color)).size, layers.length);
assert.equal(defaultLayerOrder.indexOf("data"), defaultLayerOrder.indexOf("operations") + 1);
for (const layer of layers) assert.equal(layer.color, layerPalette[layer.id]);
assert.equal(layerColor({ kind: "function", layer: "api" }), layerPalette.api);

const intervals = packTracks([
  { node: "pending", scope: "file:1", start: 0, end: 40 },
  { node: "pending", scope: "file:2", start: 2, end: 50 },
  { node: "approved", scope: "file:1", start: 40, end: 70 },
]);
assert.equal(intervals.trackCount, 2);
assert.equal(intervals.slices[0].track, intervals.slices[2].track);
for (const a of intervals.slices)
  for (const b of intervals.slices)
    if (a !== b && a.track === b.track) assert.ok(a.end <= b.start || b.end <= a.start);
assert.deepEqual(rowMetrics([intervals, { trackCount: 1 }]).heights, [50, 28]);

const all = new Map([
  ["flow", { id: "flow", kind: "action", layer: "business" }],
  ["api", { id: "api", kind: "function", layer: "api" }],
  ["value", { id: "value", kind: "data" }],
]);
const event = (id, node, phase, call, parent = null, extra = {}) => ({
  id,
  node,
  phase,
  call_id: call,
  parent_call_id: parent,
  run_id: "r",
  producer_id: "p",
  build_id: "b",
  kind: "probe",
  ...extra,
});
const events = [
  event("1", "flow", "enter", "root"),
  event("2", "api", "enter", "request", "root"),
  event("3", "value", "read", "field", "request"),
  event("4", "api", "return", "request"),
  event("5", "flow", "return", "root"),
  event("6", "api", "enter", "job", "root", { parent_event_id: "1" }),
];
const hierarchy = stepHierarchy(events, all);
assert.deepEqual(
  [...hierarchy.values()].map((entry) => entry.depth),
  [0, 1, 2, 1, 0, 1],
);
assert.equal(hierarchy.get(1).color, "#" + layerPalette.api.toString(16));
const foreign = stepHierarchy(
  [event("foreign", "api", "enter", "other", "root", { producer_id: "q" })],
  all,
  events.slice(0, 1),
);
assert.equal(foreign.get(0).depth, 0, "A matching call ID in another producer is not ancestry");
assert.ok(configurationScopeMatches({ attempt: "job:1" }, "attempt:job:1"));
assert.equal(configurationScopeMatches({ attempt: "application" }, "instance:r:file:1"), false);
assert.ok(configurationScopeMatches({ snapshot_instance: "r:file:1" }, "instance:r:file:1"));
const at = (ms) => new Date(Date.UTC(2026, 10, 2) + ms).toISOString();
const entry = { ...event("clipped-enter", "flow", "enter", "clipped"), observed_at: at(5) };
const completion = {
  ...event("clipped-exit", "flow", "return", "clipped"),
  observed_at: at(8),
  inputs: {},
  outputs: {},
};
const clipped = {
  id: "late-metadata",
  status: "stopped",
  build_id: "b",
  started_at: at(100),
  ended_at: at(101),
  events: [completion],
  commands: [],
  context: {
    model: { nodes: [all.get("flow")], edges: [], machine: {} },
    machine: {},
    events: [entry],
  },
  final: { machine: {} },
};
const clippedIndex = buildTraceIndex(
  clipped,
  timeline(clipped),
  new Map([["flow", all.get("flow")]]),
);
assert.ok(clippedIndex.axis.boundaryAdjusted);
assert.ok(
  clippedIndex.rows
    .get("flow")
    .slices.every((slice) => slice.duration === null || slice.duration >= 0),
  "Late recording metadata cannot create a negative displayed call interval",
);

const stateNodes = new Map(
  ["pending", "approved", "revoked"].map((value) => [value, { id: value, kind: "state", value }]),
);
const cfg = (id, phase) => ({ snapshot_instance: id, attempt: "application", phase });
const transitions = [
  cfg("r:file:1", "pending"),
  cfg("r:share:1", "revoked"),
  cfg("r:file:1", "approved"),
];
const steps = transitions.map((_, i) => ({ id: "s" + i, run_id: "r", revision: i }));
const recording = {
  build_id: "b",
  context: { model: {}, machine: { configurations: [] } },
  final: { machine: { configurations: [transitions[2], transitions[1]] } },
  runtime_frames: {
    schema: "stategraph-runtime-frames/v1",
    frames: transitions.map((config, i) => ({
      event_id: "s" + i,
      run_id: "r",
      build_id: "b",
      revision: i,
      machine: { state_revision: i, configurations: [config] },
    })),
  },
};
const occupancy = stateResidencies(recording, steps, [[], [], []], stateNodes, {
  times: [0, 10, 30],
  total: 50,
  ordered: true,
});
assert.deepEqual(
  occupancy.links.map((link) => [link.fromNode, link.toNode]),
  [["pending", "approved"]],
);
assert.equal(occupancy.slices.find((slice) => slice.node === "pending").duration, 30);
assert.equal(occupancy.slices.find((slice) => slice.node === "revoked").end, 50);

const original = {
  model: { nodes: [{ id: "flow" }], edges: [] },
  manifest: { bindings: {} },
  project_structure: {
    nodes: [
      { id: "dir", kind: "function", code_role: "directory" },
      { id: "file", kind: "function", code_role: "file", parent: "dir" },
    ],
    edges: [
      { id: "contains", from: "dir", to: "file", type: "contains", code_relation: "contains" },
    ],
    bindings: {},
  },
};
const merged = withCodeGraph(original, null);
assert.equal(merged.model.nodes.length, 3);
assert.equal(merged.model.edges.length, 1);
assert.equal(original.model.nodes.length, 1, "View projection never mutates the authored model");
assert.equal(
  withCodeGraph(merged, null).model.nodes.length,
  3,
  "Repeated refreshes preserve unique IDs",
);
console.log(
  "PASS: nine distinct layer colors/order, parallel residency tracks, instance identity, call nesting and file-only replay projection.",
);
