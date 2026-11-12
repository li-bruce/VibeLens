/** A guided presentation must preserve the evidence behind every selected step. */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  guidedIds,
  guidedViewIds,
  recordingWindow,
  eventAtProgress,
  depthGuide,
  investigationPositions,
} from "../docs/site/case-guide-model.mjs";
import { chapters } from "../docs/site/case-messages.mjs";
import { timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";

for (const version of [1, 2]) {
  const artifact = JSON.parse(
    readFileSync(new URL(`../docs/site/case-data/v${version}.json`, import.meta.url), "utf8"),
  );
  const before = JSON.stringify(artifact);
  const events = timeline(artifact.recording);
  const { start, end } = recordingWindow(events, artifact.story);
  assert.ok(start < end);
  assert.equal(eventAtProgress(events, artifact.story, -10), start);
  assert.equal(eventAtProgress(events, artifact.story, 140), end);
  assert.ok(
    eventAtProgress(events, artifact.story, 55) > eventAtProgress(events, artifact.story, 35),
  );
  const knownIds = new Set(
    [...artifact.view.model.nodes, ...artifact.code.nodes].map((node) => node.id),
  );
  for (const id of guidedIds(artifact.story))
    assert.ok(knownIds.has(id), `Unknown overview node ${id}`);
  for (const [id, position] of Object.entries(investigationPositions(artifact.story))) {
    assert.ok(knownIds.has(id) || id.startsWith("field:"), `Unknown layout anchor ${id}`);
    assert.ok(Number.isFinite(position.x) && Number.isFinite(position.y));
  }
  for (const depth of depthGuide) {
    for (const id of guidedIds(artifact.story, depth.id))
      assert.ok(knownIds.has(id) || id.startsWith("field:"), `Unknown detail node ${id}`);
  }
  const inspect = events.find((event) => event.id === artifact.story.inspection_event);
  assert.deepEqual(
    guidedViewIds(artifact.story, { inputs: false }),
    guidedIds(artifact.story, "operation"),
  );
  assert.deepEqual(
    guidedViewIds(artifact.story, { effects: true }),
    guidedIds(artifact.story, "data"),
  );
  const noStates = guidedViewIds(artifact.story, { states: false });
  assert.ok(artifact.story.states.every((id) => !noStates.has(id)));
  assert.ok(!guidedViewIds(artifact.story, { effects: true }).has("http_revoke"));
  assert.equal(inspect.outputs.removed, version === 2);
  assert.equal(inspect.outputs.grant_count, version === 2 ? 0 : 1);
  assert.equal(inspect.outputs.state, version === 2 ? "private" : "shared");
  assert.equal(JSON.stringify(artifact), before, "Scope selection cannot rewrite facts");
  assert.throws(
    () => recordingWindow(events, { actions: [{ event_ids: ["missing"] }] }),
    /missing/,
  );
}
assert.equal(chapters.find((item) => item.id === "build").surface, "codex");
assert.equal(chapters.find((item) => item.id === "run").surface, "vibelens");
assert.equal(chapters.find((item) => item.id === "drill").surface, "vibelens");
assert.deepEqual(
  depthGuide.map((item) => item.id),
  ["operation", "inputs", "data"],
);
console.log(
  "PASS: six-stage journey, progressive scopes, captured playback bounds and unchanged evidence",
);
