/** Lifetime styling is separate from indexing and never classifies business success.
 * Color identifies the layer; segment text comes from registered or generic facts.
 */
import { t } from "./i18n.js";
import { lifecycleCaption } from "./node-lifecycle.js";

function pill(ctx, x, y, width, height, radius = 4) {
  ctx.beginPath();
  ctx.roundRect(x, y, Math.max(2, width), height, radius);
}

export function paintDuration(
  ctx,
  slice,
  { sx, ex, y, color, x, raw, timeLabel, pulse = 0, sourceNames = false, caption = "" },
) {
  const width = Math.max(7, ex - sx),
    top = y + 6;
  const active = !slice.ambiguous && slice.raw <= raw && (slice.unfinished || raw < slice.last);
  const exception = slice.termination === "exception";
  ctx.fillStyle = color + "18";
  pill(ctx, sx, top, width, 16);
  ctx.fill();
  ctx.save();
  pill(ctx, sx, top, width, 16);
  ctx.clip();
  const stages = slice.stages?.length ? slice.stages : [{ start: slice.start, end: slice.end }];
  for (const stage of stages) {
    const start = Math.max(sx, x(stage.start)),
      end = Math.min(ex, x(stage.end));
    if (end < start) continue;
    const waiting = stage.phase === "waiting";
    ctx.fillStyle = color + (waiting ? "18" : "b8");
    ctx.fillRect(start, top, Math.max(7, end - start), 16);
    if (waiting) {
      ctx.strokeStyle = color + "65";
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let px = start - 16; px < end; px += 7) {
        ctx.moveTo(px, top + 16);
        ctx.lineTo(px + 16, top);
      }
      ctx.stroke();
    }
    if ((stage.label || caption) && end - start > 48) {
      ctx.fillStyle = waiting ? "#41576a" : "#ffffff";
      ctx.save();
      ctx.beginPath();
      ctx.rect(
        start + 4,
        top,
        Math.max(0, end - start - (slice.duration !== null && end >= ex - 1 ? 75 : 8)),
        16,
      );
      ctx.clip();
      const meaning = stage.label ? t(lifecycleCaption(stage, sourceNames)) : "";
      ctx.fillText([caption, meaning].filter(Boolean).join(" · "), start + 6, y + 18);
      ctx.restore();
    }
  }
  ctx.restore();
  ctx.strokeStyle = exception ? "#b85c4a" : color + (active ? "dd" : "75");
  ctx.lineWidth = active ? 1.5 : 1;
  ctx.setLineDash(slice.unfinished || slice.ambiguous ? [3, 3] : []);
  pill(ctx, sx, top, width, 16);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.lineWidth = 1;
  if (active && pulse) {
    ctx.fillStyle = color;
    ctx.globalAlpha *= 0.5 + 0.35 * Math.sin(pulse * Math.PI * 2);
    ctx.beginPath();
    ctx.arc(ex - 2, y + 14, 2.8, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
  }
  if (exception) {
    ctx.fillStyle = "#b85c4a";
    ctx.fillRect(ex - 3, top + 2, 3, 12);
  }
  if (width > 68 && slice.duration !== null) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(sx + 4, top, width - 8, 16);
    ctx.clip();
    ctx.fillStyle = "#ffffff";
    const text = (slice.clippedStart ? "≥ " : "") + timeLabel(slice.duration);
    const textWidth = ctx.measureText(text).width;
    ctx.fillStyle = color;
    pill(ctx, ex - textWidth - 9, top + 1, textWidth + 8, 14, 3);
    ctx.fill();
    ctx.fillStyle = "#ffffff";
    ctx.fillText(text, ex - textWidth - 5, y + 18);
    ctx.restore();
  }
}
