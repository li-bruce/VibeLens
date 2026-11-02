/** Carry witnessed open scopes across the observation boundary without replaying
 * pre-recording operations. Raw interval event IDs and ordinals remain unchanged.
 */
import { traceLifecycles } from "./trace-lifecycles.js";

export function contextualLifecycles(recording, items, all) {
  const ids = new Set(items.map((item) => item.id));
  const history = (recording.context.events || [])
    .filter((event) => !ids.has(event.id))
    .map((event) => ({ ...event, kind: "probe" }));
  if (!history.length) return { ...traceLifecycles(items, all), contextSources: [] };
  const offset = history.length,
    combined = [...history, ...items];
  const facts = traceLifecycles(combined, all);
  const sources = new Map();
  const ordinal = (raw) => Math.max(0, raw - offset);
  const slices = facts.slices
    .filter((slice) => slice.last >= offset)
    .map((slice) => {
      const clipped = slice.raw < offset;
      if (clipped) sources.set(combined[slice.raw].id, combined[slice.raw]);
      const before = slice.stages.filter((stage) => stage.raw < offset).at(-1);
      return {
        ...slice,
        raw: ordinal(slice.raw),
        last: ordinal(slice.last),
        observed: ordinal(slice.observed),
        parent: slice.parent === undefined ? undefined : ordinal(slice.parent),
        attempt: combined[slice.raw].attempt,
        ...(clipped ? { clippedStart: true, context_entry: combined[slice.raw] } : {}),
        stages: [
          ...(clipped && before ? [{ ...before, raw: 0 }] : []),
          ...slice.stages
            .filter((stage) => stage.raw >= offset)
            .map((stage) => ({ ...stage, raw: ordinal(stage.raw) })),
        ],
      };
    });
  const links = facts.links
    .filter((link) => (link.at ?? link.to) >= offset)
    .map((link) => {
      const extra = {};
      for (const end of ["from", "to"])
        if (link[end] < offset) {
          const original = combined[link[end]];
          sources.set(original.id, original);
          extra[end + "Node"] = original.node;
          extra[end + "Event"] = original.id;
        }
      return {
        ...link,
        ...extra,
        from: ordinal(link.from),
        to: ordinal(link.to),
        ...(link.at !== undefined ? { at: ordinal(link.at) } : {}),
        ...(link.invocation !== undefined ? { invocation: ordinal(link.invocation) } : {}),
      };
    });
  return { slices, links, contextSources: [...sources.values()] };
}
