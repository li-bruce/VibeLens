/** Rule truth, shared ownership and metadata must stay honest across requests. */
import assert from "node:assert/strict";
import { captureFields } from "../skills/vibelens/assets/stategraph-viewer/capture-fields.js";
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
console.log("PASS: per-check rule truth, skipped conditions, replay and quiet metadata.");
