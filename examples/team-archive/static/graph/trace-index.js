/** Immutable execution index. Static projections locate facts and never become calls. */
import { boFacts } from "./replay-steps.js";
import { layerOf, layers } from "./graph-layers.js";
import { traceTime } from "./trace-evidence.js";
import { contextualLifecycles } from "./trace-context.js";
import { stateResidencies, activityResidencies } from "./trace-residencies.js";
import { indexFlows } from "./trace-flows.js";
import { lowerBound } from "./trace-viewport.js";

const canonical = (node) => node.referenceOf || node.event_node || node.id;

/** Establish one axis without reordering the graph's authoritative replay ordinals. */
function clock(items, until) {
  const dates = items.map((item) => traceTime(item.observed_at));
  const observed = dates.filter((_, i) => !["start", "end"].includes(items[i].kind));
  const invalid =
    dates.some((value) => value === null) ||
    observed.some((value, i) => i && value < observed[i - 1]);
  const visual = [...dates];
  let boundaryAdjusted = false;
  if (!invalid && visual.length) {
    if (items[0].kind === "start" && observed.length && dates[0] > observed[0]) {
      visual[0] = observed[0];
      boundaryAdjusted = true;
    }
    if (items.at(-1).kind === "end" && observed.length && dates.at(-1) < observed.at(-1)) {
      visual[visual.length - 1] = observed.at(-1);
      boundaryAdjusted = true;
    }
  }
  const minimum = visual.reduce(
    (min, value) => (value === null ? min : Math.min(min, value)),
    Infinity,
  );
  const origin = Number.isFinite(minimum) ? minimum : 0;
  const times = invalid ? items.map((_, i) => i) : visual.map((value) => value - origin);
  const tail = traceTime(until);
  return {
    dates,
    times,
    ordered: !invalid,
    boundaryAdjusted,
    total: times.reduce(
      (max, time) => Math.max(max, time),
      tail !== null && !invalid ? Math.max(1, tail - origin) : 1,
    ),
    origin,
  };
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
  const axis = clock(items, recording.observed_until),
    calls = contextualLifecycles(recording, items, all),
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
    const targets = new Map((aliases.get(slice.node) || []).map((node) => [node.id, node]));
    if (all.has(slice.node)) targets.set(slice.node, all.get(slice.node));
    for (const node of targets.values()) {
      const declaredSubject = node.id === slice.node && !!node.lifecycle;
      if ((node.field || canonical(node) !== slice.node) && !declaredSubject) continue;
      if (!rows.has(node.id))
        rows.set(node.id, { id: node.id, node, layer: layerOf(node), marks: [], slices: [] });
      const start = axis.dates[slice.raw],
        end = axis.dates[slice.last];
      rows.get(node.id)?.slices.push({
        ...slice,
        start: axis.times[slice.raw],
        end: slice.unfinished ? axis.total : axis.times[slice.last],
        termination: slice.terminal?.termination,
        stages: slice.stages.map((stage, i) => ({
          ...stage,
          start: axis.times[stage.raw],
          end:
            i + 1 < slice.stages.length
              ? axis.times[slice.stages[i + 1].raw]
              : slice.unfinished
                ? axis.total
                : axis.times[slice.last],
        })),
        duration:
          !slice.unfinished && !slice.ambiguous && axis.ordered && start !== null && end !== null
            ? end - start
            : null,
      });
    }
  }
  for (const original of calls.contextSources)
    for (const node of aliases.get(original.node) || []) {
      if (node.field) continue;
      add(node, 0, true);
      rows.get(node.id).marks.find((mark) => mark.raw === 0).contextEvent = original;
    }
  const occupancy = stateResidencies(recording, items, facts.changes, all, axis);
  for (const slice of [
    ...occupancy.slices,
    ...activityResidencies(recording, items, facts.changes, all, axis),
  ]) {
    // A directly instrumented activity already has its actual call interval.
    if (
      slice.role === "activity" &&
      rows
        .get(slice.node)
        ?.slices.some(
          (call) =>
            items[call.raw].attempt === slice.scope &&
            call.raw <= slice.raw &&
            call.last >= slice.last,
        )
    )
      continue;
    add(all.get(slice.node), slice.raw, false);
    if (slice.last !== slice.raw) add(all.get(slice.node), slice.last, false);
    rows.get(slice.node).slices.push(slice);
  }
  for (const row of rows.values()) {
    row.marks.sort((a, b) => a.raw - b.raw);
    row.slices.sort((a, b) => a.start - b.start || a.raw - b.raw);
    let end = -Infinity;
    row.maxEnds = row.slices.map((slice) => (end = Math.max(end, slice.end)));
  }
  return {
    recording,
    items,
    axis,
    rows,
    eventRows,
    changes: facts.changes,
    links: [...calls.links, ...occupancy.links],
    flows: indexFlows([...calls.links, ...occupancy.links], axis.times),
    lifecycles: calls,
  };
}

/** Project the index to visible graph identities; hidden nodes do not reserve rows. */
export function traceRows(
  index,
  {
    visible,
    scope = "view",
    order = layers.map((layer) => layer.id),
    expanded = [],
    depth = "all",
    layerMode = "through",
  } = {},
) {
  const groups = new Map();
  const boundary = order.indexOf(depth);
  const included = new Set(
    depth === "all" || boundary < 0
      ? order
      : layerMode === "single"
        ? [depth]
        : order.slice(0, boundary + 1),
  );
  for (const row of index.rows.values()) {
    if (!included.has(row.layer)) continue;
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
      members: children.map((row) => row.id),
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
