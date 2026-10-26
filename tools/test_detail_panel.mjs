/** A slow source response must not populate the cache of a newer build. */
import assert from "node:assert/strict";
import { createDetailPanel } from "../skills/vibelens/assets/stategraph-viewer/detail-panel.js";
let resolve;
const oldFetch = globalThis.fetch;
const state = {
  selected: "a",
  mode: "source",
  version: "live",
  recording: null,
  graph: { all: new Map([["a", { id: "a" }]]) },
  view: {
    stage: "runtime",
    manifest: { build_id: "old", bindings: { a: { path: "app.py", line: 1 } } },
  },
};
const panel = createDetailPanel({
  read: () => state,
  point: () => ({ x: 0, y: 0 }),
  element: () => {
    throw Error("Obsolete responses must not touch the panel");
  },
});
let requests = 0;
try {
  globalThis.fetch = () => {
    requests++;
    return new Promise((r) => (resolve = r));
  };
  const first = panel.load();
  state.view = {
    stage: "runtime",
    manifest: { build_id: "new", bindings: { a: { path: "app.py", line: 1 } } },
  };
  resolve({ ok: true, json: async () => ({ build_id: "old", source: "obsolete source" }) });
  await first;
  state.view = {
    stage: "runtime",
    manifest: { build_id: "old", bindings: { a: { path: "app.py", line: 1 } } },
  };
  const second = panel.load();
  assert.equal(requests, 2, "An obsolete response was not cached");
  state.selected = "another-node";
  resolve({ ok: false });
  await second;
  panel.clear();
} finally {
  globalThis.fetch = oldFetch;
}
console.log("PASS: obsolete source responses are discarded and a changed selection is untouched.");
