/** Verify the public projection against independently retained raw native facts. */
import assert from "node:assert/strict";
import fs from "node:fs";
import { gunzipSync } from "node:zlib";
import { createHash } from "node:crypto";
import { compileForest } from "./forest_preview.mjs";
import { preparedNodeActive } from "../docs/site/case-activity.mjs";
const root = new URL("../docs/site/forest-data/", import.meta.url);
const manifest = JSON.parse(fs.readFileSync(new URL("manifest.json", root)));
const results = [];
for (const [epoch, expected] of Object.entries(manifest.epochs)) {
  const raw = gunzipSync(fs.readFileSync(new URL(epoch + ".json.gz", root)));
  assert.equal(createHash("sha256").update(raw).digest("hex"), expected.raw_sha256);
  const record = JSON.parse(raw),
    model = record.context.model;
  const preview = JSON.parse(fs.readFileSync(new URL(epoch + ".json", root)));
  assert.equal(preview.build_id, record.build_id);
  assert.equal(preview.recording_id, record.id);
  assert.equal(record.gaps.length, 0);
  assert.deepEqual(Object.keys(preview.networks.states), Object.keys(model.machines));
  for (const [id, machine] of Object.entries(model.machines)) {
    const graph = preview.networks.states[id];
    assert.deepEqual(new Set(graph.nodes.map((node) => node.value)), new Set(machine.values));
    assert.equal(graph.edges.length, machine.transitions.length);
    for (const edge of graph.edges) {
      const transition = machine.transitions[edge.machine_transition.index];
      const from = graph.nodes.find((node) => node.id === edge.from);
      const to = graph.nodes.find((node) => node.id === edge.to);
      assert.equal(from.value, transition.source);
      assert.equal(to.value, transition.dest);
      assert.equal(edge.event, transition.trigger);
      assert.deepEqual(edge.conditions, transition.conditions);
      assert.deepEqual(edge.unless, transition.unless || []);
    }
  }
  const networks = record.context.concept_structure.networks.filter(
    (item) => item.layer === "business",
  );
  assert.equal(Object.keys(preview.networks.business).length, networks.length);
  for (const network of networks) {
    const graph = preview.networks.business[network.id];
    assert.deepEqual(
      new Set(graph.nodes.map((node) => node.id)),
      new Set(network.nodes.filter((id) => model.concepts.business[id])),
    );
    assert.ok(graph.edges.every((edge) => network.edges.includes(edge.id)));
    assert.deepEqual(
      new Set(graph.edges.map((edge) => edge.id)),
      new Set(network.edges.filter((id) => !id.startsWith("business-contains:"))),
      "Every declared business route survives; the network itself supplies containment",
    );
  }
  const events = new Map(record.events.map((event) => [event.id, event]));
  let motions = 0;
  for (const step of preview.steps) {
    const event = events.get(step.id);
    assert(event, "A rendered step needs its actual recorded event");
    assert.equal(step.node, event.node);
    assert.equal(step.observed_at, event.observed_at);
    assert.deepEqual(step.outputs, event.outputs);
    if (step.start_event_id) {
      const start = events.get(step.start_event_id);
      assert.equal(start.run_id, event.run_id);
      assert.equal(start.call_id, event.call_id);
      assert.equal(start.producer_id, event.producer_id);
      assert.equal(step.started_at, start.observed_at);
      assert(Date.parse(step.started_at) <= Date.parse(step.observed_at));
    }
    if (event.phase === "change") {
      const graph = preview.networks.states[event.outputs.state_model_id];
      for (const id of step.transfers) {
        const edge = graph.edges.find((edge) => edge.id === id);
        assert(edge && edge.to === event.node && edge.event === event.outputs.event_name);
        assert.equal(graph.nodes.find((node) => node.id === edge.from).value, event.outputs.before);
        motions++;
      }
      const unrelated = Object.values(preview.networks.states)
        .flatMap((graph) => graph.nodes)
        .filter((node) => node.state_model_id !== event.outputs.state_model_id);
      assert(unrelated.every((node) => !preparedNodeActive(node, step)));
    }
  }
  assert(motions > 0, "A real state transition must supply visible arrow motion");
  for (const graph of [
    ...Object.values(preview.networks).flatMap(Object.values),
    preview.inspection,
  ]) {
    for (const node of graph.nodes) {
      assert(Number.isFinite(node.x) && Number.isFinite(node.y));
      assert(node.labels.every((label) => typeof label === "string" && label.length > 0));
    }
    for (let i = 0; i < graph.nodes.length; i++)
      for (let j = i + 1; j < graph.nodes.length; j++) {
        const a = graph.nodes[i],
          b = graph.nodes[j];
        assert(Math.abs(a.x - b.x) >= 199 || Math.abs(a.y - b.y) >= 79, "Label boxes overlap");
      }
  }
  const wrongEpoch = structuredClone(record);
  wrongEpoch.build_id = "wrong";
  await assert.rejects(compileForest(wrongEpoch, null), /epoch mismatch/);
  const incomplete = structuredClone(record);
  incomplete.gaps.push({ reason: "test omitted envelope" });
  await assert.rejects(compileForest(incomplete, null), /Incomplete capture/);
  results.push({
    epoch,
    models: Object.keys(model.machines).length,
    steps: preview.steps.length,
    witnessed_transfers: motions,
  });
}
const initial = manifest.epochs.initial.states,
  updated = manifest.epochs.updated.states;
for (const id of Object.keys(initial))
  assert(initial[id].every((state) => updated[id].includes(state)));
assert.deepEqual(
  updated.download_task.filter((id) => !initial.download_task.includes(id)),
  ["native_state:download_task:cancelled"],
);
console.log(JSON.stringify({ valid: true, results }, null, 2));
