/** Shared 2D geometry for flat scenes and individual X/Z planes of a spatial scene. */
import { RBush, line, curveBundle } from "./routing-tools.vendor.js";

export const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
export const samePoint = (a, b) => distance(a, b) < 1e-7;
export function cleanPoints(points) {
  const result = [];
  for (const p of points) {
    if (result.length && samePoint(p, result.at(-1))) continue;
    while (result.length > 1) {
      const a = result.at(-2),
        b = result.at(-1),
        cross = (b.x - a.x) * (p.y - b.y) - (b.y - a.y) * (p.x - b.x);
      if (Math.abs(cross) > 0.001 || (b.x - a.x) * (p.x - b.x) + (b.y - a.y) * (p.y - b.y) < 0)
        break;
      result.pop();
    }
    result.push(p);
  }
  return result;
}
export function segmentDistance(point, a, b) {
  const dx = b.x - a.x,
    dy = b.y - a.y;
  const t = Math.max(
    0,
    Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / (dx * dx + dy * dy || 1)),
  );
  return Math.hypot(point.x - a.x - t * dx, point.y - a.y - t * dy);
}
export const bounds = (a, b, margin = 0) => ({
  minX: Math.min(a.x, b.x) - margin,
  minY: Math.min(a.y, b.y) - margin,
  maxX: Math.max(a.x, b.x) + margin,
  maxY: Math.max(a.y, b.y) + margin,
});

/** R-tree queries restrict exact circle tests to obstacles near each segment. */
export class ObstacleIndex {
  constructor(obstacles = []) {
    this.items = obstacles.map((o) => ({
      ...o,
      minX: o.x - o.r,
      minY: o.y - o.r,
      maxX: o.x + o.r,
      maxY: o.y + o.r,
    }));
    this.tree = new RBush().load(this.items);
  }
  excluded(o, edge) {
    if (o.kind === "glyph") return o.id === edge.from || o.id === edge.to;
    // A region is a scope, rather than a solid object. Edges may leave a scope
    // containing an endpoint, including deliberately overlapping scope circles.
    return edge.allowed?.includes(o.id) || distance(o, edge.a) <= o.r || distance(o, edge.b) <= o.r;
  }
  collisions(points, edge, margin = 0) {
    const hits = new Map();
    for (let i = 1; i < points.length; i++) {
      const a = points[i - 1],
        b = points[i];
      for (const o of this.tree.search(bounds(a, b, margin)))
        if (!this.excluded(o, edge) && segmentDistance(o, a, b) < o.r + margin - 1e-5)
          hits.set(o.key, o);
    }
    return [...hits.values()];
  }
  clear(points, edge) {
    // Most candidate paths fail at their first obstacle. Do not collect every
    // collision when the caller only needs a yes/no certificate.
    for (let i = 1; i < points.length; i++) {
      const a = points[i - 1],
        b = points[i];
      for (const o of this.tree.search(bounds(a, b)))
        if (!this.excluded(o, edge) && segmentDistance(o, a, b) < o.r - 1e-5) return false;
    }
    return true;
  }
  free(point, edge) {
    return !this.tree
      .search(bounds(point, point))
      .some((o) => !this.excluded(o, edge) && distance(o, point) < o.r - 1e-5);
  }
}

/** Cheap certified candidates handle ordinary interactions before invoking Wasm. */
export function simpleRoute(a, b, index, edge, orthogonal = true) {
  if (!orthogonal && index.clear([a, b], edge)) return [a, b];
  const midX = (a.x + b.x) / 2,
    midY = (a.y + b.y) / 2;
  const candidates = [
    [a, { x: b.x, y: a.y }, b],
    [a, { x: a.x, y: b.y }, b],
    [a, { x: midX, y: a.y }, { x: midX, y: b.y }, b],
    [a, { x: a.x, y: midY }, { x: b.x, y: midY }, b],
  ];
  for (const points of candidates) if (index.clear(points, edge)) return cleanPoints(points);
  return null;
}

/** Find a common portal outside obstacles; a failure remains an explicit gap. */
export function freePortal(preferred, index, edge) {
  if (index.free(preferred, edge)) return preferred;
  for (let radius = 32; radius <= 4096; radius *= 2)
    for (let i = 0; i < 16; i++) {
      const angle = (i * Math.PI) / 8;
      const p = {
        x: preferred.x + Math.cos(angle) * radius,
        y: preferred.y + Math.sin(angle) * radius,
      };
      if (index.free(p, edge)) return p;
    }
  return null;
}

/** Sample D3's bundle spline near corners, then certify the actual drawn segments.
 * Extra collinear points bound corner rounding; failed smoothing keeps the safe
 * polyline rather than silently clipping through an obstacle.
 */
export function smoothRoute(points, index, edge) {
  if (points.length < 3 || points.length > 12) return points;
  const knots = [points[0]];
  for (let i = 1; i < points.length - 1; i++) {
    const a = points[i - 1],
      b = points[i],
      c = points[i + 1];
    const near = (p) => {
      const t = Math.min(0.45, 5 / (distance(p, b) || 1));
      return { x: b.x + (p.x - b.x) * t, y: b.y + (p.y - b.y) * t };
    };
    knots.push(near(a), b, near(c));
  }
  knots.push(points.at(-1));
  const output = [],
    context = {
      moveTo(x, y) {
        output.push({ x, y });
      },
      lineTo(x, y) {
        output.push({ x, y });
      },
      bezierCurveTo(x1, y1, x2, y2, x, y) {
        const a = output.at(-1);
        for (let i = 1; i <= 2; i++) {
          const t = i / 2,
            u = 1 - t;
          output.push({
            x: u ** 3 * a.x + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t ** 3 * x,
            y: u ** 3 * a.y + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t ** 3 * y,
          });
        }
      },
    };
  line()
    .x((p) => p.x)
    .y((p) => p.y)
    .curve(curveBundle.beta(1))
    .context(context)(knots);
  return index.clear(output, edge) ? cleanPoints(output) : points;
}
