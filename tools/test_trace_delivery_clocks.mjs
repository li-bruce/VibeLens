/** Late delivery may interleave independent producer clocks in one collector. */
import assert from "node:assert/strict";
import { RecordingTimeline } from "../skills/vibelens/assets/stategraph-viewer/recording-timeline.js";
import { selectedReplayPlan } from "../skills/vibelens/assets/stategraph-viewer/replay-selection.js";
import { timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import {
  buildTraceIndex,
  marksInWindow,
  tracePoints,
  traceRows,
} from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import {
  nearestEvent,
  visibleSlices,
} from "../skills/vibelens/assets/stategraph-viewer/trace-viewport.js";

const at = (ms) => new Date(Date.UTC(2026, 10, 20) + ms).toISOString();
const nodes = [{ id: "work", kind: "action", business: true, label: "Prepare a download" }];
const all = new Map(nodes.map((node) => [node.id, node]));
function event(seq, producer, phase, ms, call = "one") {
  return {
    id: `${producer}:${seq}`,
    project_id: "files",
    build_id: "build",
    run_id: producer + "-run",
    producer_id: producer,
    stream_id: "collector",
    seq,
    source_seq: seq,
    node: "work",
    phase,
    call_id: call,
    entity: "file",
    attempt: "download",
    observed_at: at(ms),
    inputs: {},
    outputs: {},
    depends: [],
  };
}
function record(events) {
  return {
    id: "delivery",
    status: "stopped",
    started_at: at(0),
    ended_at: at(100),
    events,
    commands: [],
    gaps: [],
    context: {
      events: [],
      model: { nodes, edges: [], machine: {} },
      machine: { configurations: [] },
    },
    final: { machine: { configurations: [] } },
  };
}
function build(recording) {
  return buildTraceIndex(recording, timeline(recording), all);
}

// Source B's older operation arrives after A's completed operation. Delivery
// sequence is authoritative for replay; elapsed duration belongs to each source.
const recording = record([
  event(1, "browser", "enter", 30),
  event(2, "browser", "return", 50),
  event(3, "server", "enter", 10),
  event(4, "server", "return", 20),
]);
const original = structuredClone(recording);
const items = timeline(recording);
const index = buildTraceIndex(recording, items, all);
assert.deepEqual(
  items.slice(1, -1).map((item) => item.seq),
  [1, 2, 3, 4],
);
assert.equal(index.axis.ordered, true, "Independent delivery cannot erase valid source time");
assert.equal(index.axis.arrivalOrdered, false);
assert.equal(index.axis.arrivalInversions, 1);
assert.deepEqual(
  index.rows.get("work").slices.map((slice) => slice.duration),
  [10, 20],
);
assert.deepEqual(index.axis.times, [0, 30, 50, 10, 20, 100]);
assert.deepEqual(
  marksInWindow(index.rows.get("work"), 9, 21).map((mark) => mark.raw),
  [3, 4],
);
assert.equal(visibleSlices(index.rows.get("work"), 9, 21).length, 1);
const rows = traceRows(index, { scope: "all" });
const points = tracePoints(
  rows,
  index,
  items.map((_, raw) => raw),
);
assert.equal(nearestEvent(points, 11).raw, 3, "Time seeking resolves the original replay ordinal");
assert.equal(items[nearestEvent(points, 11).raw].id, recording.events[2].id);
assert.deepEqual(recording, original, "Indexing never mutates event order or original timestamps");

// A real backwards clock inside one producer remains invalid, even if several
// producers share the collector. Reusing an entity name never creates a clock.
const reversed = structuredClone(recording);
reversed.events[3].observed_at = at(9);
assert.equal(build(reversed).axis.ordered, false);
assert.ok(
  build(reversed)
    .rows.get("work")
    .slices.every((slice) => slice.duration === null),
);
const unqualified = structuredClone(recording);
delete unqualified.events[2].producer_id;
assert.equal(
  build(unqualified).axis.ordered,
  false,
  "Missing clock identity cannot justify disorder",
);
const invalid = structuredClone(recording);
invalid.events[2].observed_at = "invalid";
assert.equal(build(invalid).axis.ordered, false);
const oneSource = structuredClone(recording);
for (const item of oneSource.events) {
  item.producer_id = "one";
  item.run_id = "one";
  item.entity = "object:" + item.seq;
}
assert.equal(
  build(oneSource).axis.ordered,
  false,
  "Object identity cannot hide a reversed source clock",
);

const delayedBoundary = structuredClone(recording);
delayedBoundary.started_at = at(15);
delayedBoundary.ended_at = at(40);
const adjusted = build(delayedBoundary);
assert.equal(adjusted.axis.ordered, true);
assert.equal(adjusted.axis.boundaryAdjusted, true);
assert.equal(adjusted.axis.times[0], 0);
assert.equal(adjusted.axis.times.at(-1), 40);
assert.equal(delayedBoundary.started_at, at(15));
assert.equal(delayedBoundary.ended_at, at(40));
// A time selection may be non-contiguous in delivery order. The 10/20/30 ms
// events must replay in their original order, excluding the 50 ms event.
let rangeSelection;
RecordingTimeline.prototype.commitRange.call({
  range: [9, 35],
  points,
  index,
  callbacks: {
    onRange: (selection) => {
      rangeSelection = selection;
    },
  },
});
assert.deepEqual(selectedReplayPlan(items, [1, 2, 3, 4], rangeSelection), [1, 3, 4]);
assert.deepEqual(
  selectedReplayPlan(items, [1, 2, 3, 4], {
    ...rangeSelection,
    skipped: [items[3].id],
  }),
  [1, 4],
  "Explicit skips still apply inside a selected time window",
);
assert.deepEqual(
  selectedReplayPlan(items, [1, 2, 3, 4], {
    ...rangeSelection,
    loop: false,
  }),
  [1, 2, 3, 4],
  "Leaving the loop restores the full replay plan",
);
console.log(
  "PASS: independent producer clocks, preserved replay ordinals, time-window queries and strict backwards-clock rejection",
);
