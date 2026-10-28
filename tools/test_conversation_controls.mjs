/** Conversation controls are opt-in and cannot add graph or runtime identities. */
import assert from "node:assert/strict";
import {
  createControlBridge,
  controlSelection,
} from "../skills/vibelens/assets/stategraph-viewer/conversation-controls.js";
const calls = [];
const request = async (...args) => {
  calls.push(args);
  return { ok: true, json: async () => ({}) };
};
const plain = createControlBridge({
  apply: () => assert.fail("Unscoped viewer applied a control"),
  request,
  url: "http://localhost/graph",
});
await plain.refresh({ model: {} });
assert.equal(calls.length, 0);
await plain.request("/api/preferences");
assert.equal(calls[0][0], "/api/preferences");
const token = "a".repeat(32);
const scoped = createControlBridge({
  apply: () => {},
  request,
  url: "http://localhost/graph?vl_session=" + token,
});
await scoped.request("/api/preferences", { method: "POST" });
assert.equal(calls[1][0], "/api/preferences?vl_session=" + token);
assert.throws(() => createControlBridge({ url: "http://localhost/graph?vl_session=invalid" }));
const all = new Map([
  ["group", { id: "group" }],
  ["f", { id: "f", parent: "group" }],
  ["value", { id: "value", event_node: "f", parent: "f" }],
  ["unrelated", { id: "unrelated" }],
]);
const before = structuredClone([...all]);
assert.deepEqual([...controlSelection(all, { node_ids: ["f"] })].sort(), ["f", "group", "value"]);
assert.deepEqual([...all], before);
assert.throws(() => controlSelection(all, { node_ids: ["missing"] }));
// A draft uses its declaration digest, without manufacturing a runtime revision.
for (const stage of ["design", "runtime"]) {
  let applied = 0;
  const receipts = [];
  const bridge = createControlBridge({
    url: "http://localhost/graph?vl_session=" + token,
    request: async (url, options) => {
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
            schema: "vibelens-control-plan/v1",
            action: "view",
            base: { model_revision: "draft-digest", build_id: "draft-digest" },
          },
        }),
      };
    },
    apply: async () => {
      applied++;
      return { view_id: "focus", nodes: ["upload"], events: [] };
    },
  });
  await bridge.refresh({ stage, model: {}, manifest: { build_id: "draft-digest" } });
  assert.equal(applied, stage === "design" ? 1 : 0);
  assert.equal(receipts[0].status, stage === "design" ? "applied" : "rejected");
}
console.log("PASS: opt-in polling, scoped preferences, actual identities and containment");
