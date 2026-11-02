/** Fit display text to measured node bounds without changing the underlying name. */
export function fitCaption(value, { maxWidth, maxLines = 2, measure }) {
  const characters = Array.from(String(value).replace(/\s+/gu, " ").trim());
  if (!characters.length || maxWidth <= 0 || maxLines < 1) return "";
  const lines = [];
  let remaining = characters;
  while (remaining.length && lines.length < maxLines) {
    const all = remaining.join("");
    if (measure(all) <= maxWidth) {
      lines.push(all);
      break;
    }
    const last = lines.length + 1 === maxLines;
    if (last && measure("…") > maxWidth) break;
    // Binary search bounds measurement work for long source identifiers.
    let low = 0,
      high = remaining.length;
    while (low < high) {
      const middle = Math.ceil((low + high) / 2);
      if (measure(remaining.slice(0, middle).join("") + (last ? "…" : "")) <= maxWidth)
        low = middle;
      else high = middle - 1;
    }
    if (last) {
      lines.push(remaining.slice(0, low).join("").trimEnd() + "…");
      break;
    }
    if (!low) break;
    // Prefer whole words, but allow CJK and source symbols to wrap anywhere.
    const prefix = remaining.slice(0, low).join(""),
      boundary = prefix.lastIndexOf(" "),
      count = boundary > prefix.length / 2 ? Array.from(prefix.slice(0, boundary)).length : low;
    lines.push(remaining.slice(0, count).join("").trimEnd());
    remaining = remaining.slice(count);
    while (remaining[0] === " ") remaining.shift();
  }
  return lines.join("\n");
}
