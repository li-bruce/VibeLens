/** State occupancy is not a function call. Its interval follows witnessed state changes. */
import { activeMachineStates } from "./machine-projection.js";
import { runtimeFrame, runtimeConfigurations } from "./runtime-frames.js";
import { conceptActivityIds } from "./concept-observation.js";
export function stateResidencies(recording, items, changes, nodes, axis) {
  const states = [...nodes.values()].filter(
    (node) =>
      node.kind === "state" &&
      node.value !== undefined &&
      (node.origin !== "concept-design" || conceptActivityIds(node).length),
  );
  const opened = new Map(),
    slices = [],
    links = [];
  const values = (value) => (Array.isArray(value) ? value : value == null ? [] : [value]);
  const machine = recording.context.model?.machine;
  const active = (value) =>
    machine?.states && machine?.values ? [...activeMachineStates(machine, value)] : values(value);
  const enter = (value, raw, scope) => {
    for (const node of states.filter((node) => active(value).includes(node.value))) {
      const key = JSON.stringify([scope, node.id]);
      if (!opened.has(key))
        opened.set(key, { node: node.id, raw, scope, role: "residency", clippedStart: raw === 0 });
    }
  };
  const close = (slice, raw, unfinished) => ({
    ...slice,
    last: raw,
    start: axis.times[slice.raw],
    end: unfinished ? axis.total : axis.times[raw],
    unfinished,
    duration: !unfinished && axis.ordered ? axis.times[raw] - axis.times[slice.raw] : null,
  });
  const visit = (value, raw, scope) => {
    for (const [key, slice] of opened) {
      if (slice.scope !== scope && (recording.runtime_frames || slice.scope !== "application"))
        continue;
      const node = nodes.get(slice.node);
      if (!active(value).includes(node.value)) {
        for (const target of states.filter((candidate) => active(value).includes(candidate.value)))
          links.push({
            from: slice.raw,
            to: raw,
            at: raw,
            fromNode: node.id,
            toNode: target.id,
            type: "transition",
            scope,
          });
        slices.push(close(slice, raw, false));
        opened.delete(key);
      }
    }
    enter(value, raw, scope);
  };
  const initial = recording.context.machine || {};
  if (initial.configurations?.length) {
    for (const [scope, cfg] of runtimeConfigurations(initial)) if (cfg) enter(cfg.phase, 0, scope);
  } else enter(initial.current, 0, "application");
  if (recording.runtime_frames) {
    // Snapshots witness occupancy even before the first transition. A caller's
    // attempt is not a machine identity when multiple configurations share it.
    const legacy = runtimeConfigurations(recording.final?.machine || initial);
    for (const [raw, event] of items.entries()) {
      const frame = runtimeFrame(recording, event);
      if (!frame) continue;
      for (const [scope, cfg] of runtimeConfigurations(frame.machine))
        if (cfg && (cfg.snapshot_instance || legacy.get(scope))) visit(cfg.phase, raw, scope);
    }
  } else {
    for (const [raw, list] of changes.entries())
      for (const change of list || []) {
        if (change.kind !== "business") continue;
        visit(
          change.after,
          raw,
          change.instance || "attempt:" + (change.attempt || items[raw].attempt || "application"),
        );
      }
  }
  for (const slice of opened.values())
    slices.push(close(slice, Math.max(0, items.length - 1), true));
  return { slices, links };
}

/** Native activity frames establish execution/wait intervals even without function probes. */
export function activityResidencies(recording, items, changes, nodes, axis) {
  const opened = new Map(),
    slices = [];
  const active = (state) => ["running", "waiting"].includes(state);
  const close = (slice, raw, unfinished, failed = false) => ({
    ...slice,
    last: raw,
    start: axis.times[slice.raw],
    end: unfinished ? axis.total : axis.times[raw],
    unfinished,
    failed,
    duration: !unfinished && axis.ordered ? axis.times[raw] - axis.times[slice.raw] : null,
    stages: slice.stages.map((stage, i) => ({
      ...stage,
      start: axis.times[stage.raw],
      end:
        i + 1 < slice.stages.length
          ? axis.times[slice.stages[i + 1].raw]
          : unfinished
            ? axis.total
            : axis.times[raw],
    })),
  });
  const update = (node, phase, raw, scope) => {
    if (nodes.get(node)?.execution_role !== "activity") return;
    const key = JSON.stringify([scope, node]);
    let slice = opened.get(key);
    if (!slice && active(phase)) {
      slice = { node, raw, scope, role: "activity", clippedStart: raw === 0, stages: [] };
      opened.set(key, slice);
    }
    if (!slice) return;
    if (active(phase)) {
      const stage = phase === "waiting" ? "waiting" : "running";
      if (slice.stages.at(-1)?.phase !== stage) slice.stages.push({ raw, phase: stage });
    } else {
      slices.push(close(slice, raw, false, phase === "failed"));
      opened.delete(key);
    }
  };
  for (const [scope, cfg] of runtimeConfigurations(recording.context.machine || {}))
    if (cfg)
      for (const [node, value] of Object.entries(cfg.activities || {}))
        update(node, value, 0, scope);
  if (recording.runtime_frames) {
    for (const [raw, event] of items.entries()) {
      const frame = runtimeFrame(recording, event);
      if (frame)
        for (const [scope, cfg] of runtimeConfigurations(frame.machine))
          if (cfg)
            for (const [node, value] of Object.entries(cfg.activities || {}))
              update(node, value, raw, scope);
    }
  } else
    for (const [raw, list] of changes.entries())
      for (const change of list || [])
        if (change.kind === "state")
          update(
            change.node,
            change.after,
            raw,
            change.instance || "attempt:" + (change.attempt || items[raw].attempt || "application"),
          );
  for (const slice of opened.values())
    slices.push(close(slice, Math.max(0, items.length - 1), true));
  return slices;
}
