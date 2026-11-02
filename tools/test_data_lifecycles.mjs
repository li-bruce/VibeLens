/** Check graph/timeline lifetimes over actual native data-adapter events. */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { lifecycleTransition } from "../skills/vibelens/assets/stategraph-viewer/node-lifecycle.js";
import { traceLifecycles } from "../skills/vibelens/assets/stategraph-viewer/trace-lifecycles.js";
import { graphActivations } from "../skills/vibelens/assets/stategraph-viewer/graph-activation.js";
import { buildTraceIndex } from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import { timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";

const payload = JSON.parse(await readFile(process.argv[2], "utf8"));
for (const nodes of [payload.legacy, payload.registered]) {
  const all = new Map(nodes.map((node) => [node.id, node]));
  const items = payload.events.map((event) => ({ ...event, kind: "probe" }));
  const facts = traceLifecycles(items, all);
  assert.equal(facts.slices.length, payload.events.filter((e) => e.phase === "enter").length);
  assert.ok(facts.slices.every((slice) => slice.closed && !slice.unfinished));
  for (const expected of payload.boundaries[nodes === payload.legacy ? "legacy" : "registered"]) {
    const actual = lifecycleTransition(all.get(expected.node), payload.events[expected.raw]);
    assert.deepEqual(
      actual && { boundary: actual.boundary, state: actual.state, registered: actual.registered },
      expected.transition,
    );
  }
  const activations = graphActivations(payload.events, nodes);
  for (const node of nodes) {
    const state = activations.get(node.id);
    assert.ok(state && !state.activeCount && state.end);
  }
  const cut = payload.events.findIndex((event) => event.phase === "commit"),
    record = {
      id: "mid-transaction",
      status: "stopped",
      commands: [],
      gaps: [],
      started_at: payload.events[cut].observed_at,
      ended_at: payload.events.at(-1).observed_at,
      events: payload.events.slice(cut),
      context: {
        model: { nodes, machine: {} },
        events: payload.events.slice(0, cut),
        machine: { configurations: [] },
      },
      final: { machine: { configurations: [] } },
    };
  const clipped = buildTraceIndex(record, timeline(record), all).lifecycles.slices;
  assert.ok(
    clipped.some((slice) => slice.node === "transaction" && slice.context_entry && slice.closed),
  );
  assert.ok(clipped.every((slice) => slice.closed));
}
// New lifecycle declarations must refresh graph activation even when facts are unchanged.
const prior = graphActivations(payload.events, payload.legacy);
const changed = graphActivations(payload.events, payload.registered);
assert.notEqual(prior, changed);
assert.ok([...changed.values()].every((state) => state.registered));

// Registered updates outrank legacy commit/change heuristics.
for (const phase of ["commit", "change"]) {
  const node = {
    id: "period",
    data_role: "transform",
    lifecycle: {
      states: [{ id: "working", kind: "active", label: "Working" }],
      bindings: [
        { phase: "enter", state: "working", boundary: "start" },
        { phase, state: "working", boundary: "update" },
      ],
    },
  };
  const events = ["enter", phase].map((phase, raw) => ({
    ...payload.events[0],
    node: node.id,
    kind: "probe",
    id: "period:" + raw,
    phase,
    outputs: { status: "transformed" },
  }));
  assert.equal(traceLifecycles(events, new Map([[node.id, node]])).slices[0].unfinished, true);
}
console.log(
  JSON.stringify({
    valid: true,
    nativeEvents: payload.events.length,
    graphAndTimelineClosed: true,
    parity: true,
  }),
);
