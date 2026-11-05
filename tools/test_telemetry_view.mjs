/** One causal recording drives graph activation, 2D/3D transfers and timeline bands. */
import assert from "node:assert/strict";
import { traceLifecycles } from "../skills/vibelens/assets/stategraph-viewer/trace-lifecycles.js";
import { graphActivations } from "../skills/vibelens/assets/stategraph-viewer/graph-activation.js";
import { parentEvent } from "../skills/vibelens/assets/stategraph-viewer/trace-evidence.js";
import { timeline, transferEdges } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import {
  buildTraceIndex,
  traceRows,
} from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import { traceDescription } from "../skills/vibelens/assets/stategraph-viewer/trace-tooltip.js";

const nodes = [
  { id: "share", layer: "business", kind: "action", label: "Share file" },
  { id: "api", code_role: "endpoint", kind: "function", label: "POST /shares" },
  { id: "job", kind: "function", label: "Deliver message" },
];
const all = new Map(nodes.map((node) => [node.id, node]));
const events = [];
const metadata = (id, parent = null, links = [], traceId = "1".repeat(32)) => ({
  trace_id: traceId,
  span_id: id.repeat(16),
  parent_span_id: parent?.repeat(16) || null,
  trace_flags: 1,
  links,
});
const event = (node, phase, call, time, trace, parent = null) => {
  const value = {
    id: `event-${events.length}`,
    node,
    phase,
    call_id: call,
    parent_event_id: parent?.id || null,
    parent_call_id: parent?.call_id || null,
    project_id: "project",
    build_id: "build",
    model_revision: "1",
    run_id: "worker",
    producer_id: "producer",
    entity: node,
    attempt: "one",
    lifecycle: "span",
    seq: events.length + 1,
    inputs: {},
    outputs: {},
    depends: [],
    trace,
    observed_at: new Date(Date.UTC(2026, 10, 1) + time).toISOString(),
    kind: "probe",
  };
  events.push(value);
  return value;
};
const root = event("share", "enter", "request", 1, metadata("1"));
event("share", "return", "request", 4, metadata("1"));
const child = event("api", "enter", "detached", 5, metadata("2", "1"), root);
const job = event(
  "job",
  "enter",
  "job",
  7,
  metadata(
    "3",
    null,
    [
      {
        trace_id: "1".repeat(32),
        span_id: "1".repeat(16),
        relation: "trigger",
      },
    ],
    "2".repeat(32),
  ),
);
event("api", "return", "detached", 10, metadata("2", "1"), root);
event("job", "return", "job", 11, job.trace);
const original = JSON.stringify(events);
const facts = traceLifecycles(events, all);
assert.ok(facts.links.some((link) => link.from === 0 && link.to === 2 && link.outlivesParent));
assert.equal(facts.links.filter((link) => link.evidence === "otel-link").length, 1);
assert.equal(parentEvent(child, events)?.id, root.id);
const active = graphActivations(events.slice(0, 4), nodes);
assert.equal(active.get("api").phase, "running");
assert.notEqual(
  active.get("share").phase,
  "running",
  "causal children do not extend parent lifecycle",
);
const edge = {
  id: "trigger-job",
  type: "flow",
  members: [{ from: "share", to: "job", type: "flow" }],
};
assert.deepEqual(transferEdges(job, events, [edge], all), [edge.id]);
const recording = {
  id: "record",
  events,
  commands: [],
  status: "stopped",
  started_at: new Date(Date.UTC(2026, 10, 1)).toISOString(),
  ended_at: new Date(Date.UTC(2026, 10, 1) + 12).toISOString(),
  context: {
    events: [],
    model: { nodes, edges: [], machine: {} },
    machine: {},
  },
  final: { machine: {} },
};
const items = timeline(recording),
  index = buildTraceIndex(recording, items, all);
const rows = traceRows(index, {
  scope: "all",
  order: ["business", "api", "execution"],
});
assert.equal(
  index.executions.chains.length,
  2,
  "Span Links connect executions without merging them",
);
assert.equal(index.executions.lanes.length, 2);
assert.equal(rows.length, 6);
assert.deepEqual(
  rows.map((row) => row.layer),
  ["business", "entry", "symbols", "business", "entry", "symbols"],
  "Each independent execution retains one row per active concern",
);
assert.ok(rows.filter((row) => row.layer === "entry").some((row) => row.members.includes("api")));
assert.ok(
  rows.filter((row) => row.layer === "symbols").some((row) => row.members.includes("job")),
  "Consolidation preserves both the HTTP registration and asynchronous job identities",
);
assert.equal(JSON.stringify(events), original);
const actualException = {
  ...events.at(-1),
  phase: "error",
  exception: { type: "TypeError" },
  outputs: {},
};
const details = traceDescription(
  { kind: "mark", raw: 0, row: "job" },
  { items: [actualException], rows: new Map() },
  all,
  {},
  String,
);
assert.ok(
  details.lines.some((line) => line.includes("TypeError")),
  "physical exception remains visible even without an optional business error output",
);
assert.equal(JSON.stringify(events), original);
console.log(
  JSON.stringify({
    valid: true,
    rows: rows.length,
    executions: index.executions.chains.length,
    links: facts.links.length,
    checks: [
      "late child",
      "parent duration",
      "Span Link transfer",
      "concurrent bands",
      "immutable recording",
    ],
  }),
);
