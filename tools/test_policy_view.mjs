/** Rule truth, shared ownership and metadata must stay honest across requests. */
import assert from "node:assert/strict";
import { captureFields } from "../skills/vibelens/assets/stategraph-viewer/capture-fields.js";
import { transferEdges } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import { matchingNodes, profileFor } from "../skills/vibelens/assets/stategraph-viewer/analysis.js";
import {
  nodeEvents,
  status,
  lines,
} from "../skills/vibelens/assets/stategraph-viewer/graph-core.js";

const rule = {
  id: "policy:permission",
  policy_node: "permission",
  kind: "decision",
  layer: "predicate",
  capture: {
    in: { bo_check: "string", bo_basis: "string", actor: "string" },
    out: { value: "boolean", status: "string" },
  },
  capture_metadata: { in: ["bo_check", "bo_basis"], out: ["status"] },
};
const field = captureFields(rule).nodes.find((node) => node.field === "actor");
assert.equal(field.capture_owner_policy, "permission");
for (const node of captureFields(rule).nodes.filter((node) =>
  ["bo_check", "bo_basis", "status"].includes(node.field),
))
  assert.equal(node.analysis_level, "advanced");
const event = (check, value, code = "completed", node = rule.id) => ({
  id: check + node,
  node,
  phase: "decision",
  inputs: { bo_check: check, bo_basis: check, actor: "Ning" },
  outputs: { value, status: code },
  basis: {},
});
const view = {
  model: { nodes: [rule], machine: {} },
  authority: { basis: {} },
  binding_status: { status: "current" },
};
const first = event("check-1", true),
  next = event("check-2", false);
assert.equal(status(rule, view, [first], "latest"), "ok");
assert.equal(status(rule, view, [first, next], "latest"), "blocked");
assert.equal(status(rule, view, [event("check-3", null, "unknown")], "latest"), "declared");
assert.equal(status(rule, view, [event("check-3", null, "error")], "latest"), "blocked");
const other = event("check-2", true, "completed", "policy:other");
assert.deepEqual(nodeEvents(rule, [first, other]), []);
assert.deepEqual(nodeEvents(field, [first, other]), []);
assert.equal(lines(rule, view, [first, other], "latest")[0].text, "Not evaluated");
assert.deepEqual(
  nodeEvents(rule, [first]),
  [first],
  "Backward replay restores its own earlier check",
);
const ordinary = { id: "ordinary" };
assert.equal(nodeEvents(ordinary, [{ node: "ordinary" }, other]).length, 1);
// Native policy declarations must not need legacy role tags to appear.
const nativeRule = { ...rule, origin: "policy-definition" };
const business = { id: "download", kind: "action", layer: "business" };
const requirement = { from: rule.id, to: business.id, type: "guard" };
const scope = matchingNodes(
  new Map([
    [rule.id, nativeRule],
    [business.id, business],
    ["unrelated", { id: "unrelated", kind: "action", layer: "business" }],
  ]),
  { model: { machine: {}, edges: [requirement] } },
  [],
  profileFor("permission"),
  () => "declared",
  [requirement],
);
assert.ok(scope.has(rule.id));
assert.ok(scope.has(business.id));
assert.ok(!scope.has("unrelated"));
// Runtime child results use data dependencies; the model retains logical guards.
const child = event("access-1", true, "completed", "policy:signed_in");
const composite = { ...rule, id: "policy:owned_session", operator: "all" };
const parent = {
  ...event("access-1", true, "completed", composite.id),
  depends: [{ event: child.id, type: "data" }],
};
const member = { from: child.node, to: parent.node, type: "guard", origin: "policy-definition" };
const edge = { id: "signed-in-to-owner", type: "guard", members: [member] };
const nodes = new Map([
  [child.node, { id: child.node }],
  [parent.node, composite],
]);
const transfers = (
  current = parent,
  relation = edge,
  inventory = nodes,
  history = [child, current],
) => transferEdges(current, history, [relation], inventory);
assert.deepEqual(transfers(), [edge.id]);
assert.deepEqual(transfers({ ...parent, outputs: { value: false, status: "completed" } }), [
  edge.id,
]);
for (const modified of [
  { ...parent, depends: [] },
  { ...parent, depends: [{ event: "unvisited", type: "data" }] },
  { ...parent, depends: [{ event: child.id, type: "control" }] },
  { ...parent, inputs: { ...parent.inputs, bo_check: "access-2" } },
  { ...parent, inputs: { ...parent.inputs, bo_basis: "another-build" } },
  { ...parent, inputs: { bo_check: "access-1" } },
])
  assert.deepEqual(transfers(modified), [], "Never infer an unwitnessed/cross-evaluation transfer");
assert.deepEqual(
  transfers(parent, { ...edge, members: [{ ...member, origin: "source-ast" }] }),
  [],
);
assert.deepEqual(
  transfers(parent, edge, new Map([[parent.node, { ...composite, operator: "predicate" }]])),
  [],
);
assert.deepEqual(
  transfers(parent, edge, new Map([[parent.node, { id: parent.node, kind: "business" }]])),
  [],
);
assert.deepEqual(
  transfers(parent, edge, nodes, [parent]),
  [],
  "A missing child event is not evidence",
);
console.log(
  "PASS: per-check rule truth, skipped conditions, replay, witnessed rule transfers and quiet metadata.",
);
