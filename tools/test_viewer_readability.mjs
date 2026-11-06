/** Geometry, naming and preset contracts shared by both renderers. */
import assert from "node:assert/strict";
import {
  fittedScale,
  zoomedScale,
  wheelFactor,
} from "../skills/vibelens/assets/stategraph-viewer/viewport-scale.js";
import {
  curveBundles,
  bundledCurve,
} from "../skills/vibelens/assets/stategraph-viewer/curve-bundling.js";
import { routeScene } from "../skills/vibelens/assets/stategraph-viewer/routing-engine.js";
import { matchingNodes, profileFor } from "../skills/vibelens/assets/stategraph-viewer/analysis.js";
import { nameNode } from "../skills/vibelens/assets/stategraph-viewer/graph-names.js";
import { graphInventory } from "../skills/vibelens/assets/stategraph-viewer/graph-inventory.js";
import { setLocale } from "../skills/vibelens/assets/stategraph-viewer/i18n.js";

for (const layer of ["business", "state", "rules", "entry", "structure", "symbols", "data"]) {
  const area = { width: 1000, height: 700 },
    width = 60000,
    height = 40000;
  const scale = fittedScale(width, height, area);
  assert.ok(width * scale <= area.width && height * scale <= area.height, layer);
  assert.ok(zoomedScale(scale, 0.1, width, height, area) < scale);
}
assert.equal(
  wheelFactor({ deltaY: 1, deltaMode: 1 }, 800),
  wheelFactor({ deltaY: 16, deltaMode: 0 }, 800),
);
assert.ok(wheelFactor({ deltaY: -100, deltaMode: 0 }, 800) > 1);

const nodes = [
  { id: "network", kind: "business", layer: "business", concept_kind: "business_network" },
  { id: "object", kind: "business", layer: "business", concept_kind: "object" },
  ...["upload", "share", "list", "read", "revoke"].map((id) => ({
    id,
    kind: "business",
    layer: "business",
    concept_kind: "operation",
    parent: "network",
  })),
];
const edges = ["share", "list", "read", "revoke"].map((to, i) => ({
  id: "e" + i,
  from: "upload",
  to,
  type: "flow",
}));
const view = { model: { nodes, edges, machine: {} } };
const selection = matchingNodes(
  new Map(nodes.map((n) => [n.id, n])),
  view,
  [],
  profileFor("business"),
  () => "idle",
);
assert.deepEqual([...selection].sort(), ["upload", "share", "list", "read", "revoke"].sort());
const model = {
  presentation: {
    names: {
      concepts: {
        "state:grant": { en: "Active grant", "zh-CN": "授权有效" },
        "rule:grant": { en: "Grant remains active", "zh-CN": "授权仍然有效" },
      },
    },
  },
};
setLocale("zh-CN");
const mapped = graphInventory({
  model: { nodes: [], edges: [], machine: { values: [], transitions: [] } },
  concept_structure: {
    nodes: [],
    edges: [
      {
        id: "map",
        from: "a",
        to: "b",
        type: "data",
        origin: "concept-binding",
        label: "Implemented by",
      },
    ],
  },
});
assert.equal(mapped.rawEdges.find((e) => e.id === "map").label, "对应实现");
for (const [lang, expected] of [
  ["zh-CN", ["授权有效", "授权仍然有效"]],
  ["en", ["Active grant", "Grant remains active"]],
]) {
  setLocale(lang);
  const result = ["state:grant", "rule:grant"].map((id) =>
    nameNode({ id, concept_kind: "predicate", label: "active" }, model),
  );
  assert.deepEqual(
    result.map((n) => n.label),
    expected,
  );
  assert.deepEqual(
    result.map((n) => n.id),
    ["state:grant", "rule:grant"],
  );
}
function edge(id, y = 10, target = 0) {
  return {
    id,
    from: "a" + id,
    to: "b" + id,
    type: "flow",
    fromLayer: "business",
    toLayer: target ? "state" : "business",
    a: { x: 10, y, level: 0 },
    b: { x: 800, y: 130 - y, level: target },
    allowed: [],
  };
}
const scene = {
  style: "curve",
  bundling: true,
  obstacles: [],
  parents: [],
  edges: [edge("1", 10), edge("2", 100)],
};
const groups = curveBundles(scene, (e) => e.type);
assert.equal(groups.size, 1);
const bundle = [...groups.values()][0];
const path = bundledCurve(scene.edges[0], bundle);
assert.deepEqual(path[0], scene.edges[0].a);
assert.deepEqual(path.at(-1), scene.edges[0].b);
assert.ok(path.every((p) => p.level === 0));
assert.equal(curveBundles({ ...scene, bundling: false }, (e) => e.type).size, 0);
assert.equal(
  curveBundles({ ...scene, edges: [edge("1"), { ...edge("2"), type: "call" }] }, (e) => e.type)
    .size,
  0,
);
assert.equal(
  curveBundles({ ...scene, edges: [edge("1"), edge("2", 50, 260)] }, (e) => e.type).size,
  0,
);
const cross = { ...scene, edges: [edge("1", 10, 260), edge("2", 100, 260)] };
const crossPath = bundledCurve(cross.edges[0], [...curveBundles(cross, (e) => e.type).values()][0]);
assert.ok(crossPath.every((p, i) => !i || p.level >= crossPath[i - 1].level));
const on = await routeScene(scene),
  off = await routeScene({ ...scene, bundling: false });
assert.equal(on.stats.bundles, 1);
assert.equal(on.stats.bundledEdges, 2);
assert.notDeepEqual(on.routes.get("1"), off.routes.get("1"));
const moved = await routeScene({ ...scene, edges: [edge("1", 60), edge("2", 100)] });
assert.notDeepEqual(moved.routes.get("1"), on.routes.get("1"));
const blocked = await routeScene({
  ...scene,
  obstacles: [{ id: "wall", key: "wall", kind: "glyph", x: 405, y: 65, r: 25, level: 0 }],
});
assert.equal(blocked.stats.bundles, 0, "A bundle crossing a node is not accepted");
assert.equal(blocked.routes.size, 2, "Obstacle fallback retains every edge");
const large = {
  ...scene,
  edges: Array.from({ length: 10000 }, (_, i) => edge(String(i), 10 + (i % 100))),
};
const start = performance.now(),
  result = await routeScene(large),
  elapsed = performance.now() - start;
assert.equal(result.routes.size, 10000);
assert.equal(result.stats.bundledEdges, 10000);
assert.ok(elapsed < 5000, "Ten thousand compatible curves stay within the worker budget");
console.log(
  JSON.stringify({
    valid: true,
    layers: 7,
    bundledEdges: result.routes.size,
    milliseconds: Math.round(elapsed),
  }),
);
