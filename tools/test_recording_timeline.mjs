/** Test trace evidence separately from rendering, business execution and layout. */
import assert from "node:assert/strict";
import {
  buildTraceIndex,
  traceRows,
  tracePoints,
} from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import {
  parentEvent,
  traceTime,
} from "../skills/vibelens/assets/stategraph-viewer/trace-evidence.js";
import {
  boundWindow,
  zoomWindow,
  nearestEvent,
  visibleSlices,
} from "../skills/vibelens/assets/stategraph-viewer/trace-viewport.js";
import { transferEdges, timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import { readFile, writeFile, mkdir } from "node:fs/promises";
import path from "node:path";

const checks = [];
const iso = (ms) => new Date(Date.UTC(2026, 9, 30) + ms).toISOString();
const nodes = [
  { id: "share", label: "Share file", kind: "action", business: true },
  { id: "check", label: "Check access", kind: "decision" },
  { id: "query", label: "Read grants", kind: "function", data_role: "query" },
  { id: "transform", label: "Normalize metadata", kind: "function", data_role: "transform" },
  { id: "source", label: "can_share", kind: "function", code_role: "function" },
];
const all = new Map(nodes.map((node) => [node.id, node]));
const edges = [{ id: "map", from: "check", to: "source", code_relation: "maps" }];
function event(id, ms, node, phase, extra = {}) {
  return {
    id,
    seq: Number(id.replace(/\D/g, "")) || 1,
    kind: "probe",
    node,
    phase,
    build_id: "build",
    run_id: "run",
    producer_id: "worker",
    stream_id: "stream",
    entity: "file:1",
    attempt: "attempt:1",
    call_id: node,
    parent_call_id: null,
    inputs: {},
    outputs: {},
    depends: [],
    observed_at: iso(ms),
    ...extra,
  };
}
function recording(events) {
  return {
    id: "recording",
    status: "stopped",
    build_id: "build",
    started_at: iso(0),
    ended_at: iso(100),
    events,
    commands: [],
    gaps: [],
    context: { events: [], model: { nodes, edges, machine: {} }, machine: { configurations: [] } },
    final: { machine: { configurations: [] } },
  };
}
function index(events) {
  const record = recording(events);
  return buildTraceIndex(record, timeline(record), all, edges);
}

try {
  const events = [
    event("e1", 1, "share", "enter"),
    event("e2", 2, "check", "enter", { parent_call_id: "share" }),
    event("e3", 3, "query", "enter", { parent_call_id: "check" }),
    event("e4", 8, "query", "return", { parent_call_id: "check" }),
    event("e5", 9, "check", "decision", {
      outputs: { allowed: true },
      depends: [{ event: "e4", type: "data" }],
    }),
    event("e6", 10, "check", "return"),
    event("e7", 11, "share", "return"),
  ];
  const result = index(events);
  assert.equal(result.rows.get("share").slices[0].duration, 10);
  assert.equal(result.rows.get("check").slices[0].duration, 8);
  assert.equal(result.rows.get("query").slices[0].duration, 5);
  assert.equal(result.links.filter((link) => link.type === "call").length, 2);
  assert.equal(result.links.filter((link) => link.type === "data").length, 1);
  assert.equal(result.rows.get("source").slices.length, 0);
  assert.ok(result.rows.get("source").marks.every((mark) => mark.projected));
  checks.push("nested durations, explicit call/dependency flows, hollow source projection");
  const sourceEvents = index([
    event("s1", 1, "source", "enter"),
    event("s2", 4, "source", "return"),
  ]);
  assert.equal(sourceEvents.rows.get("source").slices[0].duration, 3);
  assert.ok(sourceEvents.rows.get("source").marks.every((mark) => !mark.projected));
  checks.push("a directly instrumented code/API identity remains actual runtime evidence");
  const transformed = index([
    event("t1", 1, "transform", "enter"),
    event("t2", 3, "transform", "change", { outputs: { status: "transformed" } }),
  ]);
  assert.equal(
    transformed.rows.get("transform").slices[0].duration,
    2,
    "the native data-transform completion closes its own invocation",
  );
  const ordinaryChange = index([
    event("v1", 1, "share", "enter"),
    event("v2", 3, "share", "change", { outputs: { status: "transformed" } }),
  ]);
  assert.equal(
    ordinaryChange.rows.get("share").slices[0].unfinished,
    true,
    "a business value named transformed is not an execution terminal",
  );
  checks.push("native data-transform completion is distinct from an ordinary state/value change");

  const repeated = index([
    event("r1", 1, "share", "enter"),
    event("r2", 4, "share", "return"),
    event("r3", 5, "share", "enter"),
    event("r4", 9, "share", "return"),
  ]);
  assert.deepEqual(
    repeated.rows.get("share").slices.map((slice) => slice.duration),
    [3, 4],
  );
  const committed = index([
    event("c1", 1, "share", "enter"),
    event("c2", 4, "share", "commit"),
    event("c3", 5, "share", "enter"),
    event("c4", 9, "share", "commit"),
  ]);
  assert.deepEqual(
    committed.rows.get("share").slices.map((slice) => slice.duration),
    [3, 4],
  );
  const overlap = index([
    event("o1", 1, "share", "enter"),
    event("o2", 2, "share", "enter"),
    event("o3", 4, "share", "return"),
    event("o4", 9, "share", "return"),
  ]);
  assert.ok(
    overlap.rows.get("share").slices.every((slice) => slice.ambiguous && slice.duration === null),
  );
  checks.push("sequential reuse, commit-only completions and ambiguous overlapping IDs");

  for (const field of ["entity", "attempt", "producer_id", "run_id", "build_id", "stream_id"]) {
    const cross = index([
      event("x1", 1, "share", "enter"),
      event("x2", 2, "share", "return", { [field]: "another" }),
      event("x3", 3, "query", "enter", { parent_call_id: "share", [field]: "another" }),
    ]);
    assert.equal(cross.rows.get("share").slices[0].duration, null, field);
    assert.equal(cross.links.length, 0, field);
  }
  assert.equal(parentEvent(events[1], events)?.id, "e1");
  assert.equal(
    parentEvent(event("z9", 15, "query", "enter", { parent_call_id: "share" }), events),
    null,
    "closed parent is not a new invocation",
  );
  const callEdge = [{ id: "call", type: "call", members: [{ from: "share", to: "check" }] }];
  assert.deepEqual(transferEdges(events[1], events, callEdge, all), ["call"]);
  assert.deepEqual(
    transferEdges({ ...events[1], producer_id: "another" }, events, callEdge, all),
    [],
  );
  checks.push("six identity boundaries and shared graph parent-call evidence");
  const crossRun = index([
    event("cross1", 1, "share", "commit"),
    event("cross2", 4, "query", "enter", {
      run_id: "remote-run",
      depends: [{ event: "cross1", type: "trigger" }],
    }),
  ]);
  assert.deepEqual(
    crossRun.links,
    [{ from: 1, to: 2, type: "trigger" }],
    "explicit event references retain cross-run causality",
  );
  checks.push("globally qualified event dependencies retain explicit cross-run causality");

  const unknown = index([event("u1", 2, "share", "enter"), event("u2", 1, "share", "return")]);
  assert.equal(unknown.axis.ordered, false);
  assert.equal(unknown.rows.get("share").slices[0].duration, null);
  assert.equal(
    index([event("m1", 1, "share", "enter", { observed_at: "invalid" })]).axis.ordered,
    false,
  );
  assert.equal(
    index([event("q1", 1, "share", "enter")]).rows.get("share").slices[0].unfinished,
    true,
  );
  assert.equal(
    traceTime("2026-10-30T00:00:00.123456Z") - traceTime("2026-10-30T00:00:00.123000Z"),
    0.4560546875,
  );
  assert.equal(
    traceTime("2026-10-30T00:00:00"),
    null,
    "timezone-less time is not a comparable producer timestamp",
  );
  checks.push("reversed, missing and fractional clocks; open calls retain unknown completion");

  const viewRows = traceRows(result, { visible: new Set(["check"]), expanded: ["rules"] });
  assert.deepEqual(
    viewRows.map((row) => ({ layer: row.layer, members: row.members })),
    [{ layer: "rules", members: ["check"] }],
  );
  assert.deepEqual(
    tracePoints(viewRows, result, [0, 2, 5, 8]).map((point) => point.raw),
    [0, 2, 5, 8],
  );
  assert.deepEqual(traceRows(result, { visible: new Set() }), []);
  const bounds = boundWindow(-5, 5, 100);
  assert.deepEqual(bounds, { start: 0, end: 10 });
  assert.deepEqual(zoomWindow({ start: 0, end: 100 }, 2, 0.5, 100), { start: 25, end: 75 });
  assert.equal(
    nearestEvent(
      [
        { time: 1, raw: 1 },
        { time: 3, raw: 2 },
      ],
      2,
    ).raw,
    1,
  );
  assert.equal(
    visibleSlices(result.rows.get("share"), 4, 6).length,
    1,
    "a call starting offscreen still crosses the visible window",
  );
  checks.push("view filtering, skipped-step plan, bounded navigation and interval queries");

  const original = await readFile(
    new URL("../docs/review/spatial-workspace/replay-fixture.json", import.meta.url),
    "utf8",
  );
  const real = JSON.parse(original),
    items = timeline(real),
    realAll = new Map(real.context.model.nodes.map((node) => [node.id, node]));
  const before = JSON.stringify(real);
  const actual = buildTraceIndex(real, items, realAll);
  assert.equal(JSON.stringify(real), before);
  assert.ok(
    [...actual.rows.values()].some((row) => row.slices.some((slice) => slice.duration !== null)),
  );
  const actualTransforms = [...actual.rows.values()].filter(
    (row) => row.node.data_role === "transform",
  );
  assert.ok(actualTransforms.length > 0);
  assert.ok(
    actualTransforms.every(
      (row) =>
        row.slices.length &&
        row.slices.every((slice) => !slice.unfinished && slice.duration !== null),
    ),
    "actual native transformations have captured completion and duration",
  );
  checks.push("unchanged actual recording yields real duration slices");

  const largeEvents = [];
  for (let i = 0; i < 10000; i++) {
    largeEvents.push(event("large" + (i * 2 + 1), i * 2, "query", "enter", { call_id: String(i) }));
    largeEvents.push(
      event("large" + (i * 2 + 2), i * 2 + 1, "query", "return", { call_id: String(i) }),
    );
  }
  const large = recording(largeEvents);
  large.ended_at = iso(20001);
  const start = performance.now();
  const indexed = buildTraceIndex(large, timeline(large), all);
  const elapsed = performance.now() - start;
  assert.equal(indexed.rows.get("query").slices.length, 10000);
  assert.ok(elapsed < 2500, `20,000-event index: ${elapsed} ms`);
  checks.push({ largeEvents: 20000, indexMs: elapsed });
  const out = process.env.BO_TIMELINE_EVIDENCE;
  if (out) {
    await mkdir(out, { recursive: true });
    await writeFile(path.join(out, "unit.json"), JSON.stringify({ passed: true, checks }, null, 2));
  }
  console.log(JSON.stringify({ passed: true, checks }, null, 2));
} catch (error) {
  if (process.env.BO_TIMELINE_EVIDENCE) {
    await mkdir(process.env.BO_TIMELINE_EVIDENCE, { recursive: true });
    await writeFile(
      path.join(process.env.BO_TIMELINE_EVIDENCE, "unit.json"),
      JSON.stringify({ passed: false, checks, error: String(error.stack) }, null, 2),
    );
  }
  throw error;
}
