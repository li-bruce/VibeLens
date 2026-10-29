/** Conversation focus must resolve containment from the canonical model. */
import assert from "node:assert/strict";
import * as control from "../skills/vibelens/assets/stategraph-viewer/conversation-controls.js";

const canonical = [
  { id: "rules", kind: "decision" },
  { id: "read", kind: "decision", parent: "rules" },
  { id: "unrelated", kind: "decision" },
];
// A one-hop display boundary omits its original parent to remain visible in a
// business-only view. That display choice must not become control-model truth.
const displayed = new Map([
  ["rules", canonical[0]],
  ["read", { id: "read", kind: "decision", filter_context: true }],
  ["input", { id: "input", kind: "data", event_node: "read", parent: "read" }],
  ["unrelated", canonical[2]],
]);
const before = structuredClone([...displayed]);
const plan = { node_ids: ["read"], filters: { nodes: ["decision", "data"] } };
assert.ok(
  control.controlSelection(displayed, plan, canonical).has("rules"),
  "A display boundary must retain its canonical parent in a new control selection",
);
const projection = control.controlProjection(displayed, plan, canonical);
assert.deepEqual([...projection.keep].sort(), ["input", "read", "rules"]);
assert.deepEqual(projection.expanded.sort(), ["read", "rules"]);
assert.equal(projection.nodes.get("read").parent, "rules");
assert.equal(projection.nodes.get("read").filter_context, true);
assert.deepEqual([...displayed], before, "The current display projection must remain unchanged");
assert.equal(canonical[1].parent, "rules");

const nested = [
  { id: "outer", kind: "action", layer: "business" },
  { id: "inner", kind: "action", layer: "business", parent: "outer" },
];
const fields = new Map([
  ...nested.map((node) => [node.id, node]),
  ["value", { id: "value", kind: "data", parent: "inner", event_node: "inner" }],
]);
const business = control.controlProjection(
  fields,
  {
    node_ids: ["inner"],
    filters: { nodes: ["business"] },
  },
  nested,
);
assert.deepEqual(
  business.expanded,
  ["outer"],
  "Expand the requested nested business path without opening capture fields",
);
assert.ok(!business.keep.has("unrelated"));

const advanced = control.controlProjection(
  new Map(),
  {
    node_ids: ["source"],
    filters: { nodes: ["function"] },
  },
  [{ id: "source", origin: "source-ast", kind: "action" }],
);
assert.equal(
  advanced.advanced,
  true,
  "An explicitly requested source node may enable advanced detail",
);
assert.throws(() =>
  control.controlProjection(
    displayed,
    { node_ids: ["missing"], filters: { nodes: [] } },
    canonical,
  ),
);
assert.throws(() => control.requireVisibleControlNodes({ byId: new Map() }, plan), /read/);
assert.doesNotThrow(() =>
  control.requireVisibleControlNodes({ byId: new Map([["read", {}]]) }, plan),
);
const receipts = [];
const bridge = control.createControlBridge({
  url: "http://localhost/graph?vl_session=" + "a".repeat(32),
  request: async (_url, options) => {
    if (options?.method === "POST") {
      receipts.push(JSON.parse(options.body));
      return { ok: true };
    }
    return {
      ok: true,
      json: async () => ({
        active: true,
        revision: 1,
        plan: {
          ...plan,
          schema: "vibelens-control-plan/v1",
          action: "view",
          base: { model_revision: "same", build_id: "same" },
        },
      }),
    };
  },
  apply: async (selected) => {
    control.requireVisibleControlNodes({ byId: new Map() }, selected);
    throw Error("An invisible selection must never reach the success path");
  },
});
await bridge.refresh({ model: { revision: "same" }, manifest: { build_id: "same" } });
assert.equal(receipts.length, 1);
assert.equal(receipts[0].status, "rejected");
assert.match(receipts[0].error, /read/);
console.log(
  "PASS: canonical control ancestry, immutable boundaries, nested expansion and visible-node admission.",
);
