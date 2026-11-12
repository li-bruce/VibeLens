/** Verify exact reconstruction and the lightweight story's confirmation/replay contracts. */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { unpackCase } from "../docs/site/case-data.mjs";
import { confirmationModel } from "../docs/site/case-confirmation-model.mjs";
import { applicationAt } from "../docs/site/case-application.mjs";

const read = async (file) =>
  JSON.parse(await readFile(new URL("../docs/site/" + file, import.meta.url)));
const summary = await read("case-preview/story.json");
assert.equal(summary.schema, "vibelens-story-summary/v1");
for (const version of [1, 2]) {
  const original = await read(`case-data/v${version}.json`);
  const restored = unpackCase(await read(`case-preview/v${version}.json`));
  assert.deepEqual(restored, original, `All facts, source and IDs survive transport v${version}`);
  assert.notEqual(restored.view.events, restored.recording.events, "Independent mutation scopes");
  const shell = summary.versions[version - 1];
  for (const language of ["en", "zh-CN"]) {
    for (const tab of ["business", "states", "rules"])
      assert.deepEqual(
        confirmationModel(shell, tab, language),
        confirmationModel(original, tab, language),
      );
    for (const event of original.recording.events)
      assert.deepEqual(
        applicationAt(shell, event.id, language),
        applicationAt(original, event.id, language),
      );
  }
  assert.equal(
    shell.view.model.nodes.find((n) => n.id === shell.story.inspection_node).source.path,
    original.view.model.nodes.find((n) => n.id === original.story.inspection_node).source.path,
  );
}
assert.throws(() => unpackCase({ schema: "wrong" }), /Unsupported/);
assert.throws(
  () =>
    unpackCase({
      schema: "vibelens-case-transport/v1",
      data: { a: null },
      aliases: [[["a"], ["__proto__"]]],
    }),
  /Invalid/,
);
console.log(
  "PASS: exact transport, independent copies, both languages, every screenshot position and all three confirmation models",
);
