/** Anchor below the projected circumference, for any orbit angle.
 * Screen projections are supplied by the renderer; this function reads no DOM.
 */
export function regionLabelAnchor(volume, project) {
  const at = (angle) =>
    project({
      x: volume.center.x + Math.cos(angle) * volume.radius,
      y: volume.center.y,
      z: volume.center.z + Math.sin(angle) * volume.radius,
    });
  let best = null,
    angle = 0,
    step = Math.PI / 16;
  for (let i = 0; i < 32; i++) {
    const p = at(i * step);
    if ((p.depth === undefined || (p.depth > -1 && p.depth < 1)) && (!best || p.y > best.y)) {
      best = p;
      angle = i * step;
    }
  }
  if (!best) return { visible: false, x: 0, y: 0 };
  for (let i = 0; i < 3; i++) {
    step /= 2;
    for (const next of [angle - step, angle + step]) {
      const p = at(next);
      if ((p.depth === undefined || (p.depth > -1 && p.depth < 1)) && p.y > best.y) {
        best = p;
        angle = next;
      }
    }
  }
  return { ...best, y: best.y + 7 };
}
