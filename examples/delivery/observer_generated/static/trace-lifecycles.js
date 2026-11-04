/** Pair actual invocation boundaries. Shared by the timeline and graph activation overlay.
 * Parentage is producer/entity scoped; containment and source mappings never create calls.
 */
import { callKey, callScope, referencedParent } from "./trace-evidence.js";
import { lifecycleTransition, lifecycleBoundary } from "./node-lifecycle.js";
import { projectAPIIntervals } from "./api-observation.js";

export function traceLifecycles(items, all, { projections = true, registeredOnly = false } = {}) {
  const opened = new Map(),
    parents = new Map(),
    slices = [],
    links = [],
    childEnds = new Map();
  const activeEntries = new Map();
  const knownEntries = new Map();
  const byEventId = new Map(items.map((event) => [event.id, event]));
  const parentKey = (event) => JSON.stringify([callScope(event), event.call_id]);
  const finish = (slice, raw, unfinished = false) => {
    slice.last = raw;
    slice.unfinished = unfinished;
    slice.closed = !unfinished;
    if (!unfinished) slice.terminal = lifecycleBoundary(all.get(slice.node), items[raw]);
    slices.push(slice);
    if (slice.parent !== undefined)
      childEnds.set(slice.parent, Math.max(childEnds.get(slice.parent) ?? -1, raw));
    if (!unfinished && slice.parent !== undefined) {
      links.push({
        from: raw,
        to: slice.parent,
        at: raw,
        type: ["return", "error"].includes(items[raw].phase) ? "return" : "completion",
        invocation: slice.raw,
      });
    }
    const active = parents.get(parentKey(items[slice.raw]));
    if (active?.at(-1) === slice) active.pop();
    activeEntries.delete(items[slice.raw].id);
  };
  for (const [raw, event] of items.entries()) {
    if (event.kind !== "probe") continue;
    const key = callKey(event);
    if (!key) continue;
    const transition = lifecycleTransition(all.get(event.node), event);
    if (registeredOnly && !transition?.registered) continue;
    const stack = opened.get(key) || [];
    const explicitParent = referencedParent(event, byEventId);
    const enclosing = event.parent_event_id
      ? explicitParent &&
        (activeEntries.get(explicitParent.id) ||
          (event.phase === "enter" ? knownEntries.get(explicitParent.id) : null))
      : event.parent_call_id &&
        parents.get(JSON.stringify([callScope(event), event.parent_call_id]))?.at(-1);
    if (transition?.boundary === "start") {
      // Legacy commit-only producers remain supported. A later owned child is
      // evidence that the commit was not the end of the enclosing operation.
      const prior = stack.at(-1);
      if (prior?.candidate !== null && prior?.candidate !== undefined && !prior.afterCommit) {
        stack.pop();
        finish(prior, prior.candidate);
      }
      const parent = enclosing;
      if (parent) {
        if (parent.candidate !== null) parent.afterCommit = true;
        links.push({
          from: parent.raw,
          to: raw,
          at: raw,
          type: event.phase === "enter" ? "call" : "activation",
        });
      }
      if (stack.length) for (const entry of stack) entry.ambiguous = true;
      const slice = {
        raw,
        observed: raw,
        node: event.node,
        parent: parent?.raw,
        ambiguous: stack.length > 0,
        candidate: null,
        afterCommit: false,
        explicit: event.lifecycle === "span",
        stages: [
          { raw, phase: transition.kind === "waiting" ? "waiting" : "running", ...transition },
        ],
      };
      stack.push(slice);
      opened.set(key, stack);
      if (!parents.has(parentKey(event))) parents.set(parentKey(event), []);
      parents.get(parentKey(event)).push(slice);
      activeEntries.set(event.id, slice);
      knownEntries.set(event.id, slice);
    } else if (stack.length) {
      const slice = stack.at(-1);
      slice.observed = raw;
      if (transition?.boundary === "update") {
        const phase = transition.kind === "waiting" ? "waiting" : "running";
        if (slice.stages.at(-1).state !== transition.state)
          slice.stages.push({ raw, phase, ...transition });
      }
      if (transition?.boundary === "end") {
        stack.pop();
        finish(slice, raw);
      } else if (
        !slice.explicit &&
        !all.get(event.node)?.lifecycle &&
        ["commit", "decision"].includes(event.phase)
      )
        slice.candidate = raw;
      if (slice.parent !== undefined) {
        const parent = parents
          .get(JSON.stringify([callScope(event), event.parent_call_id]))
          ?.at(-1);
        if (parent?.candidate !== null && parent?.candidate !== undefined)
          parent.afterCommit = true;
      }
    } else if (enclosing) {
      // A selected value/rule fact was witnessed inside this invocation. It is
      // an ownership link, not a new call or an invented duration.
      links.push({ from: enclosing.raw, to: raw, at: raw, type: "observation" });
    }
  }
  for (const stack of opened.values())
    for (const slice of stack) {
      if (slice.parent !== undefined)
        childEnds.set(slice.parent, Math.max(childEnds.get(slice.parent) ?? -1, items.length - 1));
    }
  for (const stack of opened.values())
    for (const slice of stack) {
      const laterChild = (childEnds.get(slice.raw) ?? -1) > slice.candidate;
      const terminal = slice.candidate !== null && !slice.afterCommit && !laterChild;
      finish(slice, terminal ? slice.candidate : Math.max(0, items.length - 1), !terminal);
    }
  const byEntry = new Map(slices.map((slice) => [slice.raw, slice]));
  for (const link of links) {
    const parent = byEntry.get(["call", "activation"].includes(link.type) ? link.from : link.to);
    link.outlivesParent = !!(parent?.closed && link.at > parent.last);
  }
  const byId = new Map(items.map((event, raw) => [event.id, raw]));
  // Standard Span Links connect distinct executions; equal object IDs never do.
  const bySpan = new Map(),
    linked = new Set();
  const spanKey = (value) => (value ? `${value.trace_id}:${value.span_id}` : null);
  items.forEach((event, raw) => {
    const key = spanKey(event.trace);
    if (key && event.phase === "enter" && !bySpan.has(key)) bySpan.set(key, raw);
  });
  items.forEach((event, to) => {
    for (const relation of event.trace?.links || []) {
      const from = bySpan.get(spanKey(relation));
      const key = `${spanKey(event.trace)}:${spanKey(relation)}:${relation.relation || "trigger"}`;
      if (from === undefined || linked.has(key)) continue;
      linked.add(key);
      links.push({ from, to, at: to, type: relation.relation || "trigger", evidence: "otel-link" });
    }
  });
  for (const [to, event] of items.entries())
    for (const dependency of event.depends || []) {
      const from = byId.get(dependency.event);
      if (from !== undefined && from < to) links.push({ from, to, type: dependency.type });
    }
  if (projections)
    for (const node of all.values()) {
      const owner = node.event_node || node.referenceOf;
      if (!node.lifecycle || !owner || owner === node.id || !all.has(owner)) continue;
      // A semantic parameter has its own identity and only its explicit value/event
      // bindings. The owner's entry never invents a parameter invocation.
      const projected = items.map((event) =>
        event.node === owner
          ? { ...event, node: node.id, parent_call_id: null, parent_event_id: null }
          : { kind: "projection-boundary" },
      );
      const observed = traceLifecycles(projected, new Map([[node.id, node]]), {
        projections: false,
        registeredOnly: true,
      });
      slices.push(
        ...observed.slices.map((slice) => ({ ...slice, role: "registered", source_node: owner })),
      );
    }
  if (projections) slices.push(...projectAPIIntervals(slices, all.values()));
  return { slices, links };
}

/** Active means a witnessed entry without its completion at the selected ordinal. */
export function activeInvocations(lifecycles, raw) {
  return lifecycles.slices.filter(
    (slice) =>
      !slice.ambiguous &&
      slice.raw <= raw &&
      (slice.unfinished ? raw <= slice.last : raw < slice.last),
  );
}
