/** Registered meanings, neutral termination and visible causal routes stay evidence-bound. */
import assert from "node:assert/strict";
import {
  buildTraceIndex,
  traceRows,
} from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import { graphActivations } from "../skills/vibelens/assets/stategraph-viewer/graph-activation.js";
import { lifecycleTransition, lifecycleCaption } from "../skills/vibelens/assets/stategraph-viewer/node-lifecycle.js";
import { status } from "../skills/vibelens/assets/stategraph-viewer/graph-core.js";
import { durationDetail } from "../skills/vibelens/assets/stategraph-viewer/trace-density.js";
import { visibleFlows } from "../skills/vibelens/assets/stategraph-viewer/trace-flows.js";
import {
  routeFlow,
  routePoint,
  hitRoute,
  traceHit,
} from "../skills/vibelens/assets/stategraph-viewer/trace-routing.js";

const node = {
  id: "share",
  kind: "action",
  layer: "business",
  label: "Share file",
  capture: { in: {}, out: { status: "string", allowed: "boolean" } },
  lifecycle: {
    states: [
      { id: "checking", label: "Checking access", kind: "active" },
      { id: "queued", label: "Waiting for reviewer", kind: "waiting" },
      { id: "rejected", label: "Rejected", kind: "ended" },
    ],
    bindings: [
      { phase: "enter", boundary: "start", state: "checking" },
      {
        phase: "change",
        boundary: "update",
        state: "queued",
        when: { direction: "out", field: "status", equals: "pending" },
      },
      {
        phase: "return",
        boundary: "end",
        state: "rejected",
        when: { direction: "out", field: "allowed", equals: false },
      },
    ],
  },
};
const child = { id: "check", kind: "decision", label: "Read access" };
const event = (id, ms, phase, extra = {}) => ({
  id,
  node: "share",
  kind: "probe",
  phase,
  call_id: "share-1",
  run_id: "run",
  producer_id: "python",
  entity: "file-1",
  attempt: "request-1",
  observed_at: new Date(1793404800000 + ms).toISOString(),
  inputs: {},
  outputs: {},
  depends: [],
  lifecycle: "span",
  ...extra,
});
const items = [
  event("start", 0, "enter"),
  event("call", 100, "enter", { node: "check", call_id: "check-1", parent_call_id: "share-1" }),
  event("return", 300, "return", { node: "check", call_id: "check-1" }),
  event("waiting", 400, "change", { outputs: { status: "pending" } }),
  event("end", 1600, "return", {
    outputs: { allowed: false },
    depends: [{ event: "waiting", type: "control" }],
  }),
];
const original = JSON.stringify(items);
const nodes = [node, child],
  all = new Map(nodes.map((n) => [n.id, n]));
const record = {
  id: "test",
  status: "stopped",
  context: {
    model: { nodes, edges: [], machine: {} },
    events: [],
    machine: { configurations: [] },
  },
  final: { machine: { configurations: [] } },
};
const index = buildTraceIndex(record, items, all);
const life = index.rows.get("share").slices[0];
assert.equal(life.duration, 1600);
assert.deepEqual(
  life.stages.map((s) => s.state),
  ["checking", "queued"],
);
assert.equal(life.terminal.state, "rejected");
assert.equal(life.terminal.termination, "return");
assert.equal(lifecycleCaption(life.terminal, true), "rejected");
assert.equal(lifecycleCaption(life.terminal, false), "Rejected");
assert.equal(graphActivations(items.slice(0, 4), nodes).get("share").label, "Waiting for reviewer");
assert.equal(graphActivations(items, nodes).get("share").label, "Rejected");
assert.equal(graphActivations(items, nodes).get("check").phase, "returned");
const ordinary = { ...node };
delete ordinary.lifecycle;
const ordinaryView = {
  model: { nodes: [ordinary], machine: {} },
  binding_status: { status: "current" },
  authority: { basis: {} },
};
assert.equal(
  status(ordinary, ordinaryView, [items[0], items[4]], "latest"),
  "historical",
  "a false output cannot reclassify an observed normal return as a blocked lifecycle",
);
assert.equal(
  graphActivations([items[0], items[4]], [ordinary]).get("share").phase,
  "returned",
  "false business output is still a normal return without a registered meaning",
);
assert.equal(
  graphActivations([items[0], event("raised", 10, "error")], [ordinary]).get("share").phase,
  "exception",
);
assert.equal(
  lifecycleTransition(node, { phase: "return", outputs: { allowed: 0 } }).registered,
  false,
);
assert.equal(lifecycleTransition(node, { phase: "read" }).state, "running");
const rows = traceRows(index, { scope: "all", expanded: ["business", "rules"] });
const flows = visibleFlows(index, rows, { start: 0, end: 2000 });
assert.ok(flows.some((f) => f.type === "call"));
assert.ok(flows.some((f) => f.type === "return"));
assert.ok(flows.some((f) => f.type === "control" && f.fromRow === f.toRow));
const sameLayerNodes = [node, { ...child, kind: "action", layer: "business" }];
const sameLayerRecord = structuredClone(record);
sameLayerRecord.context.model.nodes = sameLayerNodes;
const sameLayerIndex = buildTraceIndex(
  sameLayerRecord,
  items,
  new Map(sameLayerNodes.map((n) => [n.id, n])),
);
const collapsedRows = traceRows(sameLayerIndex, { scope: "all", expanded: [] });
assert.ok(
  visibleFlows(sameLayerIndex, collapsedRows, { start: 0, end: 2000 }).some(
    (flow) =>
      flow.type === "call" &&
      flow.fromRow === flow.toRow &&
      items[flow.from].node !== items[flow.to].node,
  ),
  "two distinct nodes on one layer retain their actual call relation",
);
for (const [fy, ty] of [
  [30, 30],
  [30, 90],
  [90, 30],
]) {
  const route = routeFlow(40, fy, 180, ty);
  assert.equal(route[0].x, 40);
  assert.equal(route.at(-1).x, 180);
  const point = routePoint(route, 0.5);
  assert.ok(hitRoute(route, point));
  assert.equal(hitRoute(route, { x: 300, y: 300 }), false);
  assert.equal(traceHit([{ kind: "flow", route, raw: 4 }], point).raw, 4);
}
assert.equal(JSON.stringify(items), original);
const semantic = {
  id: "sharing-progress",
  kind: "data",
  event_node: "share",
  field: "status",
  direction: "out",
  lifecycle: {
    states: [
      { id: "pending", label: "Awaiting review", kind: "waiting" },
      { id: "denied", label: "Review declined", kind: "ended" },
    ],
    bindings: [
      {
        phase: "change",
        state: "pending",
        boundary: "start",
        when: { direction: "out", field: "status", equals: "pending" },
      },
      {
        phase: "return",
        state: "denied",
        boundary: "end",
        when: { direction: "out", field: "status", equals: "denied" },
      },
    ],
  },
};
const semanticItems = structuredClone(items);
semanticItems.at(-1).outputs.status = "denied";
const semanticNodes = [...nodes, semantic];
const semanticRecord = structuredClone(record);
semanticRecord.context.model.nodes = semanticNodes;
const semanticIndex = buildTraceIndex(
  semanticRecord,
  semanticItems,
  new Map(semanticNodes.map((n) => [n.id, n])),
);
assert.equal(semanticIndex.rows.get(semantic.id).slices[0].duration, 1200);
assert.equal(
  graphActivations(semanticItems, semanticNodes).get(semantic.id).label,
  "Review declined",
);
assert.equal(
  graphActivations(semanticItems.slice(0, 3), semanticNodes).has(semantic.id),
  false,
  "the owner's entry cannot invent a parameter invocation",
);
const bounded = routeFlow(188, 30, 189, 90, 0, { left: 190, right: 500 });
assert.ok(bounded[1].x >= 190, "the channel stays visible at the time-axis boundary");
assert.equal(bounded[0].x, 188);
assert.equal(bounded.at(-1).x, 189);
const denseSlices = Array.from({ length: 10000 }, (_, i) => ({
  raw: i * 2,
  last: i * 2 + 1,
  observed: i * 2 + 1,
  start: i * 2,
  end: i * 2 + 1,
}));
const density = durationDetail(denseSlices, {
  x: (value) => value / 20,
  left: 0,
  right: 1000,
  raw: 40,
});
assert.ok(density.bins.length <= 251);
assert.equal(
  density.bins.reduce((sum, bin) => sum + bin.count, 0) + density.detailed.length,
  10000,
);
assert.ok(
  density.detailed.some((slice) => slice.raw === 40),
  "selected interval remains individually inspectable",
);
assert.equal(
  durationDetail(denseSlices.slice(0, 5), {
    x: (value) => value * 10,
    left: 0,
    right: 1000,
    raw: -1,
  }).bins.length,
  0,
  "zoomed-in intervals retain their actual individual boundaries",
);
assert.equal(
  buildTraceIndex(structuredClone(record), [], all).rows.size,
  0,
  "definitions alone invent no execution",
);
console.log(
  JSON.stringify({
    passed: true,
    customStates: true,
    neutralTermination: true,
    actualDurations: true,
    sameRowAndCrossRowRoutes: true,
    originalEventsUnchanged: true,
  }),
);
