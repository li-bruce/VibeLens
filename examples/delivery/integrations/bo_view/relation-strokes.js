/** Small renderer-independent stroke profiles. All widths are relative to the
 * renderer's base line width, so zooming never turns a double line into a fill.
 */
export const strokeProfiles = {
  single: { mode: 0, width: 1 },
  double: { mode: 1, width: 3.2, gap: 0.36 },
  bordered: { mode: 2, width: 3, inset: 0.42, tint: 0.68 },
};

export function strokeProfile(style) {
  return strokeProfiles[style.stroke] || strokeProfiles.single;
}

/** Lighten within the same hue for a bordered line's center, not its background. */
export function strokeTint(color, amount = strokeProfiles.bordered.tint) {
  const channel = (shift) => {
    const value = (color >> shift) & 255;
    return Math.round(value + (255 - value) * amount);
  };
  return (channel(16) << 16) | (channel(8) << 8) | channel(0);
}

/** Parallel rails retain the route's centerline for picking and playback.
 * Clamp joins at sharp bends and remove zero-length steps to avoid long spikes.
 */
export function offsetPolyline(points, offset) {
  const clean = points.filter(
    (point, i) => !i || Math.hypot(point.x - points[i - 1].x, point.y - points[i - 1].y) > 1e-8,
  );
  if (clean.length < 2) return clean;
  const normals = clean.slice(1).map((point, i) => {
    const dx = point.x - clean[i].x,
      dy = point.y - clean[i].y;
    const length = Math.hypot(dx, dy);
    return { x: -dy / length, y: dx / length };
  });
  return clean.map((point, i) => {
    const a = normals[Math.max(0, i - 1)],
      b = normals[Math.min(i, normals.length - 1)];
    const x = a.x + b.x,
      y = a.y + b.y,
      length = Math.hypot(x, y);
    const n = length > 1e-8 ? { x: x / length, y: y / length } : b;
    const miter = Math.min(2, 1 / Math.max(0.25, n.x * b.x + n.y * b.y));
    return { ...point, x: point.x + n.x * offset * miter, y: point.y + n.y * offset * miter };
  });
}

/** Describe 2D draw passes without painting over the content between two rails. */
export function strokePasses(points, style, baseWidth) {
  const profile = strokeProfile(style),
    width = baseWidth * (style.width || 1);
  if (profile.mode === 1) {
    const railWidth = (width * profile.width * (1 - profile.gap)) / 2;
    const distance = (width * profile.width * (1 + profile.gap)) / 4;
    return [-distance, distance].map((offset) => ({
      points: offsetPolyline(points, offset),
      color: style.color,
      width: railWidth,
    }));
  }
  const result = [{ points, color: style.color, width: width * profile.width }];
  if (profile.mode === 2)
    result.push({
      points,
      color: strokeTint(style.color),
      width: width * profile.width * profile.inset,
    });
  return result;
}
