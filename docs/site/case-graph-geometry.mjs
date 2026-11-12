/** Small deterministic routes shared by confirmation, SVG and WebGL views. */
export function routeEdges(edges) {
  const counts = new Map(),
    visited = new Map();
  const key = (edge) => JSON.stringify([edge.from, edge.to]);
  for (const edge of edges) counts.set(key(edge), (counts.get(key(edge)) || 0) + 1);
  return edges.map((edge) => {
    const id = key(edge),
      lane = visited.get(id) || 0;
    visited.set(id, lane + 1);
    return { ...edge, lane, parallel: counts.get(id) };
  });
}

/** Distinct transitions between the same states keep separate, readable arcs. */
export function edgePoints(edge, nodes) {
  const a = nodes.get(edge.from),
    b = nodes.get(edge.to),
    lane = edge.lane || 0;
  if (a.id === b.id) {
    const width = 55 + lane * 25,
      height = 70 + lane * 38;
    return [
      [a.x - 12, a.y - 14],
      [a.x - width, a.y - height],
      [a.x + width, a.y - height],
      [a.x + 12, a.y - 14],
    ];
  }
  if (b.x < a.x)
    return [
      [a.x, a.y + 18],
      [a.x, a.y + 100 + lane * 38],
      [b.x, b.y + 100 + lane * 38],
      [b.x, b.y + 18],
    ];
  if (Math.abs(a.x - b.x) < 30)
    return [
      [a.x + 10, a.y + 18],
      [a.x + 42, (a.y + b.y) / 2],
      [b.x + 42, (a.y + b.y) / 2],
      [b.x + 10, b.y - 18],
    ];
  const bend = (lane - ((edge.parallel || 1) - 1) / 2) * 60;
  return [
    [a.x + 18, a.y],
    [(a.x + b.x) / 2, a.y + bend],
    [(a.x + b.x) / 2, b.y + bend],
    [b.x - 18, b.y],
  ];
}

export const curvePath = (points) => `M${points[0]}C${points[1]} ${points[2]} ${points[3]}`;
export const midpoint = (points) =>
  [0, 1].map(
    (axis) => (points[0][axis] + 3 * points[1][axis] + 3 * points[2][axis] + points[3][axis]) / 8,
  );

export const labelOf = (item, language) =>
  item.labels?.[language === "zh-CN" ? 1 : 0] || item.label || item.id;
