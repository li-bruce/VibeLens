/** Rounded causal routes share geometry with hit testing and animated transfers.
 * Same-track links leave the bar, travel above it, then enter the destination.
 * Cross-track links use an orthogonal channel; endpoint times never move.
 */
export function routeFlow(fx, fy, tx, ty, lane = 0, bounds = null) {
  const same = Math.abs(fy - ty) < 1;
  if (same) {
    const top = fy - 11 - (lane % 2) * 2;
    if (Math.abs(tx - fx) < 4) {
      const side = bounds && fx + 12 > bounds.right ? fx - 12 : fx + 12;
      return [
        { x: fx, y: fy - 6 },
        { x: fx, y: top },
        { x: side, y: top },
        { x: side, y: fy + 9 },
        { x: tx, y: fy + 9 },
        { x: tx, y: ty + 6 },
      ];
    }
    return [
      { x: fx, y: fy - 6 },
      { x: fx, y: top },
      { x: tx, y: top },
      { x: tx, y: ty - 6 },
    ];
  }
  let channel = Math.abs(tx - fx) > 28 ? fx + Math.sign(tx - fx) * 14 : fx - 10 - (lane % 3) * 3;
  if (bounds && channel < bounds.left) channel = Math.min(bounds.right, fx + 10 + (lane % 3) * 3);
  if (bounds) channel = Math.max(bounds.left, Math.min(bounds.right, channel));
  return [
    { x: fx, y: fy },
    { x: channel, y: fy },
    { x: channel, y: ty },
    { x: tx, y: ty },
  ];
}

export function roundedRoute(ctx, points, radius = 5) {
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length - 1; i++) {
    const before = points[i - 1],
      point = points[i],
      after = points[i + 1];
    const a = Math.hypot(point.x - before.x, point.y - before.y);
    const b = Math.hypot(after.x - point.x, after.y - point.y);
    if (!a || !b) {
      ctx.lineTo(point.x, point.y);
      continue;
    }
    const r = Math.min(radius, a / 2, b / 2);
    ctx.lineTo(point.x + ((before.x - point.x) * r) / a, point.y + ((before.y - point.y) * r) / a);
    ctx.quadraticCurveTo(
      point.x,
      point.y,
      point.x + ((after.x - point.x) * r) / b,
      point.y + ((after.y - point.y) * r) / b,
    );
  }
  ctx.lineTo(points.at(-1).x, points.at(-1).y);
}

/** Approximate arc position on the same route, with bounded work per connector. */
export function routePoint(points, fraction) {
  const lengths = points.slice(1).map((p, i) => Math.hypot(p.x - points[i].x, p.y - points[i].y));
  let distance =
    lengths.reduce((sum, value) => sum + value, 0) * Math.max(0, Math.min(1, fraction));
  for (let i = 0; i < lengths.length; i++) {
    if (distance <= lengths[i] || i === lengths.length - 1) {
      const ratio = lengths[i] ? Math.min(1, distance / lengths[i]) : 0;
      return {
        x: points[i].x + (points[i + 1].x - points[i].x) * ratio,
        y: points[i].y + (points[i + 1].y - points[i].y) * ratio,
      };
    }
    distance -= lengths[i];
  }
  return points[0];
}

export function hitRoute(points, point, tolerance = 4) {
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1],
      b = points[i];
    const dx = b.x - a.x,
      dy = b.y - a.y;
    const ratio = Math.max(
      0,
      Math.min(1, ((point.x - a.x) * dx + (point.y - a.y) * dy) / (dx * dx + dy * dy || 1)),
    );
    if (Math.hypot(point.x - a.x - ratio * dx, point.y - a.y - ratio * dy) <= tolerance)
      return true;
  }
  return false;
}

export const flowKey = (flow) => `${flow.from}:${flow.to}:${flow.at}:${flow.type}`;

/** Foreground links get first chance, without treating their entire rectangle as a hit. */
export function traceHit(hits, point) {
  return (
    hits.findLast((hit) => hit.kind === "flow" && hitRoute(hit.route, point)) ||
    hits.findLast(
      (hit) =>
        hit.kind !== "flow" &&
        point.x >= hit.x &&
        point.x <= hit.x + hit.width &&
        point.y >= hit.y &&
        point.y <= hit.y + hit.height,
    )
  );
}
