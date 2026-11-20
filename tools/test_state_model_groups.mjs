/** A model folds its declarations together without changing their meanings or facts. */
import assert from "node:assert/strict";
import { applyConceptContainment } from "../skills/vibelens/assets/stategraph-viewer/concept-containment.js";

const concept = (id, concept_kind, extra = {}) => ({
  id,
  concept_kind,
  layer: "state",
  origin: "concept-design",
  ...extra,
});
const nodes = [
  concept("grant", "state_model", { state_model_id: "grant-native" }),
  concept("job", "state_model", { state_model_id: "job-native" }),
  concept("active", "state"),
  concept("nested", "state"),
  concept("share", "event"),
  concept("owner", "guard"),
  concept("write", "logical_effect"),
  concept("grant-change", "transition"),
  {
    id: "physical-active",
    kind: "state",
    layer: "state",
    machine_state: true,
    state_model_id: "grant-native",
    value: "active",
  },
  {
    id: "physical-job",
    kind: "state",
    layer: "state",
    machine_state: true,
    state_model_id: "job-native",
    value: "active",
  },
  { id: "function", kind: "function", layer: "implementation", state_model_id: "grant-native" },
];
const relation = (id, from, to, type) => ({ id, from, to, type, origin: "concept-design" });
const edges = [
  relation("contains-state", "grant", "active", "contains"),
  relation("contains-child", "active", "nested", "contains"),
  relation("event", "grant", "share", "declares_event"),
  relation("guard", "grant", "owner", "declares_guard"),
  relation("effect", "grant", "write", "declares_effect"),
  relation("request", "share", "grant-change", "requests_transition"),
  relation("uses", "grant-change", "owner", "guarded_by"),
];
const original = JSON.stringify({ nodes, edges });
const all = new Map(nodes.map((node) => [node.id, node]));
applyConceptContainment(all, edges);
for (const id of ["active", "share", "owner", "write", "grant-change", "physical-active"])
  assert.equal(all.get(id).parent, "grant", `${id} stays within its declared state model`);
assert.equal(all.get("nested").parent, "active", "Actual nested state wins over model grouping");
assert.equal(all.get("physical-job").parent, "job", "Equal local state values never join models");
assert.equal(all.get("function").parent, undefined, "Model binding is not source containment");
assert.equal(all.get("share").display_parent_kind, "state_model_membership");
assert.equal(all.get("physical-active").display_parent_kind, "state_model_membership");
assert.equal(
  JSON.stringify({ nodes, edges }),
  original,
  "Only the local display inventory changes",
);
assert.equal(all.size, nodes.length, "Concept and native IDs remain separate");
assert.ok(
  [...all.values()].every((node) => !node.lifecycle),
  "Grouping creates no lifetime",
);

// A shared or malformed declaration keeps its explicit links instead of acquiring
// an arbitrary owner from array ordering. Existing source ancestry also wins.
const shared = new Map(
  [
    ...nodes,
    concept("owner-two", "state_model", {
      state_model_id: "grant-native",
    }),
    concept("preparented", "event", { parent: "job" }),
  ].map((node) => [node.id, node]),
);
applyConceptContainment(shared, [
  ...edges,
  relation("other-event", "job", "share", "declares_event"),
  relation("existing", "grant", "preparented", "declares_event"),
]);
assert.equal(shared.get("share").parent, undefined);
assert.equal(shared.get("grant-change").parent, undefined);
assert.equal(shared.get("physical-active").parent, undefined);
assert.equal(shared.get("preparented").parent, "job");
console.log("State-model declaration grouping checks passed");
