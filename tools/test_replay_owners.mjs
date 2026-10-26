/** One runtime fact may have several visible representations, but one change row. */
import assert from "node:assert/strict";
import { boStepDetail, boStepPlan } from "../skills/vibelens/assets/stategraph-viewer/replay-steps.js";

const node = { id: "task", label: "Repair ticket", kind: "action" };
const alias = { id: "shared-task", label: "Repair ticket", referenceOf: "task" };
const visible = [node, alias].map((node) => ({ id: node.id, node, type: "business" }));
const all = new Map([node, alias].map((n) => [n.id, n]));
function scenario(attempts = ["ticket:1"]) {
  const before = {
    configurations: attempts.map((attempt) => ({ attempt, phase: "pending" })),
  };
  const after = {
    state_revision: 1,
    configurations: attempts.map((attempt) => ({ attempt, phase: "claimed" })),
  };
  const event = {
    id: "event:1",
    kind: "probe",
    run_id: "run",
    revision: 1,
    node: "claim",
    attempt: attempts[0],
    phase: "commit",
    inputs: {},
    outputs: {},
  };
  const recording = {
    build_id: "build",
    context: {
      model: { nodes: [node], machine: {}, presentation: { runtime_owner: "task" } },
      machine: before,
      events: [],
    },
    final: { machine: after },
    runtime_frames: {
      schema: "stategraph-runtime-frames/v1",
      frames: [
        {
          event_id: event.id,
          run_id: event.run_id,
          build_id: "build",
          revision: 1,
          machine: after,
        },
      ],
    },
  };
  return { recording, items: [{ id: "start", kind: "start" }, event] };
}
const single = scenario();
const detail = boStepDetail(single.recording, single.items, 1, 0, all, visible);
assert.equal(detail.rows.length, 1, "A canonical node and its reference show one actual change");
assert.deepEqual(new Set(detail.rows[0].owners), new Set(["task", "shared-task"]));
assert.equal(detail.rows[0].owner, "task");
const states = ["pending", "claimed"].map((value) => ({
  id: "state." + value,
  type: "state",
  node: { id: "state." + value, value, label: value },
}));
const stateOnly = scenario();
const endpoints = boStepDetail(stateOnly.recording, stateOnly.items, 1, 0, all, states);
assert.equal(endpoints.rows.length, 1, "A transition's two state endpoints are one change");
assert.equal(endpoints.rows[0].owner, "state.claimed", "Focus the destination state");
assert.deepEqual(new Set(endpoints.rows[0].owners), new Set(["state.pending", "state.claimed"]));
const multiple = scenario(["ticket:1", "ticket:2"]);
const separate = boStepDetail(multiple.recording, multiple.items, 1, 0, all, visible);
assert.equal(separate.rows.length, 2, "Distinct instances keep their own changes");
assert.deepEqual(new Set(separate.rows.map((r) => r.attempt)), new Set(["ticket:1", "ticket:2"]));
const calls = {
  context: { model: { nodes: [node], machine: {} }, machine: {}, events: [] },
  final: { machine: {} },
};
const events = [
  { kind: "start", id: "start" },
  ...[1, 2].map((i) => ({
    id: "call:" + i,
    call_id: "invocation:" + i,
    kind: "probe",
    node: "task",
    phase: "return",
    inputs: {},
    outputs: { count: 4 },
    attempt: "ticket:1",
  })),
];
const repeated = boStepDetail(calls, events, 2, 0, all, visible);
assert.equal(
  repeated.rows.length,
  2,
  "Identical values from different real invocations stay separate",
);
assert.deepEqual(
  repeated.rows.map((r) => r.event),
  ["call:1", "call:2"],
);
const nested = {id:'helper',label:'Helper',kind:'function',parent:'task'};
const foldedRecording = structuredClone(calls);
const foldedAll = new Map([...all,[nested.id,nested]]);
const foldedItems = [
  {id:'start',kind:'start'},
  {id:'parent:enter',kind:'probe',node:'task',phase:'enter',inputs:{},outputs:{}},
  {id:'helper:enter',kind:'probe',node:'helper',phase:'enter',inputs:{},outputs:{}},
  {id:'helper:return',kind:'probe',node:'helper',phase:'return',inputs:{},outputs:{}},
];
assert.deepEqual(boStepPlan(foldedRecording,foldedItems,foldedAll,visible),[0,1], 'A collapsed business view omits unchanging internal calls');
assert.deepEqual(boStepPlan(foldedRecording,foldedItems,foldedAll,[...visible,{id:nested.id,node:nested,type:'function'}]),[0,1,2,3], 'Opening the function restores its actual calls');
assert.deepEqual(boStepPlan(foldedRecording,foldedItems,foldedAll,visible,{mode:'events'}),[0,1,2,3], 'Raw replay keeps every recorded event');
console.log("Replay owner identity and hierarchy grain checks passed");
