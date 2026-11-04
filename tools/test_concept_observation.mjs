/** Bound views reuse real intervals without claiming a conceptual total lifetime. */
import assert from "node:assert/strict";
import { conceptBindingId } from "../skills/vibelens/assets/stategraph-viewer/concept-bindings.js";
import { graphInventory } from "../skills/vibelens/assets/stategraph-viewer/graph-inventory.js";
import { activationFor } from "../skills/vibelens/assets/stategraph-viewer/graph-activation.js";
import {
  callValues,
  lines,
  status,
} from "../skills/vibelens/assets/stategraph-viewer/graph-core.js";
import {
  buildTraceIndex,
  traceRows,
} from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import { timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import { boStepPlan } from "../skills/vibelens/assets/stategraph-viewer/replay-steps.js";
import { traceDescription } from "../skills/vibelens/assets/stategraph-viewer/trace-tooltip.js";

const node = (id, kind, layer) => ({
  id,
  label: id,
  kind: kind === "state" ? "state" : "action",
  concept_kind: kind,
  origin: "concept-design",
  layer,
});
const concepts = [
  node("send", "action", "business"),
  node("fact:owner", "fact", "rules"),
  node("decision:send", "rule_operation", "rules"),
  node("event:send", "event", "state"),
  { ...node("state:active", "state", "state"), value: "active" },
];
const native = [
  { id: "write", kind: "function", basis_fields: [] },
  { id: "notify", kind: "function", basis_fields: [] },
  { id: "policy:allow", kind: "decision", policy_node: "allow", basis_fields: [] },
  { id: "native:active", kind: "state", value: "active" },
];
const binding = (from, to) => ({
  id: conceptBindingId(from, to),
  from,
  to,
  type: "maps",
  code_relation: "maps",
  mapping_role: "implements",
  origin: "concept-binding",
  evidence_kind: "binding",
  observed: false,
});
const view = {
  model: {
    nodes: native,
    edges: [],
    machine: {
      states: ["active", "inactive"],
      values: ["active", "inactive"],
      events: {},
      transitions: [],
    },
  },
  concept_structure: {
    schema: "bo-concept-projection/v1",
    stage: "bound",
    revision: "one",
    nodes: concepts,
    edges: [
      binding("send", "write"),
      binding("send", "notify"),
      binding("fact:owner", "write"),
      binding("decision:send", "policy:allow"),
      binding("event:send", "write"),
      binding("state:active", "native:active"),
    ],
  },
  authority: { parameters: {}, basis: {} },
  machine: { current: "active", configurations: [], journal: [] },
  manifest: { build_id: "build", bindings: {} },
  binding_status: { status: "current" },
  events: [],
};
const event = (id, node, phase, time, call, outputs = {}) => ({
  id,
  node,
  phase,
  kind: "probe",
  lifecycle: "span",
  observed_at: new Date(1735689600000 + time).toISOString(),
  call_id: call,
  run_id: "run",
  stream_id: "stream",
  producer_id: "worker",
  project_id: "project",
  build_id: "build",
  model_revision: "one",
  attempt: "attempt",
  entity: "entity",
  basis: {},
  inputs: {},
  outputs,
});
const events = [
  event("a", "write", "enter", 0, "write-call"),
  event("b", "notify", "enter", 10, "notify-call"),
  event("c", "notify", "return", 20, "notify-call"),
  event("d", "write", "return", 30, "write-call", { owner: "Alice" }),
  {
    ...event("e", "policy:allow", "decision", 35, "policy-check", { value: false }),
    inputs: { bo_check: "check" },
  },
];
const record = {
  id: "test",
  status: "stopped",
  context: view,
  final: { machine: view.machine },
  events,
  commands: [],
  started_at: new Date(1735689600000).toISOString(),
  ended_at: new Date(1735689600040).toISOString(),
};
const before = JSON.stringify({ view, record });
const inventory = graphInventory(view),
  send = inventory.all.get("send");
assert.equal(status(send, view, [], "latest"), "declared");
assert.equal(activationFor(send, view, []), null);
const open = activationFor(send, view, events.slice(0, 2));
assert.equal(open.phase, "running");
assert.equal(open.activeCount, 2);
assert.equal(open.duration, null, "A concept has no fabricated aggregate duration");
assert.equal(status(send, view, events.slice(0, 2), "latest"), "active");
assert.equal(activationFor(send, view, events).duration, null);
assert.equal(status(inventory.all.get("decision:send"), view, events, "latest"), "blocked");
assert.equal(activationFor(inventory.all.get("fact:owner"), view, events), null);
assert.equal(activationFor(inventory.all.get("event:send"), view, events), null);
assert.deepEqual(callValues(inventory.all.get("fact:owner"), events), { inputs: {}, outputs: {} });
assert.ok(lines(send, view, events, "latest").some((line) => line.text.includes("write")));
assert.equal(status(inventory.all.get("state:active"), view, events, "latest"), "active");

const items = timeline(record),
  index = buildTraceIndex(record, items, inventory.all, inventory.rawEdges);
const slices = index.rows.get("send").slices;
assert.equal(slices.length, 2);
assert.deepEqual(
  slices.map((slice) => slice.duration).sort((a, b) => a - b),
  [10, 30],
);
assert.deepEqual(slices.map((slice) => slice.source_node).sort(), ["notify", "write"]);
assert.ok(
  slices.every(
    (slice) =>
      slice.role === "concept-observation" && slice.observation_basis.kind === "concept-binding",
  ),
);
for (const slice of slices) {
  assert.equal(items[slice.raw].node, slice.source_node);
  assert.equal(items[slice.last].node, slice.source_node);
  assert.ok(
    traceDescription(
      { kind: "slice", slice, raw: slice.last, row: "send" },
      index,
      inventory.all,
      {},
      String,
    ).lines.some((line) => line.includes(slice.source_node)),
  );
}
assert.ok(index.rows.get("fact:owner").marks.every((mark) => mark.projected));
assert.equal(index.rows.get("fact:owner").slices.length, 0);
assert.equal(index.rows.get("event:send").slices.length, 0);
assert.ok(index.rows.get("state:active").slices.every((slice) => slice.role === "residency"));
const rows = traceRows(index, {
  visible: new Set(["send"]),
  scope: "view",
  order: ["business", "implementation"],
});
assert.ok(rows.length && rows.every((row) => row.layer === "business"));
assert.equal(
  rows.flatMap((row) => row.slices).length,
  2,
  "Business-only Timeline retains both real call intervals",
);
const plan = boStepPlan(
  record,
  items,
  inventory.all,
  [{ id: "send", node: send, type: "business" }],
  { mode: "view" },
);
assert.ok(plan.includes(items.findIndex((item) => item.id === "a")));
assert.ok(plan.includes(items.findIndex((item) => item.id === "d")));

for (const patch of [
  { stage: "draft" },
  { edges: view.concept_structure.edges.map((edge) => ({ ...edge, origin: "concept-design" })) },
]) {
  const unbound = { ...view, concept_structure: { ...view.concept_structure, ...patch } };
  const graph = graphInventory(unbound),
    chosen = graph.all.get("send");
  assert.equal(status(chosen, unbound, events, "latest"), "declared");
  assert.equal(activationFor(chosen, unbound, events), null);
  const trace = buildTraceIndex({ ...record, context: unbound }, items, graph.all, graph.rawEdges);
  assert.ok(!trace.rows.has("send"));
  assert.ok(!trace.rows.has("state:active"), "An unbound state definition borrows no occupancy");
}
assert.equal(
  JSON.stringify({ view, record }),
  before,
  "All event, call and conceptual IDs remain immutable",
);
console.log(
  "PASS: bound call intervals, concurrent owners, business-only replay, real rule/state facts and rejection of arbitrary maps.",
);

const sharedIdentity = {
  ...view,
  model: {
    ...view.model,
    nodes: native.map((node) =>
      node.id === "policy:allow"
        ? {
            ...node,
            source: { path: "rules.py", symbol: "allowed" },
            capture: { out: { value: "boolean" } },
            lifecycle: { states: [{ id: "checked" }], bindings: [] },
          }
        : node,
    ),
  },
  concept_structure: {
    ...view.concept_structure,
    nodes: [
      ...concepts,
      {
        ...node("policy:allow", "rule_expression", "rules"),
        label: "Allow sharing",
        concept_definition: { operator: "predicate", parameters: { actor: "identity" } },
        source: { path: "wrong.py", symbol: "wrong" },
        capture: { out: { invented: "string" } },
        lifecycle: { incorrect: "must never replace native authority" },
      },
    ],
  },
};
const shared = graphInventory(sharedIdentity).all.get("policy:allow");
assert.deepEqual(shared.concept_definition, {
  operator: "predicate",
  parameters: { actor: "identity" },
});
assert.equal(shared.policy_node, "allow");
assert.equal(shared.label, "Allow sharing");
assert.equal(shared.concept_label, "Allow sharing");
assert.equal(shared.kind, "decision");
assert.deepEqual(shared.lifecycle, { states: [{ id: "checked" }], bindings: [] });
assert.deepEqual(shared.source, { path: "rules.py", symbol: "allowed" });
assert.deepEqual(shared.capture, { out: { value: "boolean" } });
assert.equal(shared.concept_observation, undefined);
