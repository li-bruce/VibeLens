/** Shared projection contracts; no renderer, browser storage or application mocks. */
import assert from "node:assert/strict";
import { selfRelationOwners } from "../skills/vibelens/assets/stategraph-viewer/containment-semantics.js";
import {
  selectionRoots,
  rectangleSelection,
} from "../skills/vibelens/assets/stategraph-viewer/graph-selection.js";
import { visibilityForView } from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
import {
  restoredFilters,
  layerSelection,
  needsSource,
  layoutSelection,
} from "../skills/vibelens/assets/stategraph-viewer/view-selection.js";
import {
  relationStyle,
  relationCaption,
  emptyFilters,
} from "../skills/vibelens/assets/stategraph-viewer/layout.js";
import {
  explainedName,
  namedView,
} from "../skills/vibelens/assets/stategraph-viewer/graph-names.js";
import { setLocale } from "../skills/vibelens/assets/stategraph-viewer/i18n.js";
import { transferEdges } from "../skills/vibelens/assets/stategraph-viewer/recording.js";
import { respondingNodes } from "../skills/vibelens/assets/stategraph-viewer/playback-appearance.js";

for (const layer of ["business", "state", "rules", "entry", "structure", "symbols", "data"]) {
  const nodes = [
    { id: "owner", layer },
    { id: "child", parent: "owner", layer },
  ];
  const all = new Map(nodes.map((node) => [node.id, node]));
  const graph = { all, byId: all, rawEdges: [] };
  for (const origin of ["code-index", "source-ast", "concept-design", "other-adapter"]) {
    graph.rawEdges = [
      {
        id: "contains",
        from: "owner",
        to: "child",
        type: "data",
        code_relation: "contains",
        origin,
      },
    ];
    assert.deepEqual(
      [...selfRelationOwners(graph)],
      [],
      layer + ": containment is not a self-call",
    );
    graph.rawEdges.push({
      id: "call",
      from: "owner",
      to: "child",
      type: "call",
      origin,
    });
    assert.deepEqual([...selfRelationOwners(graph)], ["owner"]);
    assert.deepEqual([...selfRelationOwners(graph, (edge) => edge.id !== "call")], []);
  }
  assert.deepEqual(selectionRoots(["owner", "child"], all), ["owner"]);
  // Saved-anchor continuity is exercised through actual expansion, dragging
  // and collapse in test_expansion_relations.mjs and its all-plane browser suite.
  assert.deepEqual(
    rectangleSelection({ x: 0, y: 0, w: 20, h: 20 }, [
      { id: "owner", x: 10, y: 10 },
      { id: "child", x: 30, y: 10 },
    ]),
    ["owner"],
  );
}
const boxes = ["left", "right", "hidden"].map((id) => ({ id, x: 0, y: 0 }));
const link = { id: "real-link", from: "left", to: "right", type: "call" };
const complete = {
  boxes,
  byId: new Map(boxes.map((box) => [box.id, box])),
  all: new Map(boxes.map((box) => [box.id, box])),
  regions: [],
  edges: [link],
};
const arrangement = layoutSelection(complete, {
  glyphs: new Set(["left", "right"]),
  regions: new Set(),
  edges: [link],
});
assert.deepEqual(
  arrangement.boxes.map((box) => box.id),
  ["left", "right"],
);
assert.equal(arrangement.all, complete.all, "Hidden identities remain available");
assert.equal(arrangement.edges[0], link, "Layout never invents semantic relations");
assert.equal(complete.boxes.length, 3, "A layout projection never edits the full graph");
const contaminated = {
  layerVisibility: { api: ["business"], "custom-test": ["rules", "state"] },
};
assert.deepEqual(visibilityForView(contaminated, "api"), ["entry"]);
assert.deepEqual(visibilityForView(contaminated, "custom-test"), ["rules", "state"]);
assert.ok(restoredFilters("api", [], emptyFilters()).nodes.includes("code-endpoint"));
assert.ok(!restoredFilters("api", [], emptyFilters()).nodes.includes("business"));
const draft = layerSelection({ ...emptyFilters(), hiddenNodes: ["private"] });
assert.equal(draft.profile.scope, "all");
assert.deepEqual(draft.filters.hiddenNodes, ["private"]);
assert.ok(
  needsSource("custom-draft", {
    layers: { visible: ["business", "structure"] },
  }),
);
assert.notDeepEqual(
  relationStyle({ type: "flow", evidence_kind: "conceptual" }).stroke,
  relationStyle({ type: "guard", evidence_kind: "conceptual" }).stroke,
);
assert.deepEqual(relationStyle({ type: "call" }).dash, []);
assert.equal(relationStyle({ type: "code-imports" }).family, "reference");
assert.equal(relationStyle({ type: "code-parameter" }).family, "containment");
assert.equal(relationCaption({ type: "call", label: "Call" }), "");
assert.equal(relationCaption({ type: "code-imports", label: "imports" }), "");
assert.equal(
  relationCaption({ type: "flow", label: "When access is revoked" }),
  "When access is revoked",
);
setLocale("en");
assert.equal(explainedName({ "zh-CN": "共享" }), "");
assert.equal(explainedName("共享"), "");
setLocale("zh-CN");
assert.equal(explainedName({ en: "Share" }), "");
assert.equal(explainedName("Share"), "");
assert.equal(explainedName({ en: "Share", "zh-CN": "共享" }), "共享");
const original = {
  model: {
    nodes: [{ id: "action", label: "Share", source: { symbol: "share_file" } }],
    edges: [],
    machine: { values: [] },
  },
};
assert.equal(namedView(original).model.nodes[0].label, "share_file");
assert.equal(original.model.nodes[0].label, "Share");

// A confirmed concept may reuse an observed native action. Only an explicit
// causal dependency animates its conceptual flow; adjacent timestamps cannot.
const all = new Map(
  ["a", "b"].map((id) => [
    id,
    {
      id,
      concept_observation: {
        kind: "call",
        sources: [{ node: "native_" + id }],
      },
    },
  ]),
);
const earlier = { id: "first", node: "native_a" },
  later = {
    id: "second",
    node: "native_b",
    depends: [{ event: "first", type: "control" }],
  };
const edges = [
  {
    id: "route",
    from: "a",
    to: "b",
    type: "flow",
    evidence_kind: "conceptual",
  },
];
assert.deepEqual(transferEdges(later, [earlier, later], edges, all), ["route"]);
assert.deepEqual(transferEdges({ ...later, depends: [] }, [earlier, later], edges, all), []);
assert.deepEqual(
  [...respondingNodes(later, { all }, { glyphs: new Set(["a", "b"]), regions: new Set() })],
  ["b"],
);
console.log(
  JSON.stringify({
    passed: true,
    layers: 7,
    origins: 4,
    selection: true,
    presets: true,
    locales: true,
    causalPlayback: true,
  }),
);
