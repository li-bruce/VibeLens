/** A slow source response must not populate the cache of a newer build. */
import assert from "node:assert/strict";
import { createDetailPanel } from "../skills/vibelens/assets/stategraph-viewer/detail-panel.js";
import { conceptDefinitionElement } from "../skills/vibelens/assets/stategraph-viewer/concept-details.js";
import { previewChangeIndices } from "../skills/vibelens/assets/stategraph-viewer/change-panel.js";
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
  resolve({
    ok: true,
    json: async () => ({ build_id: "old", source: "obsolete source" }),
  });
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

const fakeDocument = {
  createElement(tag) {
    return {
      tag,
      dataset: {},
      children: [],
      append(...children) {
        this.children.push(...children);
      },
      addEventListener(name, callback) {
        this[name] = callback;
      },
    };
  },
};
const definition = {
  payload: { recipient: "string" },
  source: ["inactive"],
  dest: "active",
  conditions: ["is_owner", "recipient_exists"],
  read_basis: { timing: "commit", scope: "grant" },
  note: "<script>throw Error('text')</script>",
};
const node = { id: "transition:share", concept_definition: definition };
const original = JSON.stringify(node);
let opened;
const element = conceptDefinitionElement(node, {
  document: fakeDocument,
  onToggle: (value) => (opened = value),
});
assert.equal(element.tag, "details");
assert.equal(element.dataset.nodeId, node.id);
assert.equal(element.open, false);
assert.equal(element.children[1].tag, "pre");
assert.deepEqual(JSON.parse(element.children[1].textContent), definition);
assert.equal(element.children[1].innerHTML, undefined, "Authored text never becomes HTML");
element.open = true;
element.toggle();
assert.equal(opened, true);
assert.equal(conceptDefinitionElement({ id: "native" }), null);
assert.equal(JSON.stringify(node), original);
console.log(
  "PASS: inspectable typed concept payloads, guard order/read basis, safe text and preserved identity.",
);

const changes = [
  { kind: "value", field: "actor", after: "recipient" },
  { kind: "value", field: "rows", after: 0 },
  { kind: "state", field: "status", before: "shared", after: "private" },
  { kind: "call", field: "phase", after: "returned" },
  { kind: "business", field: "flow", after: "revoked" },
  { kind: "decision", field: "allowed", after: false },
];
const unchanged = JSON.stringify(changes);
assert.deepEqual([...previewChangeIndices(changes)], [4, 2]);
assert.deepEqual([...previewChangeIndices(changes, 3)], [4, 2, 5]);
assert.deepEqual([...previewChangeIndices(changes.slice(0, 2))], [0, 1]);
assert.equal(previewChangeIndices([]).size, 0);
assert.equal(
  JSON.stringify(changes),
  unchanged,
  "The preview never sorts or removes recorded rows",
);
console.log(
  "PASS: bounded change preview prioritizes state and decisions without mutating evidence.",
);
