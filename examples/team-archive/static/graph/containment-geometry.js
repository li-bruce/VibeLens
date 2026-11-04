import { packEnclose } from "./routing-tools.vendor.js";

/** Region boundaries describe visible bodies and the labels rendered beside them. */
export const REGION_PADDING = 12;
export const PLANAR_GLYPH_RADIUS = 33;
export const SPATIAL_GLYPH_RADIUS = 42;

/** Fit visible disks with D3's minimum enclosing-circle algorithm.
 * A deterministic geometric order and D3's seeded shuffle make repeated fits
 * independent of model insertion order. Neither disk inputs nor saved positions
 * are changed. Labels never become invisible anchors in the calculation.
 */
export function enclosingCircle(disks, padding = 0) {
  const circles = disks
    .filter((disk) => [disk.x, disk.y, disk.radius].every(Number.isFinite) && disk.radius >= 0)
    .map((disk) => ({ x: disk.x, y: disk.y, r: disk.radius }))
    .sort((a, b) => a.x - b.x || a.y - b.y || a.r - b.r);
  if (!circles.length) return null;
  const circle = packEnclose(circles);
  return { x: circle.x, y: circle.y, radius: circle.r + Math.max(0, padding) };
}

/** Fit a planar glyph and its actual label rectangle, not an invisible owner.
 * Corner points avoid the old glyph-centered diagonal overestimate for long
 * labels. A small interior margin keeps text away from the enclosing boundary.
 */
export function planarBodyCircle(box) {
  return enclosingCircle(
    [
      { x: box.x + box.w / 2, y: box.y + 31, radius: PLANAR_GLYPH_RADIUS },
      ...[
        [box.x, box.y],
        [box.x + box.w, box.y],
        [box.x + box.w, box.y + box.h],
        [box.x, box.y + box.h],
      ].map(([x, y]) => ({ x, y, radius: 0 })),
    ],
    4,
  );
}
