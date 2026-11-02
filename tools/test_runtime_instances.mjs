/** Compare native state instances independently of shared request/caller labels. */
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  runtimeChanges,
  runtimeFrame,
  rememberRuntimeMachine,
} from "../skills/vibelens/assets/stategraph-viewer/runtime-frames.js";
import { boFacts } from "../skills/vibelens/assets/stategraph-viewer/replay-steps.js";
import { timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";

const cfg = (id, phase) => ({
  snapshot_instance: id,
  attempt: "application",
  phase,
});
const machine = (...configurations) => ({ configurations });
const changes = (before, after) => {
  const rows = [];
  runtimeChanges(before, after, "flow", (...row) => rows.push(row));
  return rows;
};
const first = machine(cfg("run:file:1", "approved"), cfg("run:share:1", "revoked"));
assert.deepEqual(
  changes(first, first).filter((r) => r[2] !== r[3]),
  [],
);
assert.deepEqual(
  changes(machine(cfg("run:share:1", "revoked")), first).filter((r) => r[2] !== r[3]),
  [],
  "Never compare a share's state with a file's state",
);
const merged = rememberRuntimeMachine(first, machine(cfg("run:file:1", "archived")));
assert.equal(
  merged.configurations.length,
  2,
  "Partial frames retain independent last-known states",
);
assert.deepEqual(
  changes(first, merged)
    .filter((r) => r[2] !== r[3])
    .map((r) => r.slice(2, 4)),
  [["approved", "archived"]],
);
assert.deepEqual(
  changes(
    machine({ attempt: "a", phase: "pending" }),
    machine({ attempt: "a", phase: "done" }),
  )[0].slice(2, 4),
  ["pending", "done"],
);
assert.deepEqual(
  changes(
    machine({ attempt: "a", phase: "one" }, { attempt: "a", phase: "two" }),
    machine({ attempt: "a", phase: "three" }),
  ),
  [],
  "Ambiguous legacy identity cannot prove a change",
);

const event = {
  id: "e",
  run_id: "r",
  revision: 1,
  snapshot_instance: "r:file:1",
};
const rawFrame = {
  event_id: "e",
  run_id: "r",
  build_id: "b",
  revision: 1,
  machine: {
    state_revision: 1,
    configurations: [{ attempt: "application", phase: "approved" }],
  },
};
const legacy = {
  build_id: "b",
  runtime_frames: {
    schema: "stategraph-runtime-frames/v1",
    frames: [rawFrame],
  },
};
assert.equal(runtimeFrame(legacy, event).machine.configurations[0].snapshot_instance, "r:file:1");
assert.equal(
  rawFrame.machine.configurations[0].snapshot_instance,
  undefined,
  "Keep raw evidence unchanged",
);
assert.equal(runtimeFrame(legacy, { ...event, revision: 2 }), null);

const states = [
  cfg("r:file:1", "pending"),
  cfg("r:share:1", "revoked"),
  cfg("r:file:1", "approved"),
];
const events = states.map((state, i) => ({
  id: `e${i}`,
  kind: "probe",
  run_id: "r",
  node: "flow",
  revision: i,
  attempt: "application",
  phase: "change",
  inputs: {},
  outputs: {},
}));
const synthetic = {
  build_id: "b",
  context: {
    model: { nodes: [{ id: "flow" }], machine: {} },
    machine: machine(),
    events: [],
  },
  final: { machine: machine(states[2], states[1]) },
  runtime_frames: {
    schema: "stategraph-runtime-frames/v1",
    partial: true,
    frames: events.map((e, i) => ({
      event_id: e.id,
      run_id: "r",
      build_id: "b",
      revision: i,
      machine: { ...machine(states[i]), state_revision: i },
    })),
  },
};
const facts = boFacts(synthetic, [...events, { id: "end", kind: "end" }]);
assert.deepEqual(
  facts.changes
    .flat()
    .filter((row) => row.kind === "business")
    .map((row) => [row.before, row.after]),
  [["pending", "approved"]],
  "Interleaved single-instance frames preserve only witnessed transitions of the same instance",
);

// Optional unchanged real recording reproduces the multi-instance End-step defect.
if (process.argv[2]) {
  const recording = JSON.parse(await readFile(process.argv[2], "utf8"));
  const items = timeline(recording);
  const result = boFacts(recording, items);
  const final = result.changes.at(-1).filter((row) => row.kind === "business");
  assert.deepEqual(final, [], "End must not invent a transition between distinct final instances");
  const stateChanges = result.changes.flat().filter((row) => row.kind === "business").length;
  const identified = recording.runtime_frames.frames.every((frame) =>
    frame.machine.configurations.every((cfg) => cfg.snapshot_instance),
  );
  if (identified)
    assert.ok(stateChanges > 0, "Identified real frames must retain actual transitions");
  console.log(
    JSON.stringify({
      passed: true,
      realEvents: recording.events.length,
      finalChanges: final.length,
      stateChanges,
      identified,
    }),
  );
} else console.log("Native state-instance projection and replay checks passed");
