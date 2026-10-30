/** Pair actual invocation boundaries. Shared by the timeline and graph activation overlay.
 * Parentage is producer/entity scoped; containment and source mappings never create calls.
 */
import { callKey, callScope } from "./trace-evidence.js";

export function traceLifecycles(items, all) {
  const opened = new Map(),
    parents = new Map(),
    slices = [],
    links = [],
    childEnds = new Map();
  const parentKey = (event) => JSON.stringify([callScope(event), event.call_id]);
  const finish = (slice, raw, unfinished = false) => {
    slice.last = raw;
    slice.unfinished = unfinished;
    slice.closed = !unfinished;
    slices.push(slice);
    if (slice.parent !== undefined)
      childEnds.set(slice.parent, Math.max(childEnds.get(slice.parent) ?? -1, raw));
    if (!unfinished && slice.parent !== undefined) {
      links.push({ from: raw, to: slice.parent, at: raw, type: "return", invocation: slice.raw });
    }
    const active = parents.get(parentKey(items[slice.raw]));
    if (active?.at(-1) === slice) active.pop();
  };
  for (const [raw, event] of items.entries()) {
    if (event.kind !== "probe") continue;
    const key = callKey(event);
    if (!key) continue;
    const stack = opened.get(key) || [];
    if (event.phase === "enter") {
      // Legacy commit-only producers remain supported. A later owned child is
      // evidence that the commit was not the end of the enclosing operation.
      const prior = stack.at(-1);
      if (prior?.candidate !== null && prior?.candidate !== undefined && !prior.afterCommit) {
        stack.pop();
        finish(prior, prior.candidate);
      }
      const parent = event.parent_call_id
        ? parents.get(JSON.stringify([callScope(event), event.parent_call_id]))?.at(-1)
        : null;
      if (parent) {
        if (parent.candidate !== null) parent.afterCommit = true;
        links.push({ from: parent.raw, to: raw, at: raw, type: "call" });
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
        stages: [{ raw, phase: "running" }],
      };
      stack.push(slice);
      opened.set(key, stack);
      if (!parents.has(parentKey(event))) parents.set(parentKey(event), []);
      parents.get(parentKey(event)).push(slice);
    } else if (stack.length) {
      const slice = stack.at(-1);
      slice.observed = raw;
      if (event.phase === "wait" && slice.stages.at(-1).phase !== "waiting")
        slice.stages.push({ raw, phase: "waiting" });
      else if (event.phase === "read" && slice.stages.at(-1).phase === "waiting")
        slice.stages.push({ raw, phase: "running" });
      const transformed =
        event.phase === "change" &&
        all.get(event.node)?.data_role === "transform" &&
        event.outputs?.status === "transformed";
      if (["return", "error"].includes(event.phase) || (transformed && !slice.explicit)) {
        stack.pop();
        finish(slice, raw);
      } else if (!slice.explicit && ["commit", "decision"].includes(event.phase))
        slice.candidate = raw;
      if (slice.parent !== undefined) {
        const parent = parents
          .get(JSON.stringify([callScope(event), event.parent_call_id]))
          ?.at(-1);
        if (parent?.candidate !== null && parent?.candidate !== undefined)
          parent.afterCommit = true;
      }
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
    const parent = byEntry.get(link.type === "call" ? link.from : link.to);
    link.outlivesParent = !!(parent?.closed && link.at > parent.last);
  }
  const byId = new Map(items.map((event, raw) => [event.id, raw]));
  for (const [to, event] of items.entries())
    for (const dependency of event.depends || []) {
      const from = byId.get(dependency.event);
      if (from !== undefined && from < to) links.push({ from, to, type: dependency.type });
    }
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
