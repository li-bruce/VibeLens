/** Native JavaScript capture filtering never evaluates excluded data builders. */
import assert from "node:assert/strict";
import { BOProbe } from "../skills/vibelens/scripts/bo_observer/adapters/javascript/bo_runtime.mjs";
import {
  captureRoots,
  conceptBindingId,
} from "../skills/vibelens/assets/stategraph-viewer/capture-scope.js";

const received = [];
const project = {
  project_id: "scope-test",
  model: {
    revision: "1",
    nodes: [{ id: "included", capture: { out: { value: "string" } } }, { id: "omitted" }],
  },
};
const probe = new BOProbe({ project, buildId: "build", sink: (value) => received.push(value) });
probe.bo_set_scope(["included"]);
assert.equal(
  probe.record("omitted", "enter", () => assert.fail("excluded builder ran")),
  null,
);
const first = probe.record("included", "return", () => ({ outputs: { value: "actual" } }));
assert.ok(first.endsWith(":1"));
assert.equal(await probe.flush(), true);
assert.equal(received.length, 1);
assert.equal(received[0].outputs.value, "actual");
assert.equal(probe.bo_health().filtered, 1);
assert.equal(probe.bo_health().pending, 0);
assert.equal(probe.bo_health().errors, 0);
assert.throws(() => probe.bo_set_scope(["unknown"]), /known node/);
assert.throws(() => probe.bo_set_scope("included"), /known node/);
probe.bo_set_scope(null);
assert.ok(probe.record("omitted", "enter", () => ({})));
assert.equal(await probe.flush(), true);
assert.deepEqual(
  received.map((event) => event.seq),
  [1, 2],
);
assert.equal(probe.bo_health().errors, 0);
assert.equal(
  probe.record("included", "return", () => {
    throw new ReferenceError("Private application details");
  }),
  null,
);
assert.equal(probe.bo_health().errors, 1);
assert.deepEqual(probe.bo_health().last_error, {
  stage: "capture",
  type: "ReferenceError",
  node: "included",
  phase: "return",
});
assert.ok(!JSON.stringify(probe.bo_health()).includes("Private application details"));
const failedDelivery = new BOProbe({
  project,
  buildId: "build",
  sink: () => {
    throw new Error("Private transport details");
  },
});
assert.ok(failedDelivery.record("included", "enter", () => ({})));
assert.equal(await failedDelivery.flush(), true);
assert.equal(failedDelivery.bo_health().errors, 1);
assert.deepEqual(failedDelivery.bo_health().last_error, { stage: "transport", type: "Error" });

// A queued snapshot belongs to the flush prefix; later traffic does not.
let releaseSnapshot, releaseSuffix, enteredSnapshot, enteredSuffix;
const snapshotReady = new Promise((resolve) => (enteredSnapshot = resolve));
const suffixReady = new Promise((resolve) => (enteredSuffix = resolve));
const snapshotGate = new Promise((resolve) => (releaseSnapshot = resolve));
const suffixGate = new Promise((resolve) => (releaseSuffix = resolve));
const ordered = [];
const busy = new BOProbe({
  project,
  buildId: "build",
  sink: async (value, kind) => {
    if (kind === "snapshots") {
      enteredSnapshot();
      await snapshotGate;
    }
    if (value.outputs?.value === "later") {
      enteredSuffix();
      await suffixGate;
    }
    ordered.push(kind);
  },
});
const evidence = busy.record("included", "enter", () => ({}));
assert.equal(busy.snapshot("item", "pending", {}, 1, evidence), true);
await snapshotReady;
assert.equal(await busy.flush(10), false, "Undelivered snapshots cannot be acknowledged");
const settling = busy.flush(1000);
busy.record("included", "return", () => ({ outputs: { value: "later" } }));
releaseSnapshot();
await suffixReady;
assert.equal(await settling, true, "Future requests do not extend the settled prefix");
assert.deepEqual(ordered, ["events", "snapshots"]);
assert.equal(busy.bo_health().flush_target, 2);
assert.ok(busy.bo_health().pending > 0);
releaseSuffix();
assert.equal(await busy.flush(), true);
assert.deepEqual(ordered, ["events", "snapshots", "events"]);
assert.equal(busy.bo_health().errors, 0);

console.log(
  "PASS: actual JavaScript owner filtering, safe empty captures, exact sequences and restored full capture.",
);

// A concept and its capture owner have different identities. Presentation maps
// can locate an owner but must never rename a real event or invent a call.
const concept = { id: "share", kind: "action", layer: "business", origin: "concept-design" };
const native = { id: "native:share", kind: "function" };
const binding = {
  id: conceptBindingId(concept.id, native.id),
  from: concept.id,
  to: native.id,
  type: "maps",
  code_relation: "maps",
  mapping_role: "implements",
  origin: "concept-binding",
  evidence_kind: "binding",
  observed: false,
};
const captureView = {
  model: { nodes: [native], edges: [], machine: { execution: { parent: native.id } } },
  concept_structure: {
    schema: "bo-concept-projection/v1",
    stage: "bound",
    nodes: [concept],
    edges: [binding],
  },
};
const untouched = JSON.stringify(captureView);
assert.deepEqual(captureRoots(captureView, concept), [native.id]);
assert.deepEqual(captureRoots(captureView, { id: "ref", referenceOf: concept.id }), [native.id]);
assert.deepEqual(captureRoots(captureView, native), [native.id]);
for (const changed of [
  { id: "unverified-binding" },
  { type: "flow" },
  { code_relation: "calls" },
  { mapping_role: "summary" },
  { origin: "concept-design" },
  { evidence_kind: "conceptual" },
  { observed: true },
  { from: native.id, to: concept.id },
  { to: "absent" },
]) {
  const invalid = structuredClone(captureView);
  invalid.concept_structure.edges = [{ ...binding, ...changed }];
  assert.deepEqual(captureRoots(invalid, concept), [], JSON.stringify(changed));
}
const draft = structuredClone(captureView);
draft.concept_structure.stage = "draft";
assert.deepEqual(captureRoots(draft, concept), []);
assert.deepEqual(
  captureRoots(captureView, { id: "unbound", origin: "concept-design", kind: "state" }),
  [],
);
assert.equal(JSON.stringify(captureView), untouched);
const captured = [];
const scoped = new BOProbe({
  project: { project_id: "concept-scope", model: captureView.model },
  buildId: "build",
  sink: (event) => captured.push(event),
});
scoped.bo_set_scope(captureRoots(captureView, concept));
scoped.record(native.id, "enter", () => ({}));
await scoped.flush();
assert.equal(captured[0].node, native.id);
assert.equal(captured.length, 1);
console.log(
  "PASS: bound concepts resolve exact native capture owners without rewriting event identities.",
);
