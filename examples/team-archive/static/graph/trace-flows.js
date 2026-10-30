/** Causal geometry is independent of Canvas and uses the graph's exact event ordinals. */
import { visibleSlices } from "./trace-viewport.js";

export function indexFlows(links, times) {
  const slices = links
    .map((link) => {
      const at = link.at ?? link.to;
      const fromTime = ["call", "transition"].includes(link.type) ? times[at] : times[link.from];
      const toTime = link.type === "return" ? times[at] : times[link.to];
      return { ...link, at, start: Math.min(fromTime, toTime), end: Math.max(fromTime, toTime) };
    })
    .sort((a, b) => a.start - b.start || a.at - b.at);
  let max = -Infinity;
  return { slices, maxEnds: slices.map((flow) => (max = Math.max(max, flow.end))) };
}

/** Removing a lower layer removes its links; it never invents a shortcut call. */
export function visibleFlows(index, rows, window) {
  const positions = new Map();
  rows.forEach((row, i) => {
    if (row.header) return;
    positions.set(row.id, i);
  });
  rows.forEach((row, i) => {
    if (!row.header) return;
    for (const id of row.members) if (!positions.has(id)) positions.set(id, i);
  });
  const position = (raw, node) => {
    const owner = node || index.items[raw]?.node;
    if (positions.has(owner)) return positions.get(owner);
    if (node) return null;
    // A display reference remains the same observed identity; semantic equivalence
    // is deliberately absent here and cannot become a runtime call.
    for (const id of index.eventRows.get(raw) || [])
      if (positions.has(id) && index.rows.get(id)?.node.referenceOf === owner)
        return positions.get(id);
    return null;
  };
  return visibleSlices(index.flows, window.start, window.end).flatMap((flow) => {
    const fromRow = position(flow.from, flow.fromNode),
      toRow = position(flow.to, flow.toNode);
    if (fromRow === null || toRow === null) return [];
    const at = index.axis.times[flow.at];
    return [
      {
        ...flow,
        fromRow,
        toRow,
        fromTime: ["call", "transition"].includes(flow.type) ? at : index.axis.times[flow.from],
        toTime: flow.type === "return" ? at : index.axis.times[flow.to],
      },
    ];
  });
}
