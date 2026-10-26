/** Prevent event metadata from masquerading as lexical parameters or commit facts. */
import assert from "node:assert/strict";
import { captureFields } from "../skills/vibelens/assets/stategraph-viewer/capture-fields.js";
import { sourceBinding } from "../skills/vibelens/assets/stategraph-viewer/graph-core.js";
import { sourceLines } from "../skills/vibelens/assets/stategraph-viewer/source-view.js";
import {
  cleanLayers,
  layerOf,
  layerSlice,
} from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";

const owner = {
  id: "save",
  data_role: "query",
  data_metadata: { action: "write" },
  capture: { out: { status: "string", committed: "boolean" } },
};
const fields = captureFields(owner);
assert.ok(
  !fields.nodes.some((n) => n.field === "committed"),
  "Only transaction operations can declare commit outcomes",
);
const status = fields.nodes[0];
assert.equal(layerOf(owner), "operations");
assert.equal(layerOf(status), "operations");
assert.equal(layerOf({ kind: "function" }), "execution");
assert.equal(layerOf({ code_role: "parameter" }), "code");
const view = { manifest: { bindings: { save: { path: "gallery.py", line: 2, end_line: 3 } } } };
const all = new Map([
  [owner.id, owner],
  [status.id, status],
]);
const binding = sourceBinding(view, all, status.id);
assert.equal(binding.provenance, "capture-owner");
assert.ok(
  sourceLines("# file\ndef save(rows):\n    return rows", binding).every(
    (row) => !row.parts.some((p) => p.marked),
  ),
  "An adapter field must not highlight an unrelated function as a parameter",
);
view.manifest.bindings[status.id] = {
  path: "adapter.py",
  line: 1,
  selection: { line: 1, end_line: 1, column: 0, end_column: 6 },
};
assert.ok(
  sourceLines("status = result", sourceBinding(view, all, status.id))[0].parts.some(
    (p) => p.marked,
  ),
  "An explicit lexical binding still highlights its exact token",
);
assert.equal(cleanLayers().camera, "top");
assert.deepEqual(
  cleanLayers({ only: "state" }).visible,
  ["state"],
  "Migrate saved single-layer views",
);
const graph = {
  boxes: [
    { id: "s", node: { kind: "state" } },
    { id: "f", node: { kind: "function" } },
    { id: "q", node: owner },
  ],
  edges: [
    { from: "s", to: "f" },
    { from: "f", to: "q" },
  ],
  regions: [],
};
for (const enabled of [false, true]) {
  const slice = layerSlice(graph, cleanLayers({ enabled, visible: ["state", "execution"] }));
  assert.deepEqual(
    slice.boxes.map((b) => b.id),
    ["s", "f"],
  );
  assert.equal(slice.edges.length, 1);
}
assert.equal(layerSlice(graph, cleanLayers({ visible: [] })).boxes.length, 0);
console.log("Viewer semantic regressions passed");
