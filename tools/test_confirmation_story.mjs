/** The concise story overview must retain evidence for each summarized relation. */
import assert from "node:assert/strict";
import fs from "node:fs";
import { confirmationModel } from "../docs/site/case-confirmation-model.mjs";
const artifact = JSON.parse(
  fs.readFileSync(new URL("../docs/site/case-data/v1.json", import.meta.url)),
);
const before = JSON.stringify(artifact);
const edges = new Map(artifact.view.model.edges.map((edge) => [edge.id, edge]));
for (const language of ["en", "zh-CN"]) {
  for (const tab of ["business", "rules"]) {
    const overview = confirmationModel(artifact, tab, language);
    for (const edge of overview.edges) {
      const path = edge.witnesses.map((id) => edges.get(id));
      assert.ok(path.length && path.every(Boolean));
      assert.equal(path[0].from, edge.from);
      assert.equal(path.at(-1).to, edge.to);
      for (let index = 1; index < path.length; index++)
        assert.equal(path[index - 1].to, path[index].from);
    }
  }
  const state = confirmationModel(artifact, "states", language);
  assert.deepEqual(
    state.nodes.map((node) => node.id),
    artifact.view.model.machine.states,
  );
  const transitions = artifact.view.model.machine.transitions;
  assert.equal(
    state.edges.length,
    transitions.reduce(
      (sum, item) => sum + (Array.isArray(item.source) ? item.source.length : 1),
      0,
    ),
  );
  assert.ok(state.edges.some((edge) => edge.condition.includes("NOT has_recipients")));
  assert.ok(state.edges.some((edge) => edge.from === "shared" && edge.to === "shared"));
}
assert.equal(JSON.stringify(artifact), before, "Presentation must not mutate archived facts");
console.log(
  "PASS: business path witnesses, shared policy DAG, complete state transition alternatives, immutable recording.",
);
