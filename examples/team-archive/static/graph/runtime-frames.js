import { t as boTranslate } from "./i18n.js";
// Event-bound authoritative projections. No business commands or clock inference.
const copy = (value) => structuredClone(value);
/** Find the exact recorded state snapshot associated with this event. */
export function runtimeFrame(recording, event) {
  if (recording.runtime_frames?.schema !== "stategraph-runtime-frames/v1" || !event) return null;
  const frame =
    recording.runtime_frames.frames.find(
      (f) =>
        f.event_id === event.id &&
        f.run_id === event.run_id &&
        f.build_id === recording.build_id &&
        Number.isInteger(event.revision) &&
        f.revision === event.revision &&
        f.machine.state_revision === event.revision,
    ) || null;
  // Older recordings retained the validated identity on the event, but not
  // its single-instance projection. Use that explicit evidence only.
  if (frame && event.snapshot_instance && frame.machine.configurations?.length === 1) {
    const cfg = frame.machine.configurations[0];
    if (cfg.snapshot_instance && cfg.snapshot_instance !== event.snapshot_instance) return null;
    if (!cfg.snapshot_instance)
      return {
        ...frame,
        machine: {
          ...frame.machine,
          configurations: [{ ...cfg, snapshot_instance: event.snapshot_instance }],
        },
      };
  }
  return frame;
}
export function applyRuntimeFrame(recording, event, view) {
  if (!recording.runtime_frames) return false;
  const exact = runtimeFrame(recording, event);
  view.replay.runtime_exact = Boolean(exact);
  if (exact) {
    view.machine = copy(exact.machine);
    view.authority = copy(exact.authority);
  } else {
    view.machine = {
      current: null,
      configurations: [],
      journal: [],
      runtime_gap: boTranslate("No runtime snapshot recorded for this step"),
    };
    view.authority.state = null;
    if (!recording.runtime_frames.partial || Number.isInteger(event?.revision))
      view.replay.gaps = [
        ...(view.replay.gaps || []),
        boTranslate("No runtime snapshot recorded for this step; state has not been inferred."),
      ];
  }
  return true;
}
/** Index proven instances; duplicate legacy attempt IDs are ambiguous, not a match. */
export function runtimeConfigurations(machine) {
  const result = new Map();
  for (const cfg of machine.configurations || []) {
    const key = cfg.snapshot_instance
      ? `instance:${cfg.snapshot_instance}`
      : cfg.attempt
        ? `attempt:${cfg.attempt}`
        : null;
    if (key) result.set(key, result.has(key) ? null : cfg);
  }
  return result;
}
/** Retain last witnessed configurations when an exact frame covers one instance. */
export function rememberRuntimeMachine(before, after) {
  const configurations = new Map([
    ...runtimeConfigurations(before),
    ...runtimeConfigurations(after),
  ]);
  return {
    ...after,
    configurations: [...configurations.values()].filter(Boolean),
  };
}
/** Compare only the same known instance; never invent a prior state for a new one. */
export function runtimeChanges(before, after, owner, put) {
  const previous = runtimeConfigurations(before);
  for (const [key, cfg] of runtimeConfigurations(after)) {
    const old = previous.get(key);
    if (!cfg || !old) continue;
    put(owner, boTranslate("Flow"), old.phase, cfg.phase, "business", null, cfg.attempt);
    for (const [node, value] of Object.entries(cfg.activities || {}))
      put(node, boTranslate("Activity"), old.activities?.[node], value, "state", null, cfg.attempt);
  }
  // Global resources have a single node identity, never one copy per attempt.
  for (const node of new Set([
    ...Object.keys(before.shared_resources || {}),
    ...Object.keys(after.shared_resources || {}),
  ])) {
    const old = before.shared_resources?.[node],
      next = after.shared_resources?.[node];
    for (const field of new Set([...Object.keys(old || {}), ...Object.keys(next || {})]))
      put(node, field, old?.[field], next?.[field], "resource", null, null);
  }
}
