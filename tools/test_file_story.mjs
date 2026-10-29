/** Application previews follow recorded event order, including backward seeks. */
import assert from "node:assert/strict";
import { applicationAt } from "../docs/site/case-application.mjs";
import { chapters, messages } from "../docs/site/case-messages.mjs";
import { expandCodeSlice } from "../docs/site/case-code.mjs";

const artifact = {
  recording: {
    events: [{ id: "start" }, { id: "upload" }, { id: "share" }, { id: "revoke" }],
  },
  application_frames: [
    {
      event_id: "upload",
      images: { en: "upload.png", "zh-CN": "upload-zh.png" },
    },
    { event_id: "revoke", images: { en: "revoke.png" } },
  ],
};
assert.equal(applicationAt(artifact, "start"), null);
assert.equal(applicationAt(artifact, "missing"), null);
assert.equal(applicationAt(artifact, "share", "zh-CN").image, "upload-zh.png");
assert.equal(applicationAt(artifact, "revoke", "zh-CN").image, "revoke.png");
assert.equal(applicationAt(artifact, "upload").image, "upload.png");
assert.deepEqual(
  chapters.map((chapter) => chapter.id),
  ["foundation", "run", "drill", "iterate", "verify"],
);
for (const chapter of chapters) {
  assert.equal(!!chapter.dialogue, chapter.surface === "codex");
  for (const title of chapter.title) assert.ok(!/[.。]$/.test(title));
}
assert.ok(chapters[0].dialogue[1][1][1].includes("取消共享"));
for (const pair of Object.values(messages)) assert.equal(pair.length, 2);
const code = {
  nodes: [{ id: "file" }, { id: "f", parent: "file" }, { id: "g", parent: "file" }],
  edges: [{ id: "call", from: "f", to: "g", type: "call" }],
  bindings: { f: { path: "app.py" } },
};
const slice = {
  encoding: "code-slice-refs/v1",
  node_ids: ["f", "g"],
  boundary_ids: ["g"],
  edge_ids: ["call"],
};
const restored = expandCodeSlice(code, slice);
assert.equal(restored.nodes[0].parent, undefined);
assert.equal(restored.nodes[1].code_boundary, true);
restored.nodes[0].label = "changed";
assert.equal(
  code.nodes[1].label,
  undefined,
  "Local source inspection cannot mutate the full index",
);
assert.throws(() => expandCodeSlice(code, { ...slice, node_ids: ["missing"] }), /Missing recorded/);
assert.deepEqual(restored.edges, code.edges);
console.log(
  "PASS: event-bound application captures, backward replay and separate development dialogue.",
);
