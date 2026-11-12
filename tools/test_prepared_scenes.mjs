/** Presentation must be fast without changing the confirmed model or runtime facts. */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { compileScenes } from "./build_demo_scenes.mjs";
import { confirmationModel } from "../docs/site/case-confirmation-model.mjs";
import { curvePath, edgePoints } from "../docs/site/case-graph-geometry.mjs";
import { transferEdges } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import { presentCase } from "../docs/site/case-copy.mjs";

const read = (name) => JSON.parse(readFileSync(new URL(`../docs/site/${name}`, import.meta.url)));
const generated = read("case-preview/prepared.json");
let total = 0;
for (const version of [1, 2]) {
  const original = read(`case-data/v${version}.json`),
    before = JSON.stringify(original);
  const compiled = compileScenes(original);
  assert.deepEqual(
    generated.versions[version - 1],
    compiled,
    "Published data must match the compiler",
  );
  assert.equal(JSON.stringify(original), before, "No source or captured fact may be rewritten");
  const model = original.view.model;
  // Regression: the old hand-maintained list omitted an existing, declared state.
  assert.ok(!original.story.states.includes("state_empty"));
  assert.deepEqual(presentCase(original).story.states, [
    "state_empty",
    "state_private",
    "state_shared",
  ]);
  for (const tab of ["business", "states", "rules"])
    for (const language of ["en", "zh-CN"]) {
      const confirmed = confirmationModel(original, tab, language),
        graph = compiled.scenes[tab];
      assert.deepEqual(compiled.concepts[tab][language], confirmed);
      assert.deepEqual(
        graph.nodes.map((n) => [n.id, n.labels[language === "en" ? 0 : 1]]),
        confirmed.nodes.map((n) => [n.id, n.label]),
      );
      assert.deepEqual(
        graph.edges.map((e) => [e.from, e.to, e.witnesses, e.condition]),
        confirmed.edges.map((e) => [e.from, e.to, e.witnesses, e.condition]),
      );
    }
  const knownNodes = new Map([...model.nodes, ...original.code.nodes].map((n) => [n.id, n]));
  const sourceEdges = [...model.edges, ...original.code.edges];
  const detailIds = new Set(compiled.scenes.data.nodes.map((node) => node.id));
  const detailEdges = new Set(compiled.scenes.data.edges.map((edge) => edge.id));
  for (const edge of sourceEdges)
    if (
      detailIds.has(edge.from) &&
      detailIds.has(edge.to) &&
      (edge.data_relation === "writes" || ["maps", "defines"].includes(edge.code_relation))
    )
      assert.ok(detailEdges.has(edge.id), "Include storage writes and physical source bindings");
  const edges = new Map(
    Object.values(compiled.scenes)
      .flatMap((g) => g.edges)
      .map((e) => [e.id, e]),
  );
  for (const graph of Object.values(compiled.scenes)) {
    assert.ok(graph.nodes.length <= 25, "The walkthrough cannot grow into the whole project");
    const ids = new Set(graph.nodes.map((n) => n.id)),
      points = new Map(graph.nodes.map((n) => [n.id, n]));
    assert.equal(ids.size, graph.nodes.length);
    for (const node of graph.nodes) {
      assert.ok(knownNodes.has(node.id) || node.field, "Stable node or recorded-field identity");
      assert.ok(Number.isFinite(node.x) && Number.isFinite(node.y));
    }
    for (const edge of graph.edges) {
      assert.ok(ids.has(edge.from) && ids.has(edge.to));
      assert.ok(edge.witnesses.length);
      assert.ok(!curvePath(edgePoints(edge, points)).includes("NaN"));
    }
  }
  const states = compiled.scenes.states,
    points = new Map(states.nodes.map((n) => [n.id, n]));
  assert.equal(
    new Set(states.edges.map((e) => curvePath(edgePoints(e, points)))).size,
    states.edges.length,
    "Distinct transitions must not overlap exactly",
  );
  const events = new Map(original.recording.events.map((e, i) => [e.id, { event: e, index: i }]));
  for (const step of compiled.steps) {
    const { event, index } = events.get(step.id);
    assert.equal(step.node, event.node);
    assert.deepEqual(step.inputs, event.inputs);
    assert.deepEqual(step.outputs, event.outputs);
    for (const [id, sample] of Object.entries(step.samples)) {
      const [, owner, direction, field] = id.split(":"),
        captured = events.get(sample.eventId);
      assert.ok(captured.index <= index, "Do not show a value from the future");
      assert.equal(captured.event.node, owner);
      assert.deepEqual(
        sample.value,
        captured.event[direction === "in" ? "inputs" : "outputs"][field],
      );
    }
    const witnessed = new Set(
      transferEdges(event, original.recording.events, sourceEdges, knownNodes),
    );
    for (const id of step.transfers) {
      const edge = edges.get(id);
      assert.ok(edge, "Every moving arrow belongs to a prepared relationship");
      if (edge.type === "transition") {
        assert.equal(edge.event, step.node);
        assert.equal(edge.from, `state_${step.previous}`);
        assert.equal(edge.to, `state_${step.state}`);
        assert.equal(step.state, event.outputs.state);
      } else if (edge.id.startsWith("model-event:")) {
        assert.equal(edge.event, step.node);
        assert.equal(edge.to, `state_${event.outputs.state}`);
      } else if (edge.field)
        assert.ok(Object.hasOwn(event[edge.direction === "in" ? "inputs" : "outputs"], edge.field));
      else
        assert.ok(
          edge.witnesses.length === 1 && witnessed.has(edge.witnesses[0]),
          "No invented call animation",
        );
    }
  }
  for (const id of original.story.actions.flatMap((a) => a.event_ids))
    assert.ok(compiled.steps.some((e) => e.id === id));
  const inspected = compiled.steps.find((e) => e.id === compiled.inspection);
  assert.equal(inspected.outputs.removed, version === 2);
  assert.equal(inspected.state, version === 2 ? "private" : "shared");
  assert.equal(inspected.samples["field:db_delete_share:out:rows"].value, version === 2 ? 1 : 0);
  const source = read(`case-preview/source-v${version}.json`);
  assert.equal(source.source, original.sources[source.path]);
  assert.equal(createHash("sha256").update(source.source).digest("hex"), compiled.source.sha256);
  assert.ok(
    source.source
      .split(/\r?\n/)
      [compiled.source.highlight - 1].includes(original.story.source_excerpt),
  );
  const broken = structuredClone(original);
  broken.view.model.nodes = broken.view.model.nodes.filter((n) => n.id !== "state_empty");
  assert.throws(() => compileScenes(broken), /Missing declared state node/);
  total += compiled.steps.length;
}
assert.ok(
  Buffer.byteLength(JSON.stringify(generated)) < 200000,
  "Keep both scene versions under 200 KB",
);
console.log(
  `PASS: 18 prepared graphs, 12 concept comparisons, ${total} original events, source hashes, state completeness, separate arcs and evidence-backed animation.`,
);
