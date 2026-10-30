/** Persistent activation states, as distinct from a brief edge-transfer animation. */
import { traceLifecycles } from "./trace-lifecycles.js";
import { traceTime } from "./trace-evidence.js";

const cache = new WeakMap();
export function graphActivations(events, nodes) {
  const prior = cache.get(events);
  const signature = `${events.length}:${events.at(-1)?.id || ""}`;
  if (prior?.signature === signature) return prior.states;
  const items = events.map((event) => ({ ...event, kind: event.kind || "probe" }));
  const all = new Map(nodes.map((node) => [node.id, node]));
  const facts = traceLifecycles(items, all),
    states = new Map();
  // Process closed scopes first, so any still-running concurrent scope takes priority.
  for (const slice of [...facts.slices].sort(
    (a, b) => Number(a.unfinished) - Number(b.unfinished) || a.raw - b.raw,
  )) {
    const last = items[slice.last],
      start = items[slice.raw];
    const own = items[slice.observed];
    const phase = slice.ambiguous
      ? "unknown"
      : slice.unfinished
        ? own?.phase === "wait"
          ? "waiting"
          : "running"
        : last?.phase === "error"
          ? "failed"
          : "completed";
    const beginning = traceTime(start.observed_at),
      end = traceTime(last?.observed_at);
    const previous = states.get(slice.node);
    const runningCount = (previous?.runningCount || 0) + Number(phase === "running");
    const waitingCount = (previous?.waitingCount || 0) + Number(phase === "waiting");
    const explicitActive =
      (previous?.explicitActive || 0) +
      Number(slice.explicit && ["running", "waiting"].includes(phase));
    states.set(slice.node, {
      phase: runningCount ? "running" : waitingCount ? "waiting" : phase,
      explicit: explicitActive > 0 || slice.explicit,
      runningCount,
      waitingCount,
      activeCount: runningCount + waitingCount,
      explicitActive,
      callId: start.call_id,
      start: start.id,
      end: slice.unfinished ? null : last.id,
      duration:
        !slice.unfinished &&
        !slice.ambiguous &&
        beginning !== null &&
        end !== null &&
        end >= beginning
          ? end - beginning
          : null,
      parent: slice.parent === undefined ? null : items[slice.parent].node,
    });
  }
  cache.set(events, { signature, states });
  return states;
}

export function activationFor(node, view, events) {
  if (node.field || node.kind === "state" || !view.model || !events.length) return null;
  return (
    graphActivations(events, view.model.nodes).get(
      node.referenceOf || node.event_node || node.id,
    ) || null
  );
}
