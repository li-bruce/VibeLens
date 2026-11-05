/** Presentation-only sampling shared by both renderers. A return transfer reverses
 * its direction as well as its position. Sample the rendered path, including
 * routed bends, so arrows never imply a different relationship or trajectory.
 */
export function transferPose(sample, progress, reverse = false) {
  const t = Math.max(0, Math.min(1, reverse ? 1 - progress : progress));
  const point = sample(t);
  const before = sample(Math.max(0, t - 0.001));
  const after = sample(Math.min(1, t + 0.001));
  const sign = reverse ? -1 : 1;
  const delta = {
    x: (after.x - before.x) * sign,
    y: (after.y - before.y) * sign,
    z: ((after.z || 0) - (before.z || 0)) * sign,
  };
  const length = Math.hypot(delta.x, delta.y, delta.z);
  return {
    point,
    direction:
      length > 1e-9
        ? { x: delta.x / length, y: delta.y / length, z: delta.z / length }
        : { x: sign, y: 0, z: 0 },
  };
}

/** A compact arrow with a visible head and tail, expressed in screen-size units. */
export function transferPolygon(pose, size) {
  const { point, direction } = pose;
  return [
    [1.5, 0],
    [-0.1, -0.85],
    [-0.1, -0.32],
    [-1.2, -0.32],
    [-1.2, 0.32],
    [-0.1, 0.32],
    [-0.1, 0.85],
  ].flatMap(([along, across]) => [
    point.x + size * (along * direction.x - across * direction.y),
    point.y + size * (along * direction.y + across * direction.x),
  ]);
}
