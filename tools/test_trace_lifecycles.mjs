/** Shared graph/timeline lifetimes, causal geometry, depth and live baseline regressions. */
import assert from "node:assert/strict";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import {
  buildTraceIndex,
  traceRows,
} from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import { visibleFlows } from "../skills/vibelens/assets/stategraph-viewer/trace-flows.js";
import { graphActivations } from "../skills/vibelens/assets/stategraph-viewer/graph-activation.js";
import {
  stateResidencies,
  activityResidencies,
} from "../skills/vibelens/assets/stategraph-viewer/trace-residencies.js";
import { visibleSlices } from "../skills/vibelens/assets/stategraph-viewer/trace-viewport.js";
import { LiveTrace } from "../skills/vibelens/assets/stategraph-viewer/trace-session.js";
import { timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import {
  status,
  viewTypes,
  nodeType,
} from "../skills/vibelens/assets/stategraph-viewer/graph-core.js";
import { BOProbe } from "../skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs";

const at = (ms) => new Date(Date.UTC(2026, 9, 30) + ms).toISOString();
const nodes = [
  {
    id: "share",
    kind: "action",
    layer: "business",
    label: "Share file",
    capture: { in: {}, out: { ok: "boolean", error: "string" } },
  },
  {
    id: "check",
    kind: "decision",
    label: "Check permission",
    capture: { in: {}, out: { allowed: "boolean", error: "string" } },
  },
  {
    id: "query",
    kind: "function",
    data_role: "query",
    label: "Read grants",
    capture: { in: {}, out: { count: "number" } },
  },
];
const all = new Map(nodes.map((node) => [node.id, node]));
const event = (node, phase, time, options = {}) => ({
  id: "event:" + time,
  kind: "probe",
  seq: time,
  node,
  phase,
  call_id: node,
  build_id: "build",
  run_id: "run",
  producer_id: "worker",
  entity: "file:1",
  attempt: "share:1",
  inputs: {},
  outputs: {},
  depends: [],
  observed_at: at(time),
  ...options,
});
const view = {
  stage: "runtime",
  manifest: { build_id: "build" },
  health: { run_id: "run" },
  binding_status: { status: "current" },
  authority: { basis: {}, parameters: {} },
  model: { nodes, edges: [], machine: {} },
  machine: { current: null, configurations: [] },
  events: [],
};
const record = (events) => ({
  id: "record",
  status: "stopped",
  started_at: at(0),
  ended_at: at(30),
  context: view,
  final: view,
  events,
  commands: [],
  gaps: [],
});
const checks = [];
assert.equal(
  visibleSlices({ slices: [{ start: 3000.5, end: 3000.5 }], maxEnds: [3000.5] }, 0, 3000.5).length,
  1,
  "the visible right boundary includes fractional instant flows",
);
const semanticParameter = {
  id: "semantic-status",
  kind: "data",
  semantic_role: "state_parameter",
  represents: { path: "share.py", symbol: "share", parameter: "status" },
};
assert.equal(nodeType(semanticParameter), "data");
assert.ok(
  viewTypes(semanticParameter).includes("state"),
  "state view includes its independent parameter representation",
);

const events = [
  event("share", "enter", 1),
  event("check", "enter", 2, { parent_call_id: "share" }),
  event("query", "enter", 3, { parent_call_id: "check" }),
  event("query", "return", 8), // only the entry must carry parentage
  event("check", "return", 10),
  event("share", "return", 15),
];
const r = record(events),
  items = timeline(r),
  index = buildTraceIndex(r, items, all);
assert.deepEqual(
  [...index.rows.values()].map((row) => row.slices[0].duration),
  [14, 8, 5],
);
assert.equal(index.links.filter((link) => link.type === "return").length, 2);
for (let raw = 1; raw < items.length - 1; raw++) {
  const current = graphActivations(items.slice(0, raw + 1), nodes);
  for (const node of nodes) {
    const slice = index.rows.get(node.id).slices[0];
    if (slice.raw <= raw && raw < slice.last) assert.equal(current.get(node.id).phase, "running");
  }
}
assert.equal(graphActivations(items, nodes).get("share").phase, "returned");
checks.push(
  "all observed layers keep actual lifetimes in both graph and timeline; entry-only parentage returns correctly",
);
const delayedBoundary = record(events);
delayedBoundary.started_at = at(5);
const delayed = buildTraceIndex(delayedBoundary, timeline(delayedBoundary), all);
assert.equal(delayed.axis.ordered, true);
assert.equal(delayed.axis.boundaryAdjusted, true);
assert.equal(delayed.rows.get("share").slices[0].duration, 14);
assert.equal(
  delayedBoundary.started_at,
  at(5),
  "boundary display correction never rewrites raw timestamps",
);
checks.push(
  "late recording boundary metadata retains producer durations without hiding actual timestamp disorder",
);
const order = ["business", "rules", "operations"],
  expanded = order;
const rows = traceRows(index, { scope: "all", order, expanded });
const flows = visibleFlows(index, rows, { start: 0, end: 30 });
assert.equal(flows.length, 4);
for (const link of flows)
  assert.equal(
    link.fromTime,
    link.toTime,
    "call/return stays inside parent interval at child boundary",
  );
const upper = traceRows(index, { scope: "all", order, expanded, depth: "rules" });
assert.deepEqual([...new Set(upper.map((row) => row.layer))], ["business", "rules"]);
assert.equal(visibleFlows(index, upper, { start: 0, end: 30 }).length, 2);
const single = traceRows(index, {
  scope: "all",
  order,
  expanded,
  depth: "rules",
  layerMode: "single",
});
assert.deepEqual([...new Set(single.map((row) => row.layer))], ["rules"]);
assert.equal(visibleFlows(index, single, { start: 0, end: 30 }).length, 0);
assert.equal(index.links.length, 4, "depth filtering preserves original evidence");
checks.push(
  "contiguous observation bottom, single-layer mode and hidden lower links retain original evidence",
);

const committed = [
  event("share", "enter", 1),
  event("share", "commit", 2),
  event("check", "enter", 3, { parent_call_id: "share" }),
  event("check", "return", 8),
];
let rr = record(committed),
  ix = buildTraceIndex(rr, timeline(rr), all);
assert.equal(ix.rows.get("share").slices[0].unfinished, true);
assert.equal(graphActivations(timeline(rr), nodes).get("share").phase, "running");
const explicit = [event("share", "enter", 1, { lifecycle: "span" }), event("share", "commit", 2)];
assert.equal(
  graphActivations(explicit, nodes).get("share").phase,
  "running",
  "an explicit span cannot close at a decision or commit even before its next child begins",
);
const concurrent = [
  event("share", "enter", 1, { call_id: "first", lifecycle: "span" }),
  event("share", "enter", 2, { call_id: "second", lifecycle: "span" }),
  event("share", "wait", 3, { call_id: "second", lifecycle: "span" }),
];
const combined = graphActivations(concurrent, nodes).get("share");
assert.equal(combined.phase, "running");
assert.equal(combined.activeCount, 2);
assert.equal(combined.waitingCount, 1);
assert.equal(
  graphActivations([...concurrent, event("share", "return", 4, { call_id: "first" })], nodes).get(
    "share",
  ).phase,
  "waiting",
);
const waiting = [...committed, event("share", "wait", 9)];
assert.equal(graphActivations(waiting, nodes).get("share").phase, "waiting");
assert.equal(status(nodes[0], view, waiting, "latest"), "blocked");
assert.equal(
  graphActivations([...waiting, event("share", "error", 10)], nodes).get("share").phase,
  "exception",
);
checks.push(
  "intermediate commit does not complete a still-owned child; execution waits, returns and exceptions remain distinct from business outcomes",
);

const sameLayer = [
  event("share", "read", 1),
  event("share", "read", 4, { depends: [{ event: "event:1", type: "control" }] }),
];
rr = record(sameLayer);
ix = buildTraceIndex(rr, timeline(rr), all);
assert.equal(
  visibleFlows(ix, traceRows(ix, { scope: "all", order, expanded }), { start: 0, end: 30 }).length,
  1,
);
checks.push("same-row causal chains remain visible");
const stateNodes = new Map([
  ["pending", { id: "pending", kind: "state", value: "pending" }],
  ["done", { id: "done", kind: "state", value: "done" }],
]);
const occupancy = stateResidencies(
  { context: { machine: { current: "pending" } } },
  [{ id: "start" }, { id: "changed", attempt: "application" }],
  [[], [{ kind: "business", before: "pending", after: "done", attempt: "application" }]],
  stateNodes,
  { times: [0, 10], total: 20, ordered: true },
);
assert.equal(occupancy.slices.find((slice) => slice.node === "pending").duration, 10);
assert.equal(occupancy.slices.find((slice) => slice.node === "done").unfinished, true);
assert.equal(occupancy.links[0].fromNode, "pending");
assert.equal(occupancy.links[0].toNode, "done");
checks.push(
  "native state occupancy and witnessed transition links remain distinct from invocation calls",
);

const activityNodes = new Map([["review", { id: "review", execution_role: "activity" }]]);
const activity = activityResidencies(
  { context: { machine: { configurations: [] } } },
  [{}, {}, {}, {}],
  [
    [],
    [{ kind: "state", node: "review", after: "running" }],
    [{ kind: "state", node: "review", after: "waiting" }],
    [{ kind: "state", node: "review", after: "succeeded" }],
  ],
  activityNodes,
  { times: [0, 1, 4, 9], total: 12, ordered: true },
);
assert.equal(activity[0].duration, 8);
assert.equal(activity[0].stages.at(-1).phase, "waiting");
assert.equal(activity[0].stages.at(-1).end, 9);
checks.push("native activity execution and wait intervals need no fabricated function entry");

const live = new LiveTrace(2);
const baseline = { ...view, events: [event("share", "return", 1)] };
live.observe(baseline, "build", at(3));
assert.equal(
  live.current.events.length,
  0,
  "old events are baseline, not replayed against a future state",
);
const first = live.observe(
  { ...view, events: [...baseline.events, event("share", "enter", 4)] },
  "build",
  at(5),
);
const li = buildTraceIndex(first, timeline(first), all);
assert.equal(li.rows.get("share").slices[0].end, 2);
assert.equal(li.rows.get("share").slices[0].duration, null);
live.observe(
  { ...view, events: [...first.events, event("share", "return", 6), event("check", "read", 7)] },
  "build",
  at(8),
);
assert.equal(live.current.status, "limited");
assert.ok(live.current.gaps.length);
live.observe(view, "new-build", at(10));
assert.equal(live.current.events.length, 0);
checks.push(
  "live observation has a frozen initial baseline, open interval, bounded retention and build reset",
);

const delivered = [],
  probe = new BOProbe({
    project: { project_id: "span-test", model: { nodes } },
    buildId: "build",
    sink: (body) => delivered.push(body),
  });
const result = await probe.span(
  "share",
  async (share) => {
    await share.child(
      "check",
      async (check) => check.child("query", async () => 3, { outputs: (count) => ({ count }) }),
      { outputs: () => ({ allowed: true }) },
    );
    return 42;
  },
  { outputs: () => ({ ok: true }) },
);
assert.equal(result, 42);
await probe.flush(5000);
assert.equal(delivered.length, 6);
assert.equal(delivered[1].parent_call_id, delivered[0].call_id);
assert.equal(delivered[2].parent_call_id, delivered[1].call_id);
assert.equal(delivered.at(-1).phase, "return");
const failure = new Error("same error");
await assert.rejects(
  probe.span("share", async () => {
    throw failure;
  }),
  (error) => error === failure,
);
await probe.flush(5000);
assert.equal(delivered.at(-1).phase, "error");
checks.push(
  "native JavaScript awaited spans retain results, exception identity and explicit nested parentage",
);
const out = process.env.BO_LIFECYCLE_EVIDENCE;
if (out) {
  await mkdir(out, { recursive: true });
  await writeFile(out + "/lifecycle-unit.json", JSON.stringify({ passed: true, checks }, null, 2));
}
console.log(JSON.stringify({ passed: true, checks }, null, 2));
