/** Layer geometry and playback selections are presentation-only, with stable identities. */
import assert from "node:assert/strict";
import {
  layers,
  cleanLayers,
  layerHeights,
} from "../skills/vibelens/assets/stategraph-viewer/graph-layers.js";
import { edgeCurve } from "../skills/vibelens/assets/stategraph-viewer/spatial-paths.js";
import {
  regionPort,
  routePoints,
  polylineAt,
  busTrunks,
} from "../skills/vibelens/assets/stategraph-viewer/edge-routing.js";
import {
  cleanReplaySelection,
  selectedReplayPlan,
  nextReplayIndex,
} from "../skills/vibelens/assets/stategraph-viewer/replay-selection.js";
import { SpatialRenderer } from "../skills/vibelens/assets/stategraph-viewer/spatial-renderer.js";
import { solveSpatial } from "../skills/vibelens/assets/stategraph-viewer/spatial-layout.js";

const config = cleanLayers({
  order: ["state", "business", "state", "invalid"],
  gaps: { state: 420 },
  gap: 260,
});
assert.equal(new Set(config.order).size, layers.length);
assert.deepEqual(config.order.slice(0, 2), ["state", "business"]);
const heights = layerHeights(config);
assert.equal(heights.get("state") - heights.get("business"), 420);
assert.deepEqual(
  layerHeights({ ...config, visible: ["business"] }),
  heights,
  "Masks preserve layer slots",
);
assert.equal(layerHeights({}).get("api"), 1820, "Default fixed 260 gaps");
const positions = solveSpatial({
  nodes: [
    { id: "a", layer: "state" },
    { id: "b", layer: "business" },
  ],
  edges: [],
  layers,
  settings: config,
  gap: 260,
  positions: { a: { x: 1, y: -9, z: 2, pinned: true } },
});
assert.equal(
  positions.a.y,
  heights.get("state"),
  "Saved old height never overrides current planes",
);
assert.equal(positions.a.x, 1);

const volume = {
  id: "group",
  center: { x: 10, y: 260, z: 20 },
  radius: 80,
  members: ["inside"],
  projection: false,
};
const saved = { group: { x: 0, y: 260, z: 0 } };
const port = regionPort("group", "external", { x: 300, y: 0, z: 190 }, saved, [volume]);
assert.ok(Math.abs(Math.hypot(port.x - 10, port.z - 20) - 80) < 1e-9);
assert.equal(port.y, 260);
assert.deepEqual(regionPort("group", "inside", port, saved, [volume]), saved.group);
assert.equal(
  regionPort("group", "external", volume.center, saved, [volume]).x,
  90,
  "Stacked groups have finite rim ports",
);
for (const style of ["curve", "straight", "orthogonal", "bus"]) {
  const a = { x: 0, y: 260, z: 0, pinned: true },
    b = { x: 200, y: 260, z: 300, pinned: false };
  const curve = edgeCurve(a, b, style, 80);
  assert.deepEqual(curve.getPoint(0).toArray(), [0, 260, 0]);
  assert.deepEqual(curve.getPoint(1).toArray(), [200, 260, 300]);
  assert.ok(curve.getPoints(40).every((p) => p.y === 260));
  assert.ok(
    edgeCurve(a, a, style)
      .getPoints(20)
      .some((p) => p.distanceTo(curve.getPoint(0)) > 1),
    "Self loops stay visible",
  );
}
const rightAngles = routePoints({ x: 0, y: 0 }, { x: 100, y: 200 }, "orthogonal");
assert.ok(
  rightAngles.slice(1).every((p, i) => p.x === rightAngles[i].x || p.y === rightAngles[i].y),
);
assert.deepEqual(
  polylineAt(
    [
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      { x: 100, y: 100 },
    ],
    0.75,
  ),
  { x: 100, y: 50 },
);
const edges = [
  { id: "e1", from: "a", to: "b", type: "call" },
  { id: "e2", from: "a", to: "c", type: "call" },
  { id: "rule", from: "a", to: "c", type: "guard" },
];
const points = { a: { x: 0 }, b: { x: 100 }, c: { x: 200 } };
const trunks = busTrunks(edges, (id) => points[id]);
assert.equal(trunks.get("e1"), trunks.get("e2"));
assert.equal(trunks.has("rule"), false, "Different relation kinds do not merge");

const items = Array.from({ length: 7 }, (_, i) => ({ id: `fact-${i}`, value: i }));
const before = JSON.stringify(items),
  selection = { skipped: ["fact-2", "fact-4", "stale"], loop: true, from: "fact-5", to: "fact-1" };
assert.deepEqual(cleanReplaySelection(selection, items).skipped, ["fact-2", "fact-4"]);
assert.deepEqual(selectedReplayPlan(items, [0, 1, 2, 3, 4, 5, 6], selection), [1, 3, 5]);
assert.equal(nextReplayIndex([1, 3, 5], 5, true), 1);
assert.equal(nextReplayIndex([1, 3, 5], 5, false), undefined);
assert.equal(nextReplayIndex([], 5, true), undefined);
assert.equal(JSON.stringify(items), before, "No selection edits recorded facts");
console.log(
  "PASS: layer order/gaps, pinned plane correction, circular ports, four routes, typed buses, skip/range loops and immutable events.",
);

const badge = { dataset: {} },
  label = { querySelector: () => badge };
SpatialRenderer.prototype.updateBadges.call({}, label, { id: "flat", state: "declared" });
assert.equal(badge.dataset.childCount, "", "Absent child metadata remains unknown");
assert.equal(badge.hidden, true);
SpatialRenderer.prototype.updateBadges.call({}, label, {
  kids: ["a", "b"],
  state: "active",
  open: true,
});
assert.equal(badge.dataset.childCount, "2");
assert.ok(badge.textContent.includes("▶") && badge.textContent.includes("2"));
