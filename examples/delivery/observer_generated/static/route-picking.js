import { segmentDistance } from "./routing-geometry.js";
/** Return every original edge under a shared trunk, without a synthetic graph edge. */
export function pickRoutes(edges, pathFor, point, tolerance) {
  return edges.filter((edge) => {
    const points = pathFor(edge) || [];
    return points.slice(1).some((p, i) => segmentDistance(point, points[i], p) <= tolerance);
  });
}
