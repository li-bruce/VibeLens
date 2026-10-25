import assert from "node:assert/strict";
import {
  layerHeights,
  cleanLayers,
} from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
import { routeScene } from "../skills/vibelens/assets/stategraph-viewer/routing-engine.js";
import {
  shapedPath,
  strokeSegments,
} from "../skills/vibelens/assets/stategraph-viewer/route-shapes.js";
import {
  nodeGeometry,
  objectNames,
} from "../skills/vibelens/assets/stategraph-viewer/spatial-geometry.js";
import { clusterUnits } from "../skills/vibelens/assets/stategraph-viewer/cluster-layout.js";
assert.deepEqual(
  [...layerHeights({ visible: ["business", "state", "code"], gap: 180 })],
  [
    ["code", 0],
    ["state", 180],
    ["business", 360],
  ],
);
assert.deepEqual([...layerHeights({ visible: ["state"], gaps: { state: 600 } })], [["state", 0]]);
assert.equal(
  "gaps" in cleanLayers({ gaps: { state: 600 } }),
  false,
  "Legacy individual gaps cannot restore empty slots",
);
const a = { x: 0, y: 0, level: 0 },
  b = { x: 200, y: 90, level: 260 },
  edge = { id: "e", from: "a", to: "b", a, b };
const scene = { edges: [edge], obstacles: [], parents: [] };
const cache = new Map();
for (const style of ["curve", "straight", "orthogonal", "straight", "curve", "straight"]) {
  const r = await routeScene({ ...scene, style }, null, cache);
  assert.equal(r.routes.size, 1);
  const points = r.routes.get("e");
  assert.deepEqual(points[0], a);
  assert.deepEqual(points.at(-1), b);
  if (style === "straight")
    assert.deepEqual(points, [a, b], "Changing style never retains a dogleg");
  if (style === "curve")
    assert.ok(
      points.length > 10 && Math.abs(points[12].x - 100) > 5,
      "A cross-layer curve has a real bow",
    );
}
const flat = { ...edge, b: { ...b, level: 0 } };
assert.ok(shapedPath(flat, "curve").every((p) => p.level === 0));
const obstructed = await routeScene(
  {
    ...scene,
    style: "straight",
    obstacles: [{ id: "middle", key: "m", kind: "glyph", x: 100, y: 45, level: 130, r: 30 }],
  },
  null,
);
assert.deepEqual(obstructed.routes.get("e"), [a, b]);
assert.equal(
  obstructed.stats.intersections,
  1,
  "Straight intersections are explicit, never silently bent or omitted",
);
const strokes = strokeSegments(
  [
    { x: 0, y: 0, z: 0 },
    { x: 25, y: 0, z: 0 },
    { x: 1000, y: 0, z: 0 },
  ],
  [10, 5],
  128,
);
assert.ok(strokes.length > 40);
assert.ok(strokes.every(([a, b]) => b.x - a.x <= 11));
assert.ok(
  strokes.some(([a, b]) => a.x <= 30 && b.x >= 35),
  "Dash phase survives a polyline vertex",
);
for (const [type, name] of Object.entries(objectNames)) {
  const g = nodeGeometry(type),
    lod = nodeGeometry(type, true);
  g.computeBoundingBox();
  assert.equal(g.userData.object, name);
  assert.equal(g.userData.family, "VibeLens solids");
  assert.ok(g.boundingBox.max.y - g.boundingBox.min.y >= 0.3, type + " has a genuine solid volume");
  assert.ok([...g.attributes.position.array].every(Number.isFinite));
  assert.ok(
    lod.attributes.position.count < g.attributes.position.count,
    type + " has a cheaper LOD",
  );
  assert.ok(g.attributes.position.count < 6000, type + " keeps instance geometry bounded");
  g.dispose();
  lod.dispose();
}
const units = Array.from({ length: 45 }, (_, i) => ({
  id: "n" + i,
  type: "t" + Math.floor(i / 15),
  radius: 25,
}));
const edges = [
  { from: "n0", to: "n15" },
  { from: "n1", to: "n30" },
];
const output = clusterUnits(units, edges),
  by = new Map(output.map((n) => [n.id, n]));
assert.deepEqual(clusterUnits(units, edges), output, "Layout is deterministic");
const centers = [0, 1, 2].map((t) => {
  const a = units.filter((n) => n.type === "t" + t).map((n) => by.get(n.id));
  return {
    x: a.reduce((s, n) => s + n.x, 0) / a.length,
    y: a.reduce((s, n) => s + n.y, 0) / a.length,
  };
});
for (const n of units) {
  const p = by.get(n.id),
    t = Number(n.type.slice(1)),
    own = centers[t];
  const distance = (q) => Math.hypot(p.x - q.x, p.y - q.y);
  assert.ok(
    distance(own) < Math.min(...centers.filter((_, i) => i !== t).map(distance)),
    "Types remain clustered",
  );
}
for (let i = 0; i < output.length; i++)
  for (let j = i + 1; j < output.length; j++)
    assert.ok(
      Math.hypot(output[i].x - output[j].x, output[i].y - output[j].y) > 49,
      "Clusters do not overlap",
    );
const own = centers[0],
  radial = (n) => Math.hypot(n.x - own.x, n.y - own.y);
const internal = units.slice(2, 15).map((n) => radial(by.get(n.id)));
assert.ok(
  Math.min(radial(by.get("n0")), radial(by.get("n1"))) >
    internal.reduce((a, b) => a + b, 0) / internal.length,
  "Bridge nodes sit toward the cluster rim",
);
const pinned = clusterUnits(
  [
    { id: "pin", type: "a", radius: 40, pin: { x: 42, y: 73 } },
    { id: "new", type: "a", radius: 40 },
  ],
  [],
);
assert.deepEqual(
  pinned.find((n) => n.id === "pin"),
  { id: "pin", x: 42, y: 73 },
);
console.log(
  "PASS: compact visible planes, uniform spacing, faithful shapes/cache, continuous dashes, 19 solid objects/LOD and deterministic typed clusters with pins.",
);
