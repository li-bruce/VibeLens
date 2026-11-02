/** One layer row per execution band, independent of node counts and display names. */
import assert from "node:assert/strict";
import {
  buildTraceIndex,
  traceRows,
} from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import { visibleFlows } from "../skills/vibelens/assets/stategraph-viewer/trace-flows.js";
import { groupCurve } from "../skills/vibelens/assets/stategraph-viewer/trace-routing.js";
import { timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";

const nodes = [
  { id: "share", kind: "action", layer: "business", label: "Share file" },
  { id: "permission", kind: "decision", label: "Read access" },
  { id: "quota", kind: "decision", label: "Check quota" },
  { id: "write", kind: "function", label: "Write share" },
];
const all = new Map(nodes.map((node) => [node.id, node]));
const at = (ms) => new Date(Date.UTC(2026, 9, 31) + ms).toISOString();
const events = [];
const add = (ms, user, node, phase, call, parent = null, depends = []) => {
  const value = {
    id: "event:" + events.length,
    seq: events.length + 1,
    node,
    phase,
    call_id: call,
    parent_call_id: parent,
    build_id: "build",
    run_id: "run",
    producer_id: "worker",
    entity: user,
    attempt: user,
    inputs: {},
    outputs: {},
    depends,
    observed_at: at(ms),
    lifecycle: "span",
  };
  events.push(value);
  return value;
};
add(1, "alice", "share", "enter", "request-a");
add(2, "alice", "permission", "enter", "p-a", "request-a");
add(3, "bob", "share", "enter", "request-b");
add(4, "bob", "permission", "enter", "p-b", "request-b");
const permission = add(5, "alice", "permission", "return", "p-a", "request-a");
add(6, "alice", "quota", "enter", "q-a", "request-a", [{ event: permission.id, type: "data" }]);
add(7, "bob", "permission", "return", "p-b", "request-b");
const write = add(8, "bob", "write", "enter", "w-b", "request-b");
const release = add(9, "bob", "write", "return", "w-b", "request-b");
add(10, "alice", "quota", "return", "q-a", "request-a");
add(11, "alice", "write", "enter", "w-a", "request-a", [{ event: release.id, type: "data" }]);
add(12, "alice", "write", "return", "w-a", "request-a");
add(13, "bob", "share", "return", "request-b");
add(14, "alice", "share", "return", "request-a");
add(20, "alice", "share", "enter", "request-c");
add(21, "alice", "share", "return", "request-c");
const record = {
  id: "record",
  started_at: at(0),
  ended_at: at(22),
  status: "stopped",
  events,
  context: { events: [], model: { nodes, edges: [], machine: {} }, machine: {} },
  final: { machine: {} },
  commands: [],
};
const index = buildTraceIndex(record, timeline(record), all);
const options = { scope: "all", order: ["business", "rules", "execution"] };
const rows = traceRows(index, options);
assert.equal(index.executions.chains.length, 3);
assert.equal(index.executions.lanes.length, 2);
assert.equal(rows.length, 6, "two concurrent executions occupy exactly 2 × 3 layer rows");
assert.deepEqual(
  rows.map((row) => row.layer),
  [...options.order, ...options.order],
);
assert.equal(
  rows.filter((row) => row.layer === "rules")[0].slices.length,
  2,
  "two rule nodes share one layer row",
);
assert.equal(rows[0].slices.length, 2, "a later request reuses the completed execution band");
assert.ok(
  rows.every((row) => !row.header),
  "node tracks and duplicate layer headings are absent",
);
const group = rows[0].group;
const collapsed = traceRows(index, { ...options, collapsed: [group] });
assert.equal(collapsed.length, 4);
assert.equal(collapsed[0].layer, "business");
assert.equal(collapsed[0].folded, true);
assert.equal(traceRows(index, { ...options, collapseAll: true }).length, 2);
assert.deepEqual(
  traceRows(index, { ...options, order: ["rules", "business", "execution"], depth: "rules" }).map(
    (row) => row.layer,
  ),
  ["business", "rules", "business", "rules"],
  "business is the first fold handle even after graph-plane reordering",
);
const flows = visibleFlows(index, rows, { start: 0, end: 22 });
assert.ok(
  flows.some((flow) => flow.fromRow === flow.toRow && flow.type === "data"),
  "same-layer evidence remains horizontal",
);
assert.ok(
  flows.some(
    (flow) => rows[flow.fromRow].group === rows[flow.toRow].group && flow.fromRow !== flow.toRow,
  ),
  "nested calls cross layers inside one band",
);
const shared = flows.find((flow) => rows[flow.fromRow].group !== rows[flow.toRow].group);
assert.ok(shared, "explicit shared-data dependency bridges concurrent bands");
assert.equal(index.items[shared.from].id, release.id);
assert.equal(index.items[shared.to].node, "write");
const curve = groupCurve(100, 40, 160, 170, { left: 0, right: 600 });
assert.deepEqual(curve[0], { x: 100, y: 40 });
assert.deepEqual(curve.at(-1), { x: 160, y: 170 });
assert.ok(curve[10].x > 160, "cross-band bridge has a visible smooth bend");
const single = traceRows(index, { ...options, depth: "rules", layerMode: "single" });
assert.equal(single.length, 2);
assert.ok(single.every((row) => row.layer === "rules"));
assert.equal(index.items.length, events.length + 2, "row folding does not remove evidence");
const ongoing = {
  ...record,
  id: "mid-span",
  status: "recording",
  started_at: at(4),
  observed_until: at(4.5),
  ended_at: null,
  events: [],
  context: { ...record.context, events: events.slice(0, 4) },
};
const clippedIndex = buildTraceIndex(ongoing, timeline(ongoing), all);
const clippedRows = traceRows(clippedIndex, options);
assert.equal(clippedIndex.executions.lanes.length, 2);
assert.equal(
  clippedRows.length,
  6,
  "both already-running callers retain their own full layer band",
);
assert.deepEqual(
  clippedRows.filter((row) => row.layer === "business").map((row) => row.slices.length),
  [1, 1],
);
assert.equal(
  new Set(
    clippedIndex.lifecycles.contextSources
      .filter((event) => event.node === "share")
      .map((event) => event.id),
  ).size,
  2,
  "two context entries of the same graph node remain distinct",
);
// Legacy facts with missing ownership retain point markers in an explicit
// unassigned lane. The active request and matching entity do not invent a parent.
const unknownEvents = [
  { ...events[0], id: "unknown-start", observed_at: at(1), parent_event_id: null },
  {
    ...events[1],
    id: "unknown-point-a",
    node: "permission",
    phase: "decision",
    call_id: "point-a",
    parent_call_id: null,
    lifecycle: undefined,
    observed_at: at(2),
  },
  {
    ...events[1],
    id: "unknown-point-b",
    node: "permission",
    phase: "decision",
    call_id: "point-b",
    parent_call_id: null,
    lifecycle: undefined,
    observed_at: at(8),
  },
  { ...events[0], id: "unknown-end", phase: "return", observed_at: at(9), parent_event_id: null },
];
const unknownRecord = {
  ...record,
  context: { ...record.context, events: [] },
  events: unknownEvents,
};
const unknownIndex = buildTraceIndex(unknownRecord, timeline(unknownRecord), all);
assert.equal(unknownIndex.executions.lanes.filter((lane) => lane.kind === "invocation").length, 1);
assert.equal(unknownIndex.executions.lanes.filter((lane) => lane.kind === "observation").length, 1);
const unknownFacts = unknownIndex.executions.chains.filter((chain) => chain.kind === "observation");
assert.equal(unknownFacts.length, 2);
assert.ok(unknownFacts.every((chain) => chain.start === chain.end));
assert.ok(traceRows(unknownIndex, options).some((row) => row.groupKind === "observation"));
const externalNodes = new Map(all);
externalNodes.set("permission", { ...all.get("permission"), observation_root: true });
const externalIndex = buildTraceIndex(unknownRecord, timeline(unknownRecord), externalNodes);
assert.ok(externalIndex.executions.lanes.every((lane) => lane.kind === "invocation"));
assert.equal(externalIndex.executions.chains.length, 3);
assert.equal(
  externalIndex.executions.chains.filter((chain) => chain.start === chain.end).length,
  2,
  "declared external notifications remain point roots without an invented duration",
);
console.log(
  JSON.stringify({
    passed: true,
    executions: 3,
    concurrentBands: 2,
    rows: rows.length,
    collapsedRows: collapsed.length,
    links: flows.length,
    sharedEvent: release.id,
    checks: 15,
  }),
);
