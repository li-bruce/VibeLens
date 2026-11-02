/** Causal geometry is independent of Canvas and uses the graph's exact event ordinals. */
import { visibleSlices } from "./trace-viewport.js";

export function indexFlows(links, times) {
  const slices = links
    .map((link) => {
      const at = link.at ?? link.to;
      const fromTime = ["call", "activation", "transition", "observation"].includes(link.type)
        ? times[at]
        : times[link.from];
      const toTime = ["return", "completion"].includes(link.type) ? times[at] : times[link.to];
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
    for (const id of row.members || [row.id]) positions.set(`${row.group}:${id}`, i);
  });
  const executionOwner = (raw, original) =>
    original ? index.executions.byId.get(original) : index.executions.byEvent.get(raw);
  const position = (raw, node, original, otherOwner) => {
    const chain =
      executionOwner(raw, original) ||
      (index.executions.boundaryOwners.get(original)?.has(otherOwner) ? otherOwner : null);
    const group = index.executions.laneByChain.get(chain);
    const owner = node || index.items[raw]?.node;
    if (positions.has(`${group}:${owner}`)) return positions.get(`${group}:${owner}`);
    if (node) return null;
    // A display reference remains the same observed identity; semantic equivalence
    // is deliberately absent here and cannot become a runtime call.
    for (const id of index.eventRows.get(raw) || [])
      if (positions.has(`${group}:${id}`) && index.rows.get(id)?.node.referenceOf === owner)
        return positions.get(`${group}:${id}`);
    return null;
  };
  return visibleSlices(index.flows, window.start, window.end).flatMap((flow) => {
    const fromRow = position(
        flow.from,
        flow.fromNode,
        flow.fromEvent,
        executionOwner(flow.to, flow.toEvent),
      ),
      toRow = position(
        flow.to,
        flow.toNode,
        flow.toEvent,
        executionOwner(flow.from, flow.fromEvent),
      );
    if (fromRow === null || toRow === null) return [];
    const at = index.axis.times[flow.at];
    return [
      {
        ...flow,
        fromRow,
        toRow,
        fromTime: ["call", "activation", "transition", "observation"].includes(flow.type)
          ? at
          : index.axis.times[flow.from],
        toTime: ["return", "completion"].includes(flow.type) ? at : index.axis.times[flow.to],
      },
    ];
  });
}
