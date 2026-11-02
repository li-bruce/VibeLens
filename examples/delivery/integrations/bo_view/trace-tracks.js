/** Parallel intervals share one semantic layer row, with nonoverlapping subtracks. */
export const trackPitch = 22;
export function packTracks(slices) {
  const ends = [],
    preferred = new Map();
  const packed = slices.map((slice) => {
    const key = slice.scope || slice.node;
    let track = preferred.get(key);
    if (track === undefined || ends[track] > slice.start)
      track = ends.findIndex((end) => end <= slice.start);
    if (track < 0) track = ends.length;
    ends[track] = Math.max(slice.start, slice.end);
    preferred.set(key, track);
    return { ...slice, track };
  });
  const boundaries = new Map(),
    byNode = new Map();
  for (const slice of packed) {
    if (!byNode.has(slice.node)) byNode.set(slice.node, []);
    byNode.get(slice.node).push(slice);
    for (const raw of [slice.raw, slice.last])
      boundaries.set(JSON.stringify([slice.node, raw]), slice.track);
  }
  return { slices: packed, trackCount: Math.max(1, ends.length), tracks: { boundaries, byNode } };
}
export function rowMetrics(rows) {
  const tops = [],
    heights = [];
  let total = 0;
  for (const row of rows) {
    tops.push(total);
    const height = 28 + (Math.max(1, row.trackCount || 1) - 1) * trackPitch;
    heights.push(height);
    total += height;
  }
  return { tops, heights, total };
}
export function trackOf(row, node, raw) {
  if (!row.trackCount || row.trackCount === 1) return 0;
  const exact = row.tracks?.boundaries.get(JSON.stringify([node, raw]));
  if (exact !== undefined) return exact;
  const candidates = row.tracks?.byNode.get(node) || [];
  const match = candidates.find((slice) => slice.raw <= raw && slice.last >= raw);
  return match?.track || 0;
}
