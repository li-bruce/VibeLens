/** Pure bounded time-window arithmetic; coordinates are relative to the plot. */
export function boundWindow(start, end, total) {
  total = Math.max(1, total);
  const width = Math.max(total / 100000, Math.min(total, end - start));
  const left = Math.max(0, Math.min(total - width, start));
  return { start: left, end: left + width };
}
export function zoomWindow(window, factor, anchor, total) {
  const ratio = Math.max(0, Math.min(1, anchor));
  const width = (window.end - window.start) / factor;
  const pivot = window.start + (window.end - window.start) * ratio;
  return boundWindow(pivot - width * ratio, pivot + width * (1 - ratio), total);
}
export function panWindow(window, delta, total) {
  return boundWindow(window.start + delta, window.end + delta, total);
}
export function lowerBound(items, value, key = (item) => item) {
  let lo = 0,
    hi = items.length;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (key(items[mid]) < value) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}
/** Nearest allowed event, with a stable earlier-event tie break. */
export function nearestEvent(points, value) {
  if (!points.length) return null;
  const i = lowerBound(points, value, (point) => point.time);
  const a = points[Math.max(0, i - 1)],
    b = points[Math.min(points.length - 1, i)];
  return value - a.time <= b.time - value ? a : b;
}
export function visibleSlices(row, start, end) {
  const stop = lowerBound(row.slices, end + Number.EPSILON, (item) => item.start);
  let first = lowerBound(row.maxEnds, start);
  if (first > stop) first = stop;
  return row.slices.slice(first, stop).filter((item) => item.end >= start);
}
