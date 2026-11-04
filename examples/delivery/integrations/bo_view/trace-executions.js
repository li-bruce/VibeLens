/** Causal executions share a layer band until they overlap in time.
 * A process run or business entity is not a request. Explicit invocation roots
 * establish executions; dependencies connect them without merging competitors.
 */
import { callScope, referencedParent, configurationScopeMatches } from "./trace-evidence.js";
import { packTracks } from "./trace-tracks.js";

const scopeKey = (event, call = event.call_id) => JSON.stringify([callScope(event), call]);

/** A sequence orders one producer stream, never neighbouring workers or runs. */
function producerOrder(event) {
  if (
    !Number.isSafeInteger(event.seq) ||
    event.seq < 0 ||
    !["project_id", "build_id", "run_id", "producer_id"].every(
      (key) => typeof event[key] === "string" && event[key].length,
    )
  )
    return null;
  return {
    scope: JSON.stringify(
      ["project_id", "build_id", "run_id", "producer_id", "stream_id"].map(
        (key) => event[key] || "",
      ),
    ),
    event: event.id,
    seq: event.seq,
  };
}

/** Preserve actual witnesses for clock ties without changing their timestamps. */
function boundaryOrder(chain, items, times, ambiguous) {
  const start = producerOrder(chain.root);
  if (!start || ambiguous.has(start.scope)) return null;
  let end = null;
  for (const raw of chain.events) {
    if (times[raw] !== chain.end) continue;
    const candidate = producerOrder(items[raw]);
    if (
      candidate?.scope === start.scope &&
      candidate.seq >= start.seq &&
      (!end || candidate.seq > end.seq)
    )
      end = candidate;
  }
  return { scope: start.scope, start, end };
}

function orderPosition(intervals, sequence) {
  let low = 0,
    high = intervals.length;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (intervals[middle].start.seq < sequence) low = middle + 1;
    else high = middle;
  }
  return low;
}

/** Only an entry inside a witnessed interval establishes same-clock overlap. */
function orderedOverlap(orders, witness) {
  if (!witness) return false;
  const intervals = orders?.get(witness.scope) || [],
    position = orderPosition(intervals, witness.start.seq),
    previous = intervals[position - 1],
    next = intervals[position];
  return (
    (previous && previous.end.seq > witness.start.seq) ||
    (next && witness.end && next.start.seq > witness.start.seq && next.start.seq < witness.end.seq)
  );
}

function retainOrder(orders, witness) {
  if (!witness?.end || witness.end.seq <= witness.start.seq) return;
  if (!orders.has(witness.scope)) orders.set(witness.scope, []);
  const intervals = orders.get(witness.scope);
  intervals.splice(orderPosition(intervals, witness.start.seq), 0, witness);
}

export function executionIndex(index) {
  const { items, axis } = index;
  const entries = new Map(),
    open = new Map(),
    chains = new Map(),
    byEvent = new Map(),
    byId = new Map();
  const originalEvents = new Map(
    [...(index.recording.context.events || []), ...items].map((event) => [event.id, event]),
  );
  const sequenceOwners = new Map(),
    ambiguousOrders = new Set();
  for (const event of originalEvents.values()) {
    const witness = producerOrder(event);
    if (!witness) continue;
    if (!sequenceOwners.has(witness.scope)) sequenceOwners.set(witness.scope, new Map());
    const owners = sequenceOwners.get(witness.scope);
    if (owners.has(witness.seq) && owners.get(witness.seq) !== witness.event)
      ambiguousOrders.add(witness.scope);
    owners.set(witness.seq, witness.event);
  }
  const explicitOwner = (event) => {
    const parent = referencedParent(event, originalEvents);
    return parent && byId.get(parent.id);
  };
  const slices = index.lifecycles.slices.filter((slice) => !slice.source_node);
  const byEntry = new Map(slices.map((slice) => [slice.raw, slice]));
  const chain = (id, raw, root = items[raw]) => {
    if (!chains.has(id))
      chains.set(id, {
        id,
        raw,
        last: raw,
        root,
        start: axis.times[raw],
        end: axis.times[raw],
        events: [],
        kind: id.startsWith("observation:") ? "observation" : "invocation",
      });
    return chains.get(id);
  };
  const contextOrder = new Map(
    (index.recording.context.events || []).map((event, raw) => [event.id, raw]),
  );
  const clipped = slices
    .filter((slice) => slice.context_entry)
    .sort((a, b) => contextOrder.get(a.context_entry.id) - contextOrder.get(b.context_entry.id));
  for (const slice of clipped) {
    const original = slice.context_entry;
    const parent = original.parent_call_id && open.get(scopeKey(original, original.parent_call_id));
    const owner =
      explicitOwner(original) || parent?.chain || chain("execution:" + original.id, 0, original).id;
    open.set(scopeKey(original), {
      chain: owner,
      last: slice.last,
      unfinished: slice.unfinished,
      origin: original.id,
    });
    byId.set(original.id, owner);
  }
  // A dependency may reference an already-witnessed wait/value rather than the
  // entry itself. Keep its original ID and attach it only inside the same open
  // invocation (or its explicit parent), after that invocation's actual entry.
  for (const original of index.lifecycles.contextSources) {
    if (byId.has(original.id)) continue;
    const direct = explicitOwner(original);
    if (direct) {
      byId.set(original.id, direct);
      continue;
    }
    const owner =
      open.get(scopeKey(original)) ||
      (original.parent_call_id && open.get(scopeKey(original, original.parent_call_id)));
    if (owner && contextOrder.get(original.id) >= contextOrder.get(owner.origin))
      byId.set(original.id, owner.chain);
  }
  const contextOwners = new Set(byId.values());
  if (contextOwners.size === 1) byEvent.set(0, contextOwners.values().next().value);
  for (const [raw, event] of items.entries()) {
    if (event.kind !== "probe") continue;
    for (const [key, value] of open) if (!value.unfinished && value.last < raw) open.delete(key);
    const key = scopeKey(event);
    const slice = byEntry.get(raw);
    const parent = event.parent_call_id && open.get(scopeKey(event, event.parent_call_id));
    let owner = open.get(key)?.chain || explicitOwner(event) || parent?.chain;
    if (!owner && slice) {
      const original = slice.context_entry || event;
      owner = chain("execution:" + original.id, raw, original).id;
    }
    if (!owner) {
      // Declared external notifications are real point roots. An internal fact
      // lacking ownership remains unassigned; time never supplies its parent.
      const prior = entries.get(key);
      const prefix = index.all.get(event.node)?.observation_root ? "execution:" : "observation:";
      owner = prior?.chain || chain(prefix + event.id, raw).id;
    }
    const value = chain(owner, raw);
    value.events.push(raw);
    value.last = raw;
    value.end = Math.max(value.end, axis.times[raw]);
    byEvent.set(raw, owner);
    byId.set(event.id, owner);
    if (slice) {
      value.end = Math.max(value.end, slice.unfinished ? axis.total : axis.times[slice.last]);
      const entry = { chain: owner, last: slice.last, unfinished: slice.unfinished };
      open.set(key, entry);
      entries.set(key, entry);
    }
    if (["return", "error"].includes(event.phase)) open.delete(key);
  }
  // A final child's boundary can precede its parent's recorded exit. Keep the
  // maximum witnessed end, rather than replacing it with the last arrival time.
  for (const slice of slices) {
    const owner = slice.context_entry ? byId.get(slice.context_entry.id) : byEvent.get(slice.raw);
    if (owner) {
      const value = chains.get(owner);
      value.end = Math.max(value.end, slice.unfinished ? axis.total : axis.times[slice.last]);
    }
  }
  const boundaryOwners = new Map();
  for (const link of index.links) {
    for (const [side, other] of [
      ["from", "to"],
      ["to", "from"],
    ]) {
      const original = link[side + "Event"];
      if (!original || byId.has(original)) continue;
      const owner = link[other + "Event"]
        ? byId.get(link[other + "Event"])
        : byEvent.get(link[other]);
      if (!owner) continue;
      if (!boundaryOwners.has(original)) boundaryOwners.set(original, new Set());
      boundaryOwners.get(original).add(owner);
    }
  }
  for (const value of chains.values())
    value.orderWitness = boundaryOrder(value, items, axis.times, ambiguousOrders);
  const ordered = [...chains.values()].sort((a, b) => a.start - b.start || a.raw - b.raw);
  const lanes = [],
    laneByChain = new Map(),
    boundaryOrders = new Map();
  for (const value of ordered) {
    // Reuse an existing band after completion. Only overlapping executions add
    // another complete set of layer rows; sequential requests do not grow axes.
    let lane = lanes.find(
      (item) =>
        item.kind === value.kind &&
        (item.kind === "observation" ||
          item.end < value.start ||
          (item.end === value.start &&
            !orderedOverlap(boundaryOrders.get(item.id), value.orderWitness))),
    );
    if (!lane) {
      lane = {
        id: "lane:" + value.id,
        number: lanes.filter((item) => item.kind === "invocation").length + 1,
        kind: value.kind,
        end: -Infinity,
        chains: [],
      };
      lanes.push(lane);
      boundaryOrders.set(lane.id, new Map());
    }
    lane.chains.push(value);
    // Only tied boundary intervals need ordering. Older clock ranges cannot
    // affect future lane reuse; retaining them would grow lookup cost needlessly.
    if (value.end > lane.end) boundaryOrders.get(lane.id).clear();
    if (value.end >= lane.end) retainOrder(boundaryOrders.get(lane.id), value.orderWitness);
    lane.end = Math.max(lane.end, value.end);
    laneByChain.set(value.id, lane.id);
  }
  lanes.sort((a, b) => Number(a.kind === "observation") - Number(b.kind === "observation"));
  return { chains: ordered, lanes, byEvent, byId, boundaryOwners, laneByChain };
}

/** Produce exactly one row per included layer in each execution band.
 * Graph scope/depth changes presentation only; all source lifetimes stay indexed.
 */
export function executionRows(index, { visible, scope, order, included, collapsed = [] }) {
  const scoped = [...index.rows.values()].filter((row) => scope === "all" || visible?.has(row.id));
  if (!scoped.length) return [];
  const selected = scoped.filter((row) => included.has(row.layer));
  const available = new Set(
    [...index.all.values()]
      .filter((node) => scope === "all" || visible?.has(node.id))
      .map((node) => index.layerOf(node)),
  );
  const sequence = order.filter((id) => included.has(id) && available.has(id));
  // Business remains the fold handle even when users reorder the graph planes.
  if (sequence.includes("business")) {
    sequence.splice(sequence.indexOf("business"), 1);
    sequence.unshift("business");
  }
  const result = [];
  for (const lane of index.executions.lanes) {
    const belongs = (raw, original = null, stateScope = null) => {
      if (original) {
        const owners = index.executions.byId.has(original.id)
          ? [index.executions.byId.get(original.id)]
          : [...(index.executions.boundaryOwners.get(original.id) || [])];
        return owners.some((owner) => index.executions.laneByChain.get(owner) === lane.id);
      }
      if (raw === 0 && stateScope)
        return lane.chains.some((chain) => configurationScopeMatches(chain.root, stateScope));
      return index.executions.laneByChain.get(index.executions.byEvent.get(raw)) === lane.id;
    };
    const relevant = scoped.some((row) =>
      row.marks.some((mark) => belongs(mark.raw, mark.contextEvent)),
    );
    if (!relevant) continue;
    const folded = collapsed.includes(lane.id);
    for (const layer of folded && sequence.includes("business") ? ["business"] : sequence) {
      const children = selected.filter((row) => row.layer === layer);
      const marks = children
        .flatMap((row) => row.marks.filter((mark) => belongs(mark.raw, mark.contextEvent)))
        .sort((a, b) => a.time - b.time || a.raw - b.raw);
      const slices = children
        .flatMap((row) =>
          row.slices
            .filter((slice) => belongs(slice.raw, slice.context_entry, slice.scope))
            .map((slice) => ({ ...slice, node: row.id })),
        )
        .sort((a, b) => a.start - b.start || a.raw - b.raw);
      let end = -Infinity;
      result.push({
        id: `${lane.id}:${layer}`,
        layer,
        group: lane.id,
        groupNumber: lane.number,
        groupKind: lane.kind,
        groupStart: layer === (folded ? "business" : sequence[0]),
        folded,
        members: children.map((row) => row.id),
        marks,
        ...packTracks(slices),
        maxEnds: slices.map((slice) => (end = Math.max(end, slice.end))),
        chains: lane.chains,
      });
    }
  }
  return result;
}
