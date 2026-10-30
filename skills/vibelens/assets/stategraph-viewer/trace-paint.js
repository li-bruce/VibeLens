/** Canvas-only timeline presentation. Geometry and hit targets share one transform. */
import { t } from "./i18n.js";
import { displayName } from "./layout.js";
import { layers } from "./graph-layers.js";
import { visibleSlices } from "./trace-viewport.js";
import { visibleFlows } from "./trace-flows.js";
import { marksInWindow } from "./trace-index.js";
import { paintDuration } from "./trace-bars.js";
import { durationDetail } from "./trace-density.js";
import { routeFlow, roundedRoute, routePoint, flowKey } from "./trace-routing.js";

export const traceGeometry = { overview: 26, ruler: 24, row: 28 };
export const traceColor = (layer) =>
  "#" +
  layers
    .find((item) => item.id === layer)
    .color.toString(16)
    .padStart(6, "0");

export function timeLabel(value, ordered = true, resolution = null) {
  if (!ordered) return "#" + Math.round(value);
  if (value < 1)
    return (
      (value * 1000).toFixed(
        resolution === null
          ? value < 0.01
            ? 1
            : 0
          : Math.max(0, Math.min(3, Math.ceil(-Math.log10(resolution * 1000)))),
      ) + " µs"
    );
  if (value < 1000)
    return (
      value.toFixed(
        resolution === null
          ? value < 10
            ? 2
            : 0
          : Math.max(0, Math.min(4, Math.ceil(-Math.log10(resolution)))),
      ) + " ms"
    );
  const digits =
    resolution === null
      ? value < 10000
        ? 2
        : 1
      : Math.max(0, Math.min(6, Math.ceil(Math.log10(1000 / resolution))));
  return (value / 1000).toFixed(digits) + " s";
}

function clippedText(ctx, text, x, y, width) {
  ctx.save();
  ctx.beginPath();
  ctx.rect(x, y - 12, Math.max(0, width), 20);
  ctx.clip();
  ctx.fillText(String(text), x, y);
  ctx.restore();
}

/** Draw only visible rows and occupied pixels, retaining the selected event separately. */
export function paintTrace(canvas, state) {
  const { width, height, rows, index, window, scroll, raw, points, allowed, range } = state;
  const ctx = canvas.getContext("2d"),
    ratio = Math.min(2, globalThis.devicePixelRatio || 1);
  const left = width < 600 ? 126 : 186,
    plot = Math.max(1, width - left - 12);
  if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
  }
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
  ctx.font = '11px "Segoe UI", sans-serif';
  ctx.textBaseline = "alphabetic";
  const hits = [],
    g = traceGeometry,
    top = g.overview + g.ruler;
  const x = (time) => left + ((time - window.start) / (window.end - window.start)) * plot;
  const overviewX = (time) => left + (time / index.axis.total) * plot;
  ctx.fillStyle = "#f1f5f8";
  ctx.fillRect(left, 3, plot, g.overview - 6);
  // Density is binned once per model update, not once per pointer movement.
  const max = state.density.reduce((a, b) => Math.max(a, b), 1);
  ctx.fillStyle = "#9aafc1";
  state.density.forEach((count, i) => {
    const h = Math.max(1, (Math.log1p(count) / Math.log1p(max)) * 15);
    if (count)
      ctx.fillRect(
        left + (i / state.density.length) * plot,
        g.overview - 5 - h,
        Math.max(1, plot / state.density.length),
        h,
      );
  });
  const a = overviewX(window.start),
    b = overviewX(window.end);
  ctx.fillStyle = "#2965cc15";
  ctx.fillRect(a, 3, b - a, g.overview - 6);
  ctx.strokeStyle = "#2965cc";
  ctx.strokeRect(a, 3, Math.max(1, b - a), g.overview - 6);
  ctx.fillStyle = "#2965cc";
  for (const px of [a, b]) ctx.fillRect(px - 2, 7, 4, 10);
  ctx.fillStyle = "#667f91";
  clippedText(ctx, index.axis.ordered ? t("Elapsed time") : t("Event order"), 12, 18, left - 18);

  const firstRow = Math.max(0, Math.floor(scroll / g.row)),
    lastRow = Math.min(rows.length, Math.ceil((scroll + height - top) / g.row));
  ctx.save();
  ctx.beginPath();
  ctx.rect(left, top, plot, height - top);
  ctx.clip();
  const tickSize = (window.end - window.start) / Math.max(2, plot / 110);
  const power = 10 ** Math.floor(Math.log10(tickSize));
  const step = [1, 2, 5, 10].find((v) => v * power >= tickSize) * power;
  for (let value = Math.ceil(window.start / step) * step; value <= window.end; value += step) {
    ctx.strokeStyle = "#edf1f5";
    ctx.beginPath();
    ctx.moveTo(x(value), top);
    ctx.lineTo(x(value), height);
    ctx.stroke();
  }
  if (range) {
    ctx.fillStyle = "#2965cc14";
    ctx.fillRect(x(range[0]), top, x(range[1]) - x(range[0]), height - top);
  }
  const positions = new Map();
  let drawn = 0;
  for (let i = firstRow; i < lastRow; i++) {
    const row = rows[i],
      y = top + i * g.row - scroll,
      color = traceColor(row.layer);
    if (row.header) {
      ctx.fillStyle = color + "09";
      ctx.fillRect(left, y, plot, g.row);
    }
    const selected = row.marks.find((mark) => mark.raw === raw);
    if (selected) {
      ctx.fillStyle = "#2965cc08";
      ctx.fillRect(left, y, plot, g.row);
    }
    const visibleDurations =
      row.header && state.expanded.includes(row.layer)
        ? []
        : visibleSlices(row, window.start, window.end);
    const detail = durationDetail(visibleDurations, { x, left, right: left + plot, raw });
    for (const bin of detail.bins) {
      ctx.globalAlpha = Math.min(0.9, 0.35 + Math.log1p(bin.count) * 0.15);
      ctx.fillStyle = color;
      ctx.fillRect(bin.x - 1, y + 8, 2, 12);
      hits.push({
        kind: "density",
        count: bin.count,
        label: row.header ? t(row.label) : null,
        raw: bin.first,
        row: row.id,
        x: bin.x - 2,
        y: y + 5,
        width: 4,
        height: 20,
      });
      drawn++;
    }
    let previousSlicePixel = "";
    for (const slice of detail.detailed) {
      const sx = Math.max(left, x(slice.start)),
        ex = Math.min(left + plot, x(slice.end));
      if (ex < sx) continue;
      const pixel = `${Math.floor(sx)}:${Math.ceil(ex)}`;
      if (
        pixel === previousSlicePixel &&
        slice.raw !== raw &&
        slice.observed !== raw &&
        (slice.unfinished || slice.last !== raw)
      )
        continue;
      previousSlicePixel = pixel;
      ctx.globalAlpha = allowed.has(slice.raw) || allowed.has(slice.last) ? 0.75 : 0.23;
      paintDuration(ctx, slice, {
        sx,
        ex,
        y,
        color,
        x,
        raw,
        timeLabel,
        pulse: state.pulse || 0,
        sourceNames: state.preferences?.nameMode === "source",
      });
      hits.push({
        kind: "slice",
        slice,
        raw: slice.last,
        startRaw: slice.raw,
        row: row.id,
        x: sx,
        y: y + 5,
        width: Math.max(5, ex - sx),
        height: 20,
      });
      drawn++;
    }
    ctx.globalAlpha = 1;
    let previousPixel = -Infinity;
    for (const mark of row.header && state.expanded.includes(row.layer)
      ? []
      : marksInWindow(row, window.start, window.end)) {
      const px = x(mark.time);
      if (px < left - 5 || px > left + plot + 5) continue;
      if (mark.raw !== raw && detail.covered.has(Math.floor(px / 4))) continue;
      if (px - previousPixel < 3 && mark.raw !== raw) continue;
      previousPixel = px;
      const included = allowed.has(mark.raw);
      ctx.globalAlpha = included ? 1 : 0.24;
      ctx.strokeStyle = mark.raw === raw ? "#144eb0" : color;
      ctx.fillStyle = mark.projected ? "#ffffff" : color;
      ctx.lineWidth = mark.raw === raw ? 2 : 1;
      if (mark.projected) ctx.setLineDash([2, 1]);
      ctx.beginPath();
      ctx.moveTo(px, y + 8);
      ctx.lineTo(px + 4, y + 14);
      ctx.lineTo(px, y + 20);
      ctx.lineTo(px - 4, y + 14);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.lineWidth = 1;
      if (!positions.has(mark.raw)) positions.set(mark.raw, []);
      positions
        .get(mark.raw)
        .push({ x: px, y: y + 14, layer: row.layer, node: mark.node, projected: mark.projected });
      hits.push({
        kind: "mark",
        contextEvent: mark.contextEvent,
        raw: mark.raw,
        row: row.id,
        x: px - 5,
        y: y + 4,
        width: 10,
        height: 20,
      });
      drawn++;
    }
    ctx.globalAlpha = 1;
  }
  const positionFor = (ordinal) => {
    const matches = positions.get(ordinal) || [];
    const node = index.items[ordinal].node;
    return (
      matches.find((point) => point.node === node) ||
      matches.find((point) => !point.projected) ||
      matches[0]
    );
  };
  // Same-event projections connect layers with dashed lines, without inventing calls.
  const sourcePosition = positionFor(raw);
  for (const target of positions.get(raw) || []) {
    if (!sourcePosition || target.layer === sourcePosition.layer) continue;
    ctx.strokeStyle = target.projected ? "#8172a3" : "#8c57ad";
    ctx.setLineDash([3, 3]);
    ctx.beginPath();
    ctx.moveTo(sourcePosition.x, sourcePosition.y);
    ctx.lineTo(target.x, target.y);
    ctx.stroke();
  }
  // Cull by time/row and occupied pixels. Full causal chains remain visible while
  // the selected event receives stronger emphasis; dense views aggregate pixels.
  const pixels = new Set();
  let flowCount = 0;
  for (const flow of visibleFlows(index, rows, window)) {
    const fy = top + flow.fromRow * g.row - scroll + 14;
    const ty = top + flow.toRow * g.row - scroll + 14;
    if (Math.max(fy, ty) < top || Math.min(fy, ty) > height) continue;
    const fx = x(flow.fromTime),
      tx = x(flow.toTime);
    const selected =
      flow.at === raw ||
      (!["call", "return", "transition"].includes(flow.type) &&
        (flow.to === raw || flow.from === raw));
    const density = index.items.length > 3000;
    const bucket = density ? 8 : 3;
    const key = `${Math.round(fx / bucket)}:${Math.round(tx / bucket)}:${flow.fromRow}:${flow.toRow}:${flow.type}`;
    if (!selected && (pixels.has(key) || flowCount >= (density ? 900 : 1800))) continue;
    pixels.add(key);
    const keyId = flowKey(flow);
    const hovered = state.hover?.key === keyId;
    const emphasized = selected || hovered;
    ctx.globalAlpha = emphasized ? 1 : state.hover ? 0.22 : 0.65;
    ctx.lineWidth = emphasized ? 1.8 : 1.1;
    const color = flow.outlivesParent
      ? "#b87842"
      : flow.type === "transition"
        ? "#8c57ad"
        : traceColor(rows[flow.toRow].layer);
    ctx.strokeStyle = color;
    ctx.setLineDash(
      ["call", "return", "data", "control", "transition"].includes(flow.type) ? [] : [3, 3],
    );
    const route = routeFlow(fx, fy, tx, ty, flowCount, { left: left + 4, right: left + plot - 4 });
    roundedRoute(ctx, route);
    ctx.stroke();
    ctx.setLineDash([]);
    for (const [point, fill] of [
      [route[0], color],
      [route.at(-1), "#ffffff"],
    ]) {
      ctx.fillStyle = fill;
      ctx.beginPath();
      ctx.arc(point.x, point.y, emphasized ? 3 : 2.2, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
    const tail = route.at(-2),
      tip = route.at(-1);
    const angle = Math.atan2(tip.y - tail.y, tip.x - tail.x);
    ctx.beginPath();
    ctx.moveTo(tip.x - 5 * Math.cos(angle - 0.5), tip.y - 5 * Math.sin(angle - 0.5));
    ctx.lineTo(tip.x, tip.y);
    ctx.lineTo(tip.x - 5 * Math.cos(angle + 0.5), tip.y - 5 * Math.sin(angle + 0.5));
    ctx.stroke();
    if (selected && state.pulse) {
      const point = routePoint(route, state.pulse);
      ctx.fillStyle = color;
      ctx.shadowColor = color;
      ctx.shadowBlur = 5;
      ctx.beginPath();
      ctx.arc(point.x, point.y, 3, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
    }
    hits.push({ kind: "flow", key: keyId, flow, route, raw: flow.at, row: rows[flow.toRow].id });
    flowCount++;
  }
  ctx.globalAlpha = 1;
  ctx.lineWidth = 1;
  ctx.setLineDash([]);
  const cursor = x(state.inspection === false ? index.axis.total : (index.axis.times[raw] ?? 0));
  ctx.strokeStyle = "#2965cc";
  ctx.beginPath();
  ctx.moveTo(cursor, top);
  ctx.lineTo(cursor, height);
  ctx.stroke();
  if (cursor >= left && cursor <= left + plot) {
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(cursor, height - 7, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }
  ctx.restore();

  for (let i = firstRow; i < lastRow; i++) {
    const row = rows[i],
      y = top + i * g.row - scroll;
    ctx.fillStyle = row.header ? "#f2f6f9" : "#ffffff";
    ctx.fillRect(0, y, left, g.row);
    ctx.fillStyle = traceColor(row.layer);
    ctx.fillRect(0, y + 5, 3, g.row - 10);
    ctx.font = `${row.header ? "600" : "400"} 11px "Segoe UI", sans-serif`;
    ctx.fillStyle = "#354d5e";
    const title = row.header
      ? (state.expanded.includes(row.layer) ? "▾ " : "▸ ") + t(row.label)
      : state.preferences
        ? displayName(state.all?.get(row.id) || row.node, state.preferences)
        : row.node.label || row.id;
    clippedText(ctx, title, row.header ? 12 : 22, y + 18, left - (row.header ? 42 : 28));
    if (row.header) {
      ctx.fillStyle = "#71808e";
      ctx.fillText(String(row.count), left - 26, y + 18);
    }
    ctx.strokeStyle = "#edf1f5";
    ctx.beginPath();
    ctx.moveTo(0, y + g.row);
    ctx.lineTo(width, y + g.row);
    ctx.stroke();
    hits.push({
      kind: row.header ? "layer" : "node",
      row: row.id,
      x: 0,
      y,
      width: left,
      height: g.row,
    });
  }
  ctx.fillStyle = "#f8fafc";
  ctx.fillRect(0, g.overview, width, g.ruler);
  ctx.font = "10px Consolas, monospace";
  ctx.fillStyle = "#627b8e";
  for (let value = Math.ceil(window.start / step) * step; value <= window.end; value += step)
    clippedText(ctx, timeLabel(value, index.axis.ordered, step), x(value) + 4, top - 7, 94);
  if (cursor >= left && cursor <= width) {
    ctx.fillStyle = "#2965cc";
    ctx.beginPath();
    ctx.moveTo(cursor - 4, top - 6);
    ctx.lineTo(cursor + 4, top - 6);
    ctx.lineTo(cursor, top);
    ctx.fill();
  }
  const trackHeight = height - top,
    contentHeight = rows.length * g.row;
  if (contentHeight > trackHeight) {
    const thumb = Math.max(18, trackHeight ** 2 / contentHeight);
    ctx.fillStyle = "#bdcbd6";
    ctx.fillRect(
      width - 5,
      top + (scroll / (contentHeight - trackHeight)) * (trackHeight - thumb),
      3,
      thumb,
    );
  }
  if (!rows.length) {
    ctx.fillStyle = "#71808e";
    ctx.fillText(t("No recorded events in this view"), left + 20, top + 30);
  }
  return { hits, left, plot, top, drawn, flows: flowCount, points: points.length };
}
