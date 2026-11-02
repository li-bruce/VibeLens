/** Persistent activation states, as distinct from a brief edge-transfer animation. */
import { traceLifecycles } from "./trace-lifecycles.js";
import { traceTime } from "./trace-evidence.js";

const cache = new WeakMap();
export function graphActivations(events, nodes) {
  const prior = cache.get(events);
  const signature = `${events.length}:${events.at(-1)?.id || ""}`;
  if (prior?.signature === signature && prior.nodes === nodes) return prior.states;
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
    const state = slice.unfinished ? slice.stages.at(-1) : slice.terminal;
    const phase = slice.ambiguous
      ? "unknown"
      : slice.unfinished
        ? state?.kind === "waiting"
          ? "waiting"
          : "running"
        : state?.registered
          ? "ended"
          : state?.state || "boundary";
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
      label: previous?.runningCount && phase !== "running" ? previous.label : state?.label,
      state: previous?.runningCount && phase !== "running" ? previous.state : state?.state,
      registered:
        previous?.runningCount && phase !== "running" ? previous.registered : !!state?.registered,
      termination: slice.terminal?.termination,
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
  cache.set(events, { signature, nodes, states });
  return states;
}

export function activationFor(node, view, events) {
  if (((node.field || node.kind === "state") && !node.lifecycle) || !view.model || !events.length)
    return null;
  return (
    graphActivations(events, view.model.nodes).get(
      node.lifecycle ? node.id : node.referenceOf || node.event_node || node.id,
    ) || null
  );
}
