/** Immutable execution index. Static projections locate facts and never become calls. */
import { boFacts } from "./replay-steps.js";
import { layerOf, layers } from "./graph-layers.js";
import { callKey, callScope, traceTime } from "./trace-evidence.js";
import { lowerBound } from "./trace-viewport.js";

const canonical = (node) => node.referenceOf || node.event_node || node.id;
const complete = new Set(["return", "error"]);

/** Establish one axis without reordering the graph's authoritative replay ordinals. */
function clock(items) {
  const dates = items.map((item) => traceTime(item.observed_at));
  const invalid = dates.some((value, i) => value === null || (i && value < dates[i - 1]));
  const origin = dates.find((value) => value !== null) ?? 0;
  const times = invalid ? items.map((_, i) => i) : dates.map((value) => value - origin);
  return {
    dates,
    times,
    ordered: !invalid,
    total: times.reduce((max, time) => Math.max(max, time), 1),
    origin,
  };
}

/** Pair repeated IDs by occurrence. Overlapping reuse remains explicitly ambiguous. */
function invocations(items, axis, all) {
  const opened = new Map(),
    slices = [],
    activeParents = new Map(),
    links = [];
  const finish = (slice, raw, unfinished = false) => {
    const start = axis.dates[slice.raw],
      end = axis.dates[raw];
    slices.push({
      ...slice,
      last: raw,
      start: axis.times[slice.raw],
      end: axis.times[raw],
      unfinished,
      duration:
        !unfinished && !slice.ambiguous && start !== null && end !== null && end >= start
          ? end - start
          : null,
    });
  };
  for (const [raw, event] of items.entries()) {
    if (event.kind !== "probe") continue;
    const key = callKey(event),
      scope = callScope(event);
    const parent =
      event.parent_call_id &&
      activeParents.get(JSON.stringify([scope, event.parent_call_id]))?.at(-1);
    if (typeof parent === "number" && event.phase === "enter")
      links.push({ from: parent, to: raw, type: "call" });
    if (typeof parent === "number" && ["return", "decision", "error"].includes(event.phase))
      links.push({ from: raw, to: parent, type: "return" });
    if (!key) continue;
    if (event.phase === "enter") {
      const stack = opened.get(key) || [];
      if (stack.at(-1)?.candidate !== null && stack.at(-1)?.candidate !== undefined) {
        const previous = stack.pop();
        finish(previous, previous.candidate);
        activeParents.get(JSON.stringify([scope, event.call_id]))?.pop();
      }
      if (stack.length) for (const entry of stack) entry.ambiguous = true;
      stack.push({ raw, node: event.node, ambiguous: stack.length > 0, candidate: null });
      opened.set(key, stack);
      const parentKey = JSON.stringify([scope, event.call_id]);
      if (!activeParents.has(parentKey)) activeParents.set(parentKey, []);
      activeParents.get(parentKey).push(raw);
    } else if (opened.get(key)?.length) {
      const stack = opened.get(key),
        slice = stack.at(-1);
      // The native data adapter completes transformations with change/transformed.
      // A business parameter with the same text is not a terminal observation.
      const transformed =
        event.phase === "change" &&
        all.get(event.node)?.data_role === "transform" &&
        event.outputs?.status === "transformed";
      if (complete.has(event.phase) || transformed) {
        finish(stack.pop(), raw);
        activeParents.get(JSON.stringify([scope, event.call_id]))?.pop();
      } else if (["commit", "decision"].includes(event.phase)) slice.candidate = raw;
    }
  }
  for (const stack of opened.values())
    for (const slice of stack)
      finish(slice, slice.candidate ?? items.length - 1, slice.candidate === null);
  const byId = new Map(items.map((event, raw) => [event.id, raw]));
  for (const [to, event] of items.entries())
    for (const dependency of event.depends || []) {
      const from = byId.get(dependency.event);
      // Globally qualified explicit references may cross producer/run boundaries.
      // Unlike a reused parent-call ID, the event ID identifies the exact fact.
      if (from !== undefined && from < to) links.push({ from, to, type: dependency.type });
    }
  return { slices, links };
}

/** Build a reverse map from an observed identity to explicit source/capture projections. */
function projections(all, edges) {
  const aliases = new Map(),
    sources = new Map();
  for (const edge of edges) {
    if (edge.code_relation === "maps") {
      if (!sources.has(edge.to)) sources.set(edge.to, []);
      sources.get(edge.to).push(edge.from);
    } else if (edge.code_relation === "handles") {
      if (!sources.has(edge.from)) sources.set(edge.from, []);
      sources.get(edge.from).push(edge.to);
    }
  }
  const memo = new Map();
  const owners = (id, seen = new Set()) => {
    if (seen.has(id)) return [];
    if (memo.has(id)) return memo.get(id);
    const node = all.get(id);
    if (!node) return [];
    if (!node.code_role) return [canonical(node)];
    const next = new Set(seen).add(id);
    const value = [...new Set((sources.get(id) || []).flatMap((key) => owners(key, next)))];
    memo.set(id, value);
    return value;
  };
  for (const node of all.values()) {
    const origin = node.code_role ? [...new Set([node.id, ...owners(node.id)])] : [canonical(node)];
    for (const id of origin) {
      if (!aliases.has(id)) aliases.set(id, []);
      aliases.get(id).push(node);
    }
  }
  return aliases;
}

export function buildTraceIndex(
  recording,
  items,
  all,
  edges = recording.context.model.edges || [],
) {
  const axis = clock(items),
    calls = invocations(items, axis, all),
    facts = boFacts(recording, items);
  const aliases = projections(all, edges),
    rows = new Map(),
    eventRows = new Map();
  const add = (node, raw, projected, change = null) => {
    if (!rows.has(node.id))
      rows.set(node.id, { id: node.id, node, layer: layerOf(node), marks: [], slices: [] });
    const row = rows.get(node.id);
    const previous = row.marks.at(-1);
    if (previous?.raw === raw) {
      if (change) previous.changes.push(change);
      previous.projected &&= projected;
      return;
    }
    row.marks.push({
      raw,
      node: node.id,
      time: axis.times[raw],
      projected,
      changes: change ? [change] : [],
    });
    if (!eventRows.has(raw)) eventRows.set(raw, []);
    eventRows.get(raw).push(node.id);
  };
  const put = (id, raw, change = null) => {
    for (const node of aliases.get(id) || []) {
      // A captured parameter belongs to its declared direction/field only.
      if (node.field && node.event_node) {
        const values = node.direction === "in" ? items[raw].inputs : items[raw].outputs;
        if (!Object.hasOwn(values || {}, node.field)) continue;
        if (change && (change.field !== node.field || change.direction !== node.direction))
          continue;
      }
      add(node, raw, !!node.code_role && node.id !== id, change);
    }
  };
  const states = [...all.values()].filter((node) => node.kind === "state");
  for (const [raw, event] of items.entries()) {
    if (event.node) put(event.node, raw);
    for (const change of facts.changes[raw] || []) {
      put(change.node, raw, change);
      if (change.kind === "business")
        for (const node of states)
          if (node.value === change.before || node.value === change.after)
            add(node, raw, false, change);
    }
  }
  for (const slice of calls.slices) {
    // Duration belongs to the instrumented node, never to a source mapping/ancestor.
    for (const node of aliases.get(slice.node) || []) {
      if (node.field || canonical(node) !== slice.node) continue;
      rows.get(node.id)?.slices.push(slice);
    }
  }
  for (const row of rows.values()) {
    row.slices.sort((a, b) => a.start - b.start || a.raw - b.raw);
    let end = -Infinity;
    row.maxEnds = row.slices.map((slice) => (end = Math.max(end, slice.end)));
  }
  return { recording, items, axis, rows, eventRows, changes: facts.changes, links: calls.links };
}

/** Project the index to visible graph identities; hidden nodes do not reserve rows. */
export function traceRows(
  index,
  { visible, scope = "view", order = layers.map((layer) => layer.id), expanded = [] } = {},
) {
  const groups = new Map();
  for (const row of index.rows.values()) {
    if (scope === "view" && !visible?.has(row.id)) continue;
    if (!groups.has(row.layer)) groups.set(row.layer, []);
    groups.get(row.layer).push(row);
  }
  const result = [];
  for (const id of order) {
    const children = groups.get(id);
    if (!children?.length) continue;
    const layer = layers.find((item) => item.id === id);
    const marks = children.flatMap((row) => row.marks).sort((a, b) => a.raw - b.raw);
    const unique = marks.filter((mark, i) => !i || mark.raw !== marks[i - 1].raw);
    const slices = children
      .flatMap((row) => row.slices)
      .sort((a, b) => a.start - b.start || a.raw - b.raw);
    let maxEnd = -Infinity;
    result.push({
      id: "layer:" + id,
      layer: id,
      header: true,
      label: layer.label,
      color: layer.color,
      count: children.length,
      marks: unique,
      slices,
      maxEnds: slices.map((slice) => (maxEnd = Math.max(maxEnd, slice.end))),
    });
    if (expanded.includes(id))
      result.push(
        ...children.sort((a, b) => a.marks[0].raw - b.marks[0].raw || a.id.localeCompare(b.id)),
      );
  }
  return result;
}

export function tracePoints(rows, index, plan) {
  const allowed = new Set(plan),
    seen = new Set(),
    points = [];
  for (const row of rows)
    for (const mark of row.marks) {
      if (!allowed.has(mark.raw) || seen.has(mark.raw)) continue;
      seen.add(mark.raw);
      points.push({ raw: mark.raw, time: index.axis.times[mark.raw] });
    }
  // Start/end snapshots remain seekable even when the view has no visible calls.
  for (const raw of [0, index.items.length - 1])
    if (allowed.has(raw) && !seen.has(raw)) points.push({ raw, time: index.axis.times[raw] });
  return points.sort((a, b) => a.time - b.time || a.raw - b.raw);
}

export function marksInWindow(row, start, end) {
  const first = lowerBound(row.marks, start, (mark) => mark.time);
  const last = lowerBound(row.marks, end, (mark) => mark.time);
  return row.marks.slice(first, last + 1);
}
