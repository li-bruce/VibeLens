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

/** Keep circle captions below their projected rims without overlapping targets.
 * The renderer caps captions at 300. A deterministic sweep checks each earlier
 * rectangle at most once per caption; no simulation or source graph changes.
 */
export function stackRegionCaptions(captions, gap = 4) {
  const placed = [],
    result = new Map();
  for (const caption of captions
    .slice()
    .sort((a, b) => a.y - b.y || a.x - b.x || a.key.localeCompare(b.key))) {
    const left = caption.x - caption.width / 2,
      right = left + caption.width;
    let top = caption.y;
    for (const previous of placed)
      if (
        left < previous.right + gap &&
        right + gap > previous.left &&
        top < previous.bottom + gap &&
        top + caption.height + gap > previous.top
      )
        top = previous.bottom + gap;
    const rectangle = { left, right, top, bottom: top + caption.height };
    placed.push(rectangle);
    placed.sort((a, b) => a.top - b.top);
    result.set(caption.key, { x: caption.x, y: top, shift: top - caption.y });
  }
  return result;
}
