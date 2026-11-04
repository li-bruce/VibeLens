/** Exact HTTP representations retain native evidence without source-call guesses. */
import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
import { apiObservationIds } from "../skills/vibelens/assets/stategraph-viewer/api-observation.js";
import { withCodeGraph } from "../skills/vibelens/assets/stategraph-viewer/code-layer.js";
import {
  graphActivations,
  activationFor,
} from "../skills/vibelens/assets/stategraph-viewer/graph-activation.js";
import {
  nodeEvents,
  callValues,
  status,
  lines,
} from "../skills/vibelens/assets/stategraph-viewer/graph-core.js";
import { runtimeOwners } from "../skills/vibelens/assets/stategraph-viewer/graph-links.js";
import {
  timeline,
  frame,
  transferEdges,
} from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import {
  boStepPlan,
  boStepDetail,
} from "../skills/vibelens/assets/stategraph-viewer/replay-steps.js";
import {
  buildTraceIndex,
  traceRows,
} from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import { visibleFlows } from "../skills/vibelens/assets/stategraph-viewer/trace-flows.js";
import { trackOf } from "../skills/vibelens/assets/stategraph-viewer/trace-tracks.js";
import {
  graphVersion,
  recordingMatches,
} from "../skills/vibelens/assets/stategraph-viewer/view-lifecycle.js";
import { renderRevision } from "../skills/vibelens/assets/stategraph-viewer/layout.js";

const registration = (node, method) => ({
  node,
  method,
  route: "/files",
  source: { path: "web.py", symbol: "files" },
  selector: { name: `${method} /files` },
});
const endpoint = {
    id: "endpoint:files",
    label: "GET POST /files",
    kind: "function",
    code_role: "endpoint",
    api_role: "endpoint",
    api: { path: "/files", methods: ["GET", "POST"] },
    observation_projection: true,
    observation_sources: [registration("api_get", "GET"), registration("api_post", "POST")],
  },
  archive = {
    ...endpoint,
    id: "endpoint:archive",
    label: "GET /archive",
    api: { path: "/archive", methods: ["GET"] },
    observation_projection: undefined,
    observation_sources: [],
  },
  handler = {
    id: "code:files",
    kind: "function",
    code_role: "function",
    source: { path: "web.py", symbol: "files" },
  },
  nativeNodes = [
    {
      id: "share",
      label: "Share file",
      kind: "function",
      layer: "business",
      basis_fields: [],
    },
    {
      id: "api_get",
      label: "HTTP GET",
      kind: "function",
      layer: "execution",
      basis_fields: [],
    },
    {
      id: "api_post",
      label: "HTTP POST",
      kind: "function",
      layer: "execution",
      basis_fields: [],
    },
    { id: "store", label: "Save file", kind: "function", basis_fields: [] },
  ],
  edges = [
    {
      id: "map",
      from: "api_get",
      to: handler.id,
      type: "data",
      code_relation: "maps",
    },
    ...[endpoint, archive].map((node) => ({
      id: `handles:${node.id}`,
      from: node.id,
      to: handler.id,
      type: "data",
      code_relation: "handles",
    })),
    {
      id: "observation",
      from: "api_get",
      to: endpoint.id,
      type: "data",
      code_relation: "maps",
      mapping_role: "http-observation",
    },
  ],
  model = {
    nodes: nativeNodes,
    edges: [],
    machine: { values: [], states: [], transitions: [], events: {} },
    presentation: {},
  },
  initial = {
    model,
    events: [],
    authority: { parameters: {}, basis: {} },
    machine: { current: null, configurations: [], journal: [] },
    manifest: { build_id: "build", bindings: {} },
    binding_status: { status: "current" },
    api_structure: { nodes: [endpoint, archive, handler], edges, bindings: {} },
  };
const event = (id, node, phase, time, call, parent = null, values = {}) => ({
  id,
  node,
  phase,
  lifecycle: "span",
  observed_at: new Date(1735689600000 + time).toISOString(),
  kind: "probe",
  call_id: call,
  parent_call_id: parent,
  run_id: "run",
  stream_id: "stream",
  producer_id: "worker",
  project_id: "project",
  build_id: "build",
  model_revision: "revision",
  attempt: "attempt",
  entity: "entity",
  basis: {},
  inputs: phase === "enter" ? values : {},
  outputs: phase === "return" ? values : {},
});
const events = [
  event("business-enter", "share", "enter", 0, "business"),
  event("get-enter", "api_get", "enter", 10, "get", "business", {
    method: "GET",
    path: "/files",
  }),
  event("store-enter", "store", "enter", 20, "store", "get"),
  event("store-return", "store", "return", 40, "store", "get", { count: 3 }),
  event("get-return", "api_get", "return", 70, "get", "business", {
    status: 200,
  }),
  event("post-enter", "api_post", "enter", 80, "post", "business", {
    method: "POST",
    path: "/files",
  }),
  event("post-return", "api_post", "return", 110, "post", "business", {
    status: 403,
  }),
  event("business-return", "share", "return", 120, "business"),
];
const recording = {
    id: "api-recording",
    started_at: new Date(1735689599999).toISOString(),
    ended_at: new Date(1735689600130).toISOString(),
    status: "stopped",
    commands: [],
    context: initial,
    final: { ...initial, events },
    events,
  },
  items = timeline(recording),
  view = withCodeGraph({ ...initial, events }, null),
  all = new Map(view.model.nodes.map((node) => [node.id, node])),
  before = JSON.stringify(recording);
assert.deepEqual(apiObservationIds(endpoint), ["api_get", "api_post"]);
assert.deepEqual(apiObservationIds({ ...endpoint, observation_projection: false }), []);
assert.deepEqual(runtimeOwners(view.model, endpoint.id), ["api_get", "api_post"]);
assert.deepEqual(
  runtimeOwners(view.model, archive.id),
  [],
  "Shared handler alone never identifies the observed route",
);
const legacyEndpoint = { ...archive, id: "legacy:endpoint" };
delete legacyEndpoint.observation_sources;
delete legacyEndpoint.observation_projection;
const legacyModel = {
  ...view.model,
  nodes: [...view.model.nodes, legacyEndpoint],
  edges: [
    ...view.model.edges,
    {
      id: "legacy-handles",
      from: legacyEndpoint.id,
      to: handler.id,
      code_relation: "handles",
    },
  ],
};
assert.deepEqual(
  runtimeOwners(legacyModel, legacyEndpoint.id),
  ["api_get"],
  "Legacy source-based focus selection stays available",
);
assert.equal(
  status(legacyEndpoint, { ...view, model: legacyModel }, events, "latest"),
  "declared",
  "Legacy selection is not endpoint activation evidence",
);
assert.equal(activationFor(legacyEndpoint, { ...view, model: legacyModel }, events), null);
const legacyTrace = buildTraceIndex(
  recording,
  items,
  new Map(legacyModel.nodes.map((node) => [node.id, node])),
  legacyModel.edges,
);
assert.equal(
  legacyTrace.rows.get(legacyEndpoint.id)?.slices.length || 0,
  0,
  "Legacy focus selection creates no HTTP duration",
);
assert.equal(view.model.nodes.filter((node) => node.id === endpoint.id).length, 1);
assert.equal(
  withCodeGraph(view, initial.api_structure).model.nodes.filter((node) => node.id === endpoint.id)
    .length,
  1,
);
assert.equal(nodeEvents(endpoint, events).length, 4);
assert.equal(nodeEvents(archive, events).length, 0);
assert.equal(callValues(endpoint, events).outputs.status, 403);
const mixedIds = [
  event("get-input", "api_get", "enter", 1, "reused", null, { getOnly: true }),
  event("post-output", "api_post", "return", 2, "reused", null, {
    status: 201,
  }),
];
assert.equal(
  callValues(endpoint, mixedIds).inputs.getOnly,
  undefined,
  "Methods cannot merge values through a reused call ID",
);
const active = graphActivations(events.slice(0, 3), view.model.nodes).get(endpoint.id);
assert.equal(active.phase, "running");
assert.equal(active.callId, "get");
assert.equal(active.observation_basis.source_node, "api_get");
assert.equal(activationFor(archive, view, events), null);
assert.equal(
  activationFor(handler, view, events),
  null,
  "A static handler gains no invented duration",
);
assert.equal(
  status(endpoint, { ...view, events: events.slice(0, 3) }, events.slice(0, 3), "latest"),
  "active",
);
assert.equal(status(archive, view, events, "latest"), "declared");
assert(lines(endpoint, view, events, "latest").some((row) => row.text === "status: 403"));
assert.equal(
  activationFor(endpoint, view, events).phase,
  "returned",
  "HTTP 403 is an observed response, not inferred failure",
);
const concurrent = [
  event("get-active", "api_get", "enter", 1, "shared-call-id"),
  event("post-active", "api_post", "enter", 2, "shared-call-id"),
];
assert.equal(graphActivations(concurrent, view.model.nodes).get(endpoint.id).activeCount, 2);
const oldAPI = {
    ...initial,
    api_structure: { ...initial.api_structure, revision: "api-1" },
  },
  newAPI = {
    ...initial,
    api_structure: { ...initial.api_structure, revision: "api-2" },
  };
assert.notEqual(graphVersion(oldAPI), graphVersion(newAPI));
assert.notEqual(renderRevision(oldAPI), renderRevision(newAPI));
assert(!recordingMatches({ context: oldAPI }, newAPI));
assert.equal(
  graphVersion(oldAPI),
  graphVersion({ ...oldAPI, preferences: { hiddenNodes: ["api_get"] } }),
);
const legacy = {
  ...initial,
  manifest: { ...initial.manifest, model_hash: "legacy-model" },
};
delete legacy.api_structure;
assert.equal(
  graphVersion(legacy),
  '["build","legacy-model"]',
  "Legacy snapshots retain their original graph version",
);
const index = buildTraceIndex(recording, items, all, edges),
  apiRow = index.rows.get(endpoint.id);
assert.deepEqual(
  apiRow.slices.map((slice) => [items[slice.raw].id, items[slice.last].id, slice.duration]),
  [
    ["get-enter", "get-return", 60],
    ["post-enter", "post-return", 30],
  ],
);
assert(!index.rows.has(archive.id));
assert.equal(index.rows.get(handler.id)?.slices.length || 0, 0);
assert(apiRow.slices.every((slice) => slice.observation_basis.kind === "http-registration"));
const shown = new Set(["share", endpoint.id, "store"]),
  rows = traceRows(index, {
    visible: shown,
    order: ["business", "api", "execution"],
  }),
  flows = visibleFlows(index, rows, { start: 0, end: index.axis.total });
assert(
  flows.some(
    (flow) =>
      rows[flow.fromRow].layer === "business" &&
      rows[flow.toRow].layer === "implementation" &&
      flow.toNode === endpoint.id,
  ),
);
assert(
  flows.some(
    (flow) =>
      flow.fromNode === endpoint.id &&
      (flow.toNode || items[flow.to]?.node) === "store" &&
      rows[flow.fromRow].layer === "implementation" &&
      rows[flow.toRow].layer === "implementation",
  ),
  "API-to-operation causality stays visible horizontally in the shared implementation plane",
);
assert(flows.some((flow) => flow.type === "return" && flow.toNode === endpoint.id));
assert(
  flows
    .filter((flow) => flow.toNode === endpoint.id)
    .every((flow) => flow.toNode === endpoint.id && flow.toObservedNode),
  "Projected causal endpoints retain both display identity for subtracks and native observed subject",
);
const boxes = [{ id: endpoint.id, type: "code-endpoint", node: endpoint }],
  plan = boStepPlan(recording, items, all, boxes),
  detail = boStepDetail(recording, items, 5, 4, all, boxes);
assert(plan.includes(items.findIndex((item) => item.id === "get-enter")));
assert(plan.includes(items.findIndex((item) => item.id === "post-return")));
assert(detail.rows.some((change) => change.owner === endpoint.id && change.field === "status"));
const parallelEvents = [
    event("parallel-business", "share", "enter", 1, "parallel-parent"),
    event("parallel-get", "api_get", "enter", 2, "parallel-get", "parallel-parent"),
    event("parallel-post", "api_post", "enter", 3, "parallel-post", "parallel-parent"),
    event("parallel-get-end", "api_get", "return", 10, "parallel-get", "parallel-parent"),
    event("parallel-post-end", "api_post", "return", 12, "parallel-post", "parallel-parent"),
    event("parallel-business-end", "share", "return", 15, "parallel-parent"),
  ],
  parallelRecording = {
    ...recording,
    id: "parallel-api",
    events: parallelEvents,
  },
  parallelItems = timeline(parallelRecording),
  parallelIndex = buildTraceIndex(parallelRecording, parallelItems, all, edges),
  parallelRows = traceRows(parallelIndex, {
    visible: new Set(["share", endpoint.id]),
    order: ["business", "api"],
  }),
  parallelFlows = visibleFlows(parallelIndex, parallelRows, {
    start: 0,
    end: parallelIndex.axis.total,
  }),
  invocationTracks = parallelFlows
    .filter(
      (flow) =>
        flow.type === "call" &&
        flow.toNode === endpoint.id &&
        parallelRows[flow.toRow].layer === "implementation",
    )
    .map((flow) => trackOf(parallelRows[flow.toRow], flow.toNode, flow.to));
assert.equal(
  new Set(invocationTracks).size,
  2,
  "Concurrent HTTP calls connect to their own API subtracks",
);
const observedEdge = {
  id: "visible-observation",
  type: "data",
  members: [edges.at(-1)],
};
assert.deepEqual(transferEdges(items[2], items, [observedEdge], all), ["visible-observation"]);
const replay = withCodeGraph(frame(recording, 2, items), null);
assert.equal(
  status(
    replay.model.nodes.find((node) => node.id === endpoint.id),
    replay,
    replay.events,
    "latest",
  ),
  "active",
);
assert.equal(
  JSON.stringify(recording),
  before,
  "Projection cannot rewrite events, recordings or causal identities",
);
if (process.env.BO_API_RECORDING)
  await writeFile(process.env.BO_API_RECORDING, JSON.stringify(recording, null, 2) + "\n");
console.log(
  "Exact API observation: native intervals, values, causal rows, playback, shared-handler isolation and recorded snapshots passed",
);
