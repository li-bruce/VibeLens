/** Shape construction is shared by worker routing and immediate drag previews.
 * A straight relation has exactly two ports, including between different planes.
 * Curves interpolate elevation monotonically; same-plane curves stay coplanar.
 */
export function shapedPath(edge, style, bendFactor = 1, samples = 24) {
  const { a, b } = edge;
  if (style === "straight" && edge.from !== edge.to) return [a, b];
  const dx = b.x - a.x,
    dy = b.y - a.y,
    length = Math.hypot(dx, dy);
  const self = edge.from === edge.to && length < 1;
  const bend = Math.min(100, Math.max(30, length * 0.2)) * bendFactor;
  const nx = length > 0.001 ? -dy / length : 1,
    ny = length > 0.001 ? dx / length : 0;
  const c = self
    ? { x: a.x + 90, y: a.y - 110 }
    : { x: a.x + dx / 3 + nx * bend, y: a.y + dy / 3 + ny * bend };
  const d = self
    ? { x: b.x - 90, y: b.y - 110 }
    : { x: b.x - dx / 3 + nx * bend, y: b.y - dy / 3 + ny * bend };
  return Array.from({ length: samples + 1 }, (_, i) => {
    if (i === 0) return a;
    if (i === samples) return b;
    const t = i / samples,
      u = 1 - t;
    return {
      x: u * u * u * a.x + 3 * u * u * t * c.x + 3 * u * t * t * d.x + t * t * t * b.x,
      y: u * u * u * a.y + 3 * u * u * t * c.y + 3 * u * t * t * d.y + t * t * t * b.y,
      level: a.level + (b.level - a.level) * t,
    };
  });
}

/** Physical dash lengths continue across vertices; long graphs bound tessellation.
 * Skip distances along the path, never whole polyline segments.
 */
export function strokeSegments(points, dash = [], limit = 64) {
  if (!dash.length) return points.slice(1).map((p, i) => [points[i], p]);
  const length = points
    .slice(1)
    .reduce(
      (s, p, i) =>
        s + Math.hypot(p.x - points[i].x, p.y - points[i].y, (p.z || 0) - (points[i].z || 0)),
      0,
    );
  const scale = Math.max(1, length / (limit * dash.reduce((a, b) => a + b, 0)));
  let index = 0,
    remaining = dash[0] * scale;
  const result = [];
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1],
      b = points[i],
      distance = Math.hypot(b.x - a.x, b.y - a.y, (b.z || 0) - (a.z || 0));
    if (distance < 1e-8) continue;
    const at = (t) => ({
      x: a.x + (b.x - a.x) * t,
      y: a.y + (b.y - a.y) * t,
      z: (a.z || 0) + ((b.z || 0) - (a.z || 0)) * t,
    });
    let offset = 0;
    while (offset < distance - 1e-8) {
      const next = Math.min(distance, offset + remaining);
      if (index % 2 === 0) result.push([at(offset / distance), at(next / distance)]);
      remaining -= next - offset;
      offset = next;
      if (remaining < 1e-8) {
        index = (index + 1) % dash.length;
        remaining = dash[index] * scale;
      }
    }
  }
  return result;
}
