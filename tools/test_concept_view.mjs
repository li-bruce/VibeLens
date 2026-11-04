/** Concept definitions and their source bindings survive every view projection. */
import assert from "node:assert/strict";
import { graphInventory } from "../skills/vibelens/assets/stategraph-viewer/graph-inventory.js";
import {
  layoutGraph,
  relationType,
} from "../skills/vibelens/assets/stategraph-viewer/graph-core.js";
import { profileFor, matchingNodes } from "../skills/vibelens/assets/stategraph-viewer/analysis.js";
import { layerOf, layerSlice } from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
import { visualType } from "../skills/vibelens/assets/stategraph-viewer/graph-classification.js";
import {
  emptyFilters,
  cleanFilters,
  refreshHierarchy,
  presentationGraph,
  renderRevision,
  relationStyle,
  hierarchyOf,
  relationName,
} from "../skills/vibelens/assets/stategraph-viewer/layout.js";
import { setLocale } from "../skills/vibelens/assets/stategraph-viewer/i18n.js";
import {
  spatialModel,
  containmentVolumes,
  prepareSpatialHierarchy,
} from "../skills/vibelens/assets/stategraph-viewer/spatial-model.js";
import {
  graphVersion,
  recordingMatches,
} from "../skills/vibelens/assets/stategraph-viewer/view-lifecycle.js";
import { buildTraceIndex } from "../skills/vibelens/assets/stategraph-viewer/trace-index.js";
import { frame, timeline } from "../skills/vibelens/assets/stategraph-viewer/recording.js";

const concept = (id, layer, conceptKind, kind) => ({
  id,
  label: id,
  layer,
  concept_kind: conceptKind,
  kind,
  origin: "concept-design",
  capture: {},
});
const nodes = [
  concept("share", "business", "action", "action"),
  concept("object:grant", "business", "object", "data"),
  concept("event:share", "state", "event", "data"),
  concept("transition:grant", "state", "transition", "action"),
  concept("state:active", "state", "state", "state"),
  concept("decision:share", "rules", "rule_operation", "decision"),
  concept("fact:owner", "rules", "fact", "data"),
];
const edge = (id, from, to, type) => ({
  id,
  from,
  to,
  type,
  label: type,
  origin: "concept-design",
  evidence_kind: "conceptual",
});
const edges = [
  edge("request", "share", "event:share", "action_requests_event"),
  edge("trigger", "event:share", "transition:grant", "requests_transition"),
  edge("guard", "transition:grant", "decision:share", "transition_guarded_by"),
  edge("read", "decision:share", "fact:owner", "decision_reads_fact"),
  edge("target", "transition:grant", "state:active", "declares_target"),
  edge("fact", "object:grant", "fact:owner", "describes_fact"),
];
const native = {
  id: "source:share",
  label: "share_file",
  kind: "function",
  source: { path: "sharing.py", symbol: "share_file" },
};
const view = {
  model: {
    nodes: [native],
    edges: [],
    machine: { values: [], transitions: [] },
  },
  concept_structure: {
    nodes,
    edges: [
      ...edges,
      {
        id: "binding",
        from: "share",
        to: native.id,
        type: "maps",
        origin: "concept-binding",
        mapping_role: "implements",
      },
    ],
    revision: "confirmed-1",
  },
  manifest: { build_id: "build-1", model_hash: "native-1", bindings: {} },
  machine: { configurations: [], journal: [] },
  events: [],
  authority: { parameters: {}, basis: {} },
  binding_status: { status: "current" },
};
const before = JSON.stringify(view);
const inventory = graphInventory(view);
assert.equal(inventory.all.size, 8);
assert.equal(inventory.rawEdges.length, 7);
for (const node of nodes) assert.equal(layerOf(node), node.layer, node.id);
assert.equal(visualType(nodes.find((node) => node.id === "transition:grant")), "state");
for (const relation of edges) {
  assert.equal(relationType(relation), relation.type);
  assert.ok(emptyFilters().edges.includes(relation.type));
  assert.ok(relationStyle(relation).dash.length);
}
assert.ok(cleanFilters({ edges: ["other"] }).edges.includes("requests_transition"));
assert.deepEqual(cleanFilters({ edges: ["call"] }).edges, ["call"]);
for (const [preset, concern] of [
  ["business", "business"],
  ["states", "state"],
  ["rules", "rules"],
]) {
  const profile = profileFor(preset);
  const graph = layoutGraph(
    view,
    new Set(nodes.map((node) => node.id)),
    new Set(),
    new Map(),
    "latest",
    "latest",
    {
      match: (all, events, status, relations) =>
        matchingNodes(all, view, events, profile, status, relations),
    },
  );
  refreshHierarchy(graph);
  const shown = presentationGraph(graph, profile);
  for (const node of nodes.filter((node) => node.layer === concern))
    assert.ok(shown.glyphs.has(node.id), preset + " preserves " + node.id);
  for (const relation of edges.filter((relation) =>
    [relation.from, relation.to].every(
      (id) => nodes.find((node) => node.id === id)?.layer === concern,
    ),
  ))
    assert.ok(
      shown.edges.some((drawn) => drawn.members.some((member) => member.id === relation.id)),
      "Typed peer relationship remains visible: " + relation.id,
    );
}
const graph = layoutGraph(view);
const slice = layerSlice(graph, { visible: ["business", "rules"] });
const path = slice.edges.find(
  (relation) => relation.derived && relation.from === "share" && relation.to === "decision:share",
);
assert.deepEqual(path.witnesses[0].types, [
  "action_requests_event",
  "requests_transition",
  "transition_guarded_by",
]);
assert.equal(path.observed, false);
assert.equal(relationType(path), "indirect");
refreshHierarchy(slice);
assert.ok(
  presentationGraph(slice, {
    ...emptyFilters(),
    edges: ["indirect"],
  }).edges.some((relation) => relation.derived),
  "The indirect relation filter works after compound-edge projection",
);
assert.equal(
  layerSlice(graph, {
    visible: ["business", "rules"],
    projections: false,
  }).edges.some((relation) => relation.derived),
  false,
);
const changed = {
  ...view,
  concept_structure: { ...view.concept_structure, revision: "confirmed-2" },
};
assert.notEqual(graphVersion(changed), graphVersion(view));
assert.notEqual(renderRevision(changed), renderRevision(view));
const recording = {
  id: "r",
  status: "stopped",
  context: view,
  final: { machine: view.machine },
  events: [],
  commands: [],
  started_at: "2026-11-04T00:00:00Z",
  ended_at: "2026-11-04T00:00:01Z",
};
assert.equal(recordingMatches(recording, changed), false);
assert.equal(frame(recording, 0).concept_structure.revision, "confirmed-1");
const trace = buildTraceIndex(recording, timeline(recording), inventory.all);
assert.equal(
  [...trace.rows.values()].flatMap((row) => row.slices).length,
  0,
  "A design map creates no invocation or duration",
);
assert.equal(
  JSON.stringify(view),
  before,
  "All projections preserve source and concept identities",
);

/** Exercise the same inventory, filter and enclosure path used by both renderers. */
function displayFixture(fixtureNodes, fixtureEdges, preset, { layered = false, regions } = {}) {
  const fixture = {
    ...view,
    concept_structure: undefined,
    model: { nodes: fixtureNodes, edges: fixtureEdges, machine: { values: [], transitions: [] } },
  };
  const profile = profileFor(preset);
  if (regions) profile.regions = regions;
  const graph = layoutGraph(
    fixture,
    new Set(fixtureNodes.map((node) => node.id)),
    new Set(),
    new Map(),
    "latest",
    "latest",
    {
      match: (all, events, status, relations) =>
        matchingNodes(all, fixture, events, profile, status, relations),
    },
  );
  graph.layered = layered;
  refreshHierarchy(graph);
  return { graph, shown: presentationGraph(graph, profile) };
}

// A state machine has display ancestry derived from typed semantic membership.
// Ordinary 2D can use regions; layered/3D retains its plane relationship links.
const stateNodes = [
  concept("machine", "state", "state_model", "state"),
  concept("parent", "state", "state", "state"),
  concept("child", "state", "state", "state"),
];
const stateEdges = [
  edge("mp", "machine", "parent", "contains"),
  edge("pc", "parent", "child", "contains"),
];
const stateBefore = JSON.stringify({ stateNodes, stateEdges });
for (const layered of [false, true]) {
  const { graph, shown } = displayFixture(stateNodes, stateEdges, "states", { layered });
  assert.deepEqual(
    [...hierarchyOf(graph).parents],
    [
      ["parent", "machine"],
      ["child", "parent"],
    ],
  );
  assert.deepEqual([...shown.regions].sort(), ["machine", "parent"]);
  assert.equal(graph.all.get("child").display_parent_kind, "state_hierarchy");
  for (const relation of stateEdges)
    assert.ok(
      shown.edges.some((drawn) => drawn.members.some((member) => member.id === relation.id)) ||
        (!layered && shown.regions.has(relation.from)),
      `Containment is represented in ${layered ? "3D" : "2D"}: ${relation.id}`,
    );
  if (layered) {
    // Check the actual spatial scene adapter and volume builder, beyond merely
    // selecting the layered flag on a planar projection.
    prepareSpatialHierarchy(graph, { positions: {} });
    const scene = spatialModel(graph, presentationGraph(graph, profileFor("states")));
    const positions = Object.fromEntries(
      scene.nodes.map((node, index) => [node.id, { x: index * 60, y: 0, z: 0 }]),
    );
    const volumes = containmentVolumes(scene, positions, 260);
    assert.deepEqual(new Set(volumes.map((region) => region.id)), new Set(["machine", "parent"]));
    assert.ok(volumes.every((region) => region.members.includes("child")));
  }
}
const noRegions = displayFixture(stateNodes, stateEdges, "states", { regions: [] });
assert.equal(noRegions.shown.regions.size, 0);
assert.deepEqual(
  new Set(noRegions.shown.edges.flatMap((drawn) => drawn.members.map((member) => member.id))),
  new Set(["mp", "pc"]),
);

// Containment with no unique valid display owner must remain an explicit edge.
const ambiguousEdges = [...stateEdges, edge("mc", "machine", "child", "contains")];
const ambiguous = displayFixture(stateNodes, ambiguousEdges, "states");
assert.equal(ambiguous.graph.all.get("child").parent, undefined);
assert.ok(
  ambiguous.shown.edges.some((drawn) => drawn.members.some((member) => member.id === "pc")),
);
const cyclic = displayFixture(
  stateNodes,
  [...stateEdges, edge("cp", "child", "parent", "contains")],
  "states",
);
assert.ok(cyclic.shown.edges.length, "A malformed display hierarchy does not erase its relations");
const nativeOwner = displayFixture(
  [
    ...stateNodes.slice(0, 2),
    { ...stateNodes[2], parent: "machine", source: { path: "state.py", symbol: "child" } },
  ],
  stateEdges,
  "states",
);
assert.equal(
  nativeOwner.graph.all.get("child").parent,
  "machine",
  "Display adaptation preserves explicit native ownership",
);
assert.equal(
  JSON.stringify({ stateNodes, stateEdges }),
  stateBefore,
  "The canonical concept graph remains untouched",
);

// Polarity survives grouping even when two guards share visible endpoints.
const guardedNodes = [
  concept("t", "state", "transition", "action"),
  concept("g", "state", "guard", "decision"),
];
const guardedEdges = [false, true].map((negated) => ({
  ...edge("guard:" + negated, "t", "g", "guarded_by"),
  negated,
}));
for (const [language, expected] of [
  ["en", ["Requires true", "Requires false"]],
  ["zh-CN", ["条件成立", "条件不成立"]],
]) {
  setLocale(language);
  const { shown } = displayFixture(guardedNodes, guardedEdges, "states");
  assert.equal(shown.edges.length, 2);
  assert.deepEqual(
    shown.edges.map((edge) => relationName(edge)),
    expected,
  );
  assert.ok(
    shown.edges.every((edge) => !edge.observed),
    "A guard diagram creates no runtime result",
  );
}
setLocale("en");

// Static and observed function families must keep calls, parameters and mappings.
const functionNodes = [
  { id: "f", kind: "function", code_role: "function", label: "f" },
  { id: "g", kind: "function", code_role: "function", label: "g" },
  { id: "p", kind: "data", code_role: "parameter", parent: "f", label: "p" },
  { id: "ref", kind: "function", code_role: "reference", label: "observed f" },
];
const functionEdges = [
  { id: "call", from: "f", to: "g", type: "call", code_relation: "calls", origin: "code-index" },
  {
    id: "parameter",
    from: "f",
    to: "p",
    type: "data",
    code_relation: "parameter",
    origin: "code-index",
  },
  { id: "map", from: "ref", to: "f", type: "maps", code_relation: "maps", origin: "code-index" },
];
for (const preset of ["functions", "code", "implementation"]) {
  const { shown } = displayFixture(functionNodes, functionEdges, preset);
  for (const relation of functionEdges)
    assert.ok(
      shown.edges.some((drawn) => drawn.members.some((member) => member.id === relation.id)),
      preset + " retains " + relation.id,
    );
}
const customFunctions = displayFixture(functionNodes, functionEdges, "functions");
const noStaticCalls = presentationGraph(customFunctions.graph, {
  ...profileFor("functions"),
  edges: ["code-parameter", "code-maps"],
});
assert.equal(
  noStaticCalls.edges.some((drawn) => drawn.members.some((member) => member.id === "call")),
  false,
  "Preset repair still respects an explicit user relation filter",
);
console.log(
  "PASS: peer design views, guard polarity, typed containment in 2D/3D, complete function relations, source binding, indirect witnesses, revision isolation and no fabricated lifecycle.",
);
