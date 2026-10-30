/** Invocation identity shared by timeline slices and graph call animations. */
export function callScope(event) {
  return JSON.stringify([
    event.build_id || "",
    event.run_id || "",
    event.producer_id || "",
    event.stream_id || "",
    event.entity || "",
    event.attempt || "",
  ]);
}

export function callKey(event) {
  return event.call_id ? JSON.stringify([callScope(event), event.node, event.call_id]) : null;
}

/** Pick the latest preceding entry in the same producer/entity invocation scope.
 * An ID in another worker or entity does not establish a parent call.
 */
export function parentEvent(event, events) {
  if (!event?.parent_call_id) return null;
  const scope = callScope(event),
    at = events.findIndex((item) => item.id === event.id);
  for (let i = (at < 0 ? events.length : at) - 1; i >= 0; i--) {
    const item = events[i];
    if (
      ["return", "error"].includes(item.phase) &&
      item.call_id === event.parent_call_id &&
      callScope(item) === scope
    )
      return null;
    if (
      item.phase === "enter" &&
      item.call_id === event.parent_call_id &&
      callScope(item) === scope
    )
      return item;
  }
  return null;
}

/** Preserve sub-millisecond ISO fractions instead of silently rounding short calls to zero. */
export function traceTime(value) {
  if (typeof value !== "string" || !/(Z|[+-]\d{2}:\d{2})$/i.test(value)) return null;
  const parsed = Date.parse(value);
  if (!Number.isFinite(parsed)) return null;
  const fraction = value.match(/\.(\d+)(?:Z|[+-]\d{2}:\d{2})$/i)?.[1] || "";
  return parsed + (fraction.length > 3 ? Number("0." + fraction.slice(3)) : 0);
}
