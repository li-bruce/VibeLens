/** Canvas-only timeline presentation. Geometry and hit targets share one transform. */
import { t } from "./i18n.js";
import { displayName } from "./layout.js";
import { layers } from "./graph-layers.js";
import { visibleSlices } from "./trace-viewport.js";
import { marksInWindow } from "./trace-index.js";

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
  const positions = new Map(),
    rowPositions = new Map();
  let drawn = 0;
  for (let i = firstRow; i < lastRow; i++) {
    const row = rows[i],
      y = top + i * g.row - scroll,
      color = traceColor(row.layer);
    rowPositions.set(row.id, y + 14);
    if (row.header) {
      ctx.fillStyle = color + "09";
      ctx.fillRect(left, y, plot, g.row);
    }
    const selected = row.marks.find((mark) => mark.raw === raw);
    if (selected) {
      ctx.fillStyle = "#2965cc08";
      ctx.fillRect(left, y, plot, g.row);
    }
    let previousSlicePixel = "";
    for (const slice of visibleSlices(row, window.start, window.end)) {
      const sx = Math.max(left, x(slice.start)),
        ex = Math.min(left + plot, x(slice.end));
      if (ex < sx) continue;
      const pixel = `${Math.floor(sx)}:${Math.ceil(ex)}`;
      if (pixel === previousSlicePixel && !(slice.raw <= raw && raw <= slice.last)) continue;
      previousSlicePixel = pixel;
      ctx.globalAlpha = allowed.has(slice.raw) || allowed.has(slice.last) ? 0.75 : 0.23;
      ctx.fillStyle = slice.unfinished || slice.ambiguous ? color + "12" : color;
      ctx.fillRect(sx, y + 8, Math.max(2, ex - sx), 12);
      if (slice.unfinished || slice.ambiguous) {
        ctx.strokeStyle = color;
        ctx.setLineDash([2, 2]);
        ctx.strokeRect(sx, y + 8, Math.max(2, ex - sx), 12);
        ctx.setLineDash([]);
        ctx.fillStyle = color;
        ctx.fillRect(sx, y + 8, 2, 12);
      }
      if (ex - sx > 65 && slice.duration !== null) {
        ctx.fillStyle = "#ffffff";
        clippedText(ctx, timeLabel(slice.duration), sx + 5, y + 18, ex - sx - 10);
      }
      hits.push({
        kind: "slice",
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
    for (const mark of marksInWindow(row, window.start, window.end)) {
      const px = x(mark.time);
      if (px < left - 5 || px > left + plot + 5) continue;
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
  // Only selected-event flows are drawn; thousands of simultaneous links never cover the trace.
  for (const flow of index.links) {
    if (flow.to !== raw && flow.from !== raw) continue;
    if (Math.max(flow.to, flow.from) > raw) continue;
    const from = positionFor(flow.from),
      parentRow = index.rows.get(index.items[flow.to].node),
      parentY = rowPositions.get(parentRow?.id) ?? rowPositions.get("layer:" + parentRow?.layer),
      to =
        flow.type === "return" && parentY !== undefined
          ? { x: x(index.axis.times[flow.from]), y: parentY }
          : positionFor(flow.to);
    if (!from || !to || from.y === to.y) continue;
    ctx.strokeStyle = flow.type === "data" ? "#208b73" : "#477b9c";
    ctx.setLineDash(["call", "return", "data"].includes(flow.type) ? [] : [3, 3]);
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.bezierCurveTo(from.x + 18, from.y, to.x - 18, to.y, to.x, to.y);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(to.x - 5, to.y - 3);
    ctx.lineTo(to.x, to.y);
    ctx.lineTo(to.x - 5, to.y + 3);
    ctx.stroke();
  }
  ctx.setLineDash([]);
  const cursor = x(index.axis.times[raw] ?? 0);
  ctx.strokeStyle = "#2965cc";
  ctx.beginPath();
  ctx.moveTo(cursor, top);
  ctx.lineTo(cursor, height);
  ctx.stroke();
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
  return { hits, left, plot, top, drawn, points: points.length };
}
