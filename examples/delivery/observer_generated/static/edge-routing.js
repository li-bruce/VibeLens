/** Presentation paths only: routing never changes graph endpoints or relation kinds. */
export const edgeRoutes = ["curve", "straight", "orthogonal", "bus"];
export const cleanRoute = (value) => (edgeRoutes.includes(value) ? value : "curve");

/** Arc-length interpolation keeps particles at constant speed on bent paths. */
export function polylineAt(points, progress) {
  const axes = "z" in points[0] ? ["x", "y", "z"] : ["x", "y"];
  const lengths = points
    .slice(1)
    .map((p, i) => Math.hypot(...axes.map((key) => p[key] - points[i][key])));
  let remaining = Math.max(0, Math.min(1, progress)) * lengths.reduce((a, b) => a + b, 0);
  for (let i = 0; i < lengths.length; i++) {
    if (remaining <= lengths[i] || i === lengths.length - 1) {
      const ratio = lengths[i] ? Math.min(1, remaining / lengths[i]) : 0;
      return Object.fromEntries(
        axes.map((key) => [key, points[i][key] + (points[i + 1][key] - points[i][key]) * ratio]),
      );
    }
    remaining -= lengths[i];
  }
  return { ...points[0] };
}

/** Bus trunks group a shared source AND relation kind, without inventing junction facts. */
export function busTrunks(edges, point) {
  const groups = new Map();
  for (const edge of edges) {
    const key = `${edge.from}:${edge.type}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(edge);
  }
  const result = new Map();
  for (const group of groups.values()) {
    const source = point(group[0].from),
      targets = group.map((e) => point(e.to)).filter(Boolean);
    if (!source || targets.length < 2) continue;
    const x = (source.x + targets.reduce((n, p) => n + p.x, 0) / targets.length) / 2;
    for (const edge of group) result.set(edge.id, x);
  }
  return result;
}

/** Orthogonal routes retain exact layer elevation and a vertical cross-layer segment. */
export function routePoints(start, end, style, trunk) {
  if (style === "straight") return [start, end];
  const x = Number.isFinite(trunk) ? trunk : (start.x + end.x) / 2;
  const points =
    "z" in start
      ? [
          start,
          { x, y: start.y, z: start.z },
          { x, y: start.y, z: end.z },
          { x, y: end.y, z: end.z },
          end,
        ]
      : [start, { x, y: start.y }, { x, y: end.y }, end];
  return points.filter((p, i) => !i || Object.keys(p).some((key) => p[key] !== points[i - 1][key]));
}

/** An external group edge terminates on its owner's ring. Internal edges keep the self node. */
export function regionPort(id, otherId, towards, positions, volumes) {
  const volume = volumes.find((v) => v.id === id && !v.projection);
  if (!volume || volume.members.includes(otherId)) return positions[id];
  const dx = towards.x - volume.center.x,
    dz = towards.z - volume.center.z;
  const length = Math.hypot(dx, dz);
  // A directly stacked endpoint has no radial direction; choose a stable rim point.
  return {
    x: volume.center.x + (length ? dx / length : 1) * volume.radius,
    y: volume.center.y,
    z: volume.center.z + (length ? dz / length : 0) * volume.radius,
  };
}
