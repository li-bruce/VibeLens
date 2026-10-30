/** Screen-space detail selection. Density marks are counts, never merged lifetimes.
 * The immutable trace index keeps every interval; zoom or selection reveals each one.
 */
export function durationDetail(slices, { x, left, right, raw, binSize = 4 }) {
  const dense = slices.length > (right - left) / 5;
  if (!dense) return { detailed: slices, bins: [], covered: new Set() };
  const detailed = [],
    bins = new Map();
  for (const slice of slices) {
    const start = x(slice.start),
      end = x(slice.end);
    const selected =
      slice.raw === raw || slice.observed === raw || (!slice.unfinished && slice.last === raw);
    if (end - start >= 6 || selected) {
      detailed.push(slice);
      continue;
    }
    const column = Math.floor((Math.max(left, start) + Math.min(right, end)) / 2 / binSize);
    const bin = bins.get(column);
    if (bin) {
      bin.count++;
      bin.first = Math.min(bin.first, slice.raw);
      bin.last = Math.max(bin.last, slice.last);
    } else
      bins.set(column, {
        column,
        x: column * binSize + binSize / 2,
        count: 1,
        first: slice.raw,
        last: slice.last,
        representative: slice,
      });
  }
  return { detailed, bins: [...bins.values()], covered: new Set(bins.keys()) };
}
