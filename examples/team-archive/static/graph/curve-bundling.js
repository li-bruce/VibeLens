/** D3 bundle geometry is a display aid: every original edge keeps its two ports.
 * Only compatible, similarly directed relations share intermediate control points.
 * The routing worker checks the sampled result against current obstacles.
 */
import { line, curveBundle } from "./routing-tools.vendor.js";

export function curveBundles(scene, hierarchyKey) {
  const groups = new Map();
  if (scene.style !== "curve" || !scene.bundling) return groups;
  for (const edge of scene.edges) {
    if (edge.from === edge.to) continue;
    const angle = Math.round(Math.atan2(edge.b.y - edge.a.y, edge.b.x - edge.a.x) / (Math.PI / 4));
    const key = `${hierarchyKey(edge)}|${edge.fromLayer}>${edge.toLayer}|${angle}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(edge);
  }
  return new Map(
    [...groups]
      .filter(([, group]) => group.length > 1)
      .map(([key, members]) => {
        // Compute a shared spine once; rescanning every member per edge is quadratic.
        const mean = (side) => ({
          x: members.reduce((sum, edge) => sum + edge[side].x, 0) / members.length,
          y: members.reduce((sum, edge) => sum + edge[side].y, 0) / members.length,
        });
        return [key, { members, a: mean("a"), b: mean("b") }];
      }),
  );
}

/** Sample the mature D3 spline once in the worker, then share it with both renderers. */
export function bundledCurve(edge, group, samples = 6) {
  const { a, b } = group,
    output = [];
  const blend = (t) => ({ x: a.x * (1 - t) + b.x * t, y: a.y * (1 - t) + b.y * t });
  const context = {
    moveTo(x, y) {
      output.push({ x, y });
    },
    lineTo(x, y) {
      output.push({ x, y });
    },
    bezierCurveTo(x1, y1, x2, y2, x, y) {
      const start = output.at(-1);
      for (let i = 1; i <= samples; i++) {
        const t = i / samples,
          u = 1 - t;
        output.push({
          x: u ** 3 * start.x + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t ** 3 * x,
          y: u ** 3 * start.y + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t ** 3 * y,
        });
      }
    },
  };
  line()
    .x((point) => point.x)
    .y((point) => point.y)
    .curve(curveBundle.beta(0.95))
    .context(context)([edge.a, blend(0.3), blend(0.5), blend(0.7), edge.b]);
  const lengths = [0];
  for (let i = 1; i < output.length; i++)
    lengths.push(
      lengths[i - 1] + Math.hypot(output[i].x - output[i - 1].x, output[i].y - output[i - 1].y),
    );
  const total = lengths.at(-1) || 1;
  return output.map((point, i) =>
    i === 0
      ? edge.a
      : i === output.length - 1
        ? edge.b
        : {
            ...point,
            level: edge.a.level + ((edge.b.level - edge.a.level) * lengths[i]) / total,
          },
  );
}
