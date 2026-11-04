/** Hidden rings cannot route edges; dragging uses the visible body's depth. */
import assert from "node:assert/strict";
import * as T from "../skills/vibelens/assets/stategraph-viewer/spatial-three.vendor.js";
import {
  SpatialRenderer,
  visibleSpatialBodies,
  visibleSpatialPoints,
  spatialProjectionGuides,
} from "../skills/vibelens/assets/stategraph-viewer/spatial-renderer.js";
import { spatialScene } from "../skills/vibelens/assets/stategraph-viewer/routing-scene.js";
import { stackRegionCaptions } from "../skills/vibelens/assets/stategraph-viewer/spatial-labels.js";

const owner = { id: "database", layer: "data", glyph: false, region: true },
  self = { id: "self", layer: "business", glyph: true, region: true },
  model = {
    nodes: [owner, self],
    edges: [{ id: "call", from: "database", to: "self", sourceRegion: true }],
  },
  positions = {
    database: { x: -10000, y: 260, z: -4104, pinned: true },
    self: { x: 400, y: 520, z: 100 },
  },
  projection = {
    id: "database",
    layer: "code",
    projection: true,
    center: { x: 50, y: 0, z: 20 },
    radius: 80,
    members: [],
  },
  own = {
    id: "self",
    layer: "business",
    projection: false,
    center: positions.self,
    radius: 100,
    members: ["self"],
  },
  volumes = [projection, own],
  before = JSON.stringify({ model, positions, volumes });

const enabled = visibleSpatialBodies(model, volumes, true);
assert.equal(enabled.volumes.length, 2);
assert(!enabled.glyphs.has(owner.id), "A visible owner ring represents its hidden center glyph");
assert(enabled.glyphs.has(self.id), "Real self glyph remains displayed with its ring");
const disabled = visibleSpatialBodies(model, volumes, false);
assert.deepEqual(disabled.volumes, [own]);
assert(
  disabled.glyphs.has(owner.id),
  "Projection-only owners retain a visible, selectable identity",
);
assert(disabled.glyphs.has(self.id));
const shownRoute = spatialScene(model, positions, enabled.volumes, "straight").edges[0],
  hiddenRoute = spatialScene(model, positions, disabled.volumes, "straight").edges[0];
assert.equal(shownRoute.a.level, projection.center.y);
assert.deepEqual(
  hiddenRoute.a,
  {
    x: positions.database.x,
    y: positions.database.z,
    level: positions.database.y,
  },
  "An endpoint uses its visible fallback glyph, not a hidden projection rim",
);
assert.equal(JSON.stringify({ model, positions, volumes }), before);
const captions = Array.from({ length: 300 }, (_, index) => ({
    key: `owner:${index}`,
    x: 200 + (index % 3),
    y: 100 + (index % 7),
    width: 120,
    height: 30,
  })),
  placed = stackRegionCaptions(captions);
assert.deepEqual(
  placed,
  stackRegionCaptions(captions.toReversed()),
  "Caption placement is deterministic",
);
for (let i = 0; i < captions.length; i++) {
  const a = captions[i],
    position = placed.get(a.key);
  assert.equal(position.x, a.x);
  assert(position.y >= a.y, "Captions remain below their own projected circle rims");
  for (const b of captions.slice(i + 1)) {
    const other = placed.get(b.key);
    assert(
      position.y + a.height <= other.y || other.y + b.height <= position.y,
      "Nested caption rectangles retain distinct pointer targets",
    );
  }
}
const fittedPoints = visibleSpatialPoints(positions, enabled.volumes, enabled.glyphs);
assert(
  fittedPoints.every((point) => point.x > -1000 && point.z > -1000),
  "Hidden saved anchors cannot enlarge camera or plane bounds",
);
const focusPoints = visibleSpatialPoints(
  positions,
  enabled.volumes,
  enabled.glyphs,
  new Set(["database"]),
);
assert.equal(focusPoints.length, 2);
assert.deepEqual(focusPoints, [
  { x: -30, y: 0, z: -60 },
  { x: 130, y: 0, z: 100 },
]);
assert.deepEqual(
  spatialProjectionGuides(positions, enabled.volumes, enabled.glyphs),
  [],
  "A sole projected owner ring has no guide from its invisible saved point",
);
const secondProjection = {
    ...projection,
    layer: "api",
    center: { x: 20, y: 260, z: 5 },
  },
  guides = spatialProjectionGuides(positions, [...volumes, secondProjection], enabled.glyphs);
assert.equal(guides.length, 1);
assert.deepEqual(guides[0].fromPosition, projection.center);
assert.deepEqual(guides[0].toPosition, secondProjection.center);

const camera = new T.PerspectiveCamera(43, 1, 1, 100000);
camera.position.set(600, 600, 1000);
camera.lookAt(0, 0, 0);
camera.updateMatrixWorld();
const canvas = {
  getBoundingClientRect: () => ({ left: 0, top: 0, width: 800, height: 800 }),
  setPointerCapture() {},
};
function start(hit) {
  const context = {
    camera,
    canvas,
    raycaster: new T.Raycaster(),
    callbacks: {},
    controls: { enabled: true },
    positions,
    branch: () => ["database", "self"],
  };
  SpatialRenderer.prototype.startDrag.call(
    context,
    {
      button: 0,
      clientX: 400,
      clientY: 400,
      pointerId: 1,
      preventDefault() {},
      stopImmediatePropagation() {},
    },
    hit,
  );
  return context;
}
const ringDrag = start({ region: owner.id, anchor: projection.center });
assert(
  Math.abs(
    ringDrag.dragPlane.distanceToPoint(
      new T.Vector3(projection.center.x, projection.center.y, projection.center.z),
    ),
  ) < 1e-7,
  "The drag plane passes through the actual clicked ring",
);
assert(
  Math.abs(
    ringDrag.dragPlane.distanceToPoint(
      new T.Vector3(positions.database.x, positions.database.y, positions.database.z),
    ),
  ) > 1000,
  "A stale hidden owner cannot set the ring drag depth",
);
assert.deepEqual(ringDrag.dragIds, ["database", "self"]);
assert.deepEqual(ringDrag.dragPositions, positions);
assert.notEqual(
  ringDrag.dragPositions,
  positions,
  "Drag snapshots do not mutate saved coordinates",
);
const glyphDrag = start({ id: owner.id });
assert(
  Math.abs(
    glyphDrag.dragPlane.distanceToPoint(
      new T.Vector3(positions.database.x, positions.database.y, positions.database.z),
    ),
  ) < 1e-7,
  "A visible glyph retains its own physical drag anchor",
);
assert.equal(JSON.stringify({ model, positions, volumes }), before);
console.log("Spatial ring visibility, endpoint routing and perspective drag anchors passed");
