/** Open context is left-clipped evidence, not a fabricated start inside a recording. */
import assert from "node:assert/strict";
import {
  buildTraceIndex,
  traceRows,
} from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import { visibleFlows } from "../skills/vibelens/assets/stategraph-viewer/trace-flows.js";
import { graphActivations } from "../skills/vibelens/assets/stategraph-viewer/graph-activation.js";
import { timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import { BOProbe } from "../skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs";
const at = (ms) => new Date(Date.UTC(2026, 9, 30) + ms).toISOString();
const nodes = [
  { id: "share", kind: "action", layer: "business", capture: { in: {}, out: {} } },
  { id: "check", kind: "decision", capture: { in: {}, out: {} } },
];
const all = new Map(nodes.map((node) => [node.id, node]));
const event = (id, node, phase, ms, extra = {}) => ({
  id,
  node,
  phase,
  seq: ms,
  call_id: node,
  producer_id: "worker",
  run_id: "run",
  build_id: "build",
  entity: "file-1",
  attempt: "share-1",
  lifecycle: "span",
  observed_at: at(ms),
  inputs: {},
  outputs: {},
  depends: [],
  ...extra,
});
const parent = event("before-start", "share", "enter", 1);
const r = {
  id: "window",
  status: "stopped",
  started_at: at(10),
  ended_at: at(20),
  commands: [],
  gaps: [],
  context: {
    model: { nodes, edges: [], machine: {} },
    machine: { configurations: [] },
    events: [parent],
  },
  final: { machine: { configurations: [] } },
  events: [
    event("child-enter", "check", "enter", 12, { parent_call_id: "share" }),
    event("child-return", "check", "return", 15),
    event("parent-return", "share", "return", 18),
  ],
};
const bytes = JSON.stringify(r),
  items = timeline(r),
  index = buildTraceIndex(r, items, all);
const bar = index.rows.get("share").slices[0];
assert.equal(bar.raw, 0);
assert.equal(bar.start, 0);
assert.equal(bar.end, 8);
assert.equal(bar.clippedStart, true);
assert.equal(bar.context_entry.id, parent.id);
assert.equal(bar.unfinished, false);
assert.equal(index.links.filter((link) => link.type === "call").length, 1);
assert.equal(index.links.filter((link) => link.type === "return").length, 1);
const flow = visibleFlows(
  index,
  traceRows(index, { scope: "all", order: ["business", "rules"], expanded: ["business", "rules"] }),
  { start: 0, end: 10 },
);
assert.equal(flow.length, 2);
assert.equal(graphActivations(r.context.events, nodes).get("share").phase, "running");
assert.equal(JSON.stringify(r), bytes, "raw context and interval events remain byte-identical");
const live = { ...r, status: "recording", events: [], observed_until: at(22) };
const open = buildTraceIndex(live, timeline(live), all).rows.get("share").slices[0];
assert.equal(open.unfinished, true);
assert.equal(open.end, 12);
const closedContext = {
  ...r,
  events: [],
  context: { ...r.context, events: [parent, event("old-return", "share", "return", 5)] },
};
assert.equal(
  buildTraceIndex(closedContext, timeline(closedContext), all).rows.size,
  0,
  "old completed context does not create a new activity",
);
const completedDependency = {
  ...closedContext,
  events: [
    event("new-check", "check", "enter", 12, {
      depends: [{ event: "old-return", type: "control" }],
    }),
  ],
};
const dependency = buildTraceIndex(completedDependency, timeline(completedDependency), all);
assert.equal(dependency.links[0].fromEvent, "old-return");
assert.equal(
  dependency.rows.get("share").slices.length,
  0,
  "a prior fact gets a boundary marker, not an invented duration",
);
const dependencyRows = traceRows(dependency, { scope: "all", order: ["business", "rules"] });
assert.equal(
  visibleFlows(dependency, dependencyRows, { start: 0, end: dependency.axis.total }).length,
  1,
  "a closed pre-recording fact keeps its boundary connector in the recipient band",
);
const sharedHistory = {
  ...completedDependency,
  events: [
    ...completedDependency.events,
    event("another-check", "check", "enter", 13, {
      entity: "file-2",
      depends: [{ event: "old-return", type: "data" }],
    }),
  ],
};
const sharedDependency = buildTraceIndex(sharedHistory, timeline(sharedHistory), all);
const sharedRows = traceRows(sharedDependency, { scope: "all", order: ["business", "rules"] });
const sharedFlows = visibleFlows(sharedDependency, sharedRows, {
  start: 0,
  end: sharedDependency.axis.total,
});
assert.equal(
  sharedFlows.length,
  2,
  "one historical fact can feed two independent concurrent executions",
);
assert.ok(
  sharedFlows.every((flow) => sharedRows[flow.fromRow].group === sharedRows[flow.toRow].group),
);
assert.ok(
  sharedRows.filter((row) => row.layer === "business").every((row) => row.slices.length === 0),
  "shared boundary markers never become invented active calls",
);

const delivered = [],
  probe = new BOProbe({
    project: { project_id: "child-context", model: { nodes } },
    buildId: "build",
    sink: (body) => delivered.push(body),
  });
await probe.span(
  "share",
  async (operation) => {
    assert.ok(operation.entryId);
    return operation.child("check", async () => true);
  },
  {
    entity: "file-1",
    attempt: "share-1",
    revision: 3,
    depends: [{ event: "prior", type: "data" }],
  },
);
await probe.flush(5000);
const child = delivered.find((event) => event.node === "check");
assert.equal(child.entity, "file-1");
assert.equal(child.parent_call_id, delivered[0].call_id);
assert.equal(
  Object.hasOwn(child, "revision"),
  false,
  "a parent's state snapshot revision is not a child's frame",
);
assert.deepEqual(child.depends, [], "a parent's direct dependencies are not invented child inputs");
console.log(
  JSON.stringify({
    passed: true,
    clippedScopes: true,
    parentReturns: true,
    contextBytesUnchanged: true,
    childMetadataIsolated: true,
  }),
);
