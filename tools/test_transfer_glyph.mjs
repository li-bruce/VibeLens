/** Direction follows the exact drawn path for outbound and returning transfers. */
import assert from "node:assert/strict";
import {transferPose, transferPolygon} from "../skills/vibelens/assets/stategraph-viewer/transfer-glyph.js";
import {transferGeometry} from "../skills/vibelens/assets/stategraph-viewer/spatial-geometry.js";
import {bezierAt} from "../skills/vibelens/assets/stategraph-viewer/renderer.js";
const paths = [
  {points: [{x: 0, y: 0}, {x: 80, y: 0}]},
  {points: [{x: 0, y: 0}, {x: 0, y: 40}, {x: 80, y: 40}]},
  {start: {x: 0, y: 0}, c1: {x: 15, y: 80}, c2: {x: 90, y: -60}, end: {x: 100, y: 0}},
];
for (const path of paths) for (const progress of [0, 0.2, 0.7, 1]) {
  const sample = (t) => bezierAt(path, t);
  const forward = transferPose(sample, progress), back = transferPose(sample, 1 - progress, true);
  assert.ok(Math.hypot(forward.point.x - back.point.x, forward.point.y - back.point.y) < 1e-8);
  assert.ok(Math.abs(forward.direction.x * back.direction.x + forward.direction.y * back.direction.y + 1) < 1e-8);
  const polygon = transferPolygon(forward, 5);
  assert.equal(polygon.length, 14);
  assert.ok(polygon.every(Number.isFinite));
  // The first vertex is the arrow tip, ahead of the sampled point along travel.
  assert.ok((polygon[0] - forward.point.x) * forward.direction.x
    + (polygon[1] - forward.point.y) * forward.direction.y > 0);
}
const vertical = transferPose(t => ({x: 3, y: t * 400, z: 8}), 0.5, true);
assert.deepEqual(vertical.direction, {x: -0, y: -1, z: -0});
assert.ok(Object.values(transferPose(() => ({x: 0, y: 0}), 0).direction).every(Number.isFinite));
const arrow = transferGeometry();
arrow.computeBoundingBox();
assert.equal(arrow.boundingBox.min.y, -7);
assert.equal(arrow.boundingBox.max.y, 7);
assert.ok(arrow.attributes.position.count < 100);
console.log("PASS: straight, routed, curved, reverse, cross-layer and degenerate transfer arrows.");
