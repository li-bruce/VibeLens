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

/** Match a witnessed configuration without equating unrelated caller labels. */
export function configurationScopeMatches(event, scope) {
  if (scope?.startsWith("instance:")) return scope === "instance:" + event.snapshot_instance;
  return scope === "attempt:" + event.attempt || scope === event.attempt;
}

const spanCaches = new WeakMap();

/** Resolve only recorded OTel Span Links, retaining their typed relation. */
export function spanLinkEvents(event, events) {
  let cached = spanCaches.get(events);
  const signature = `${events.length}:${events.at(-1)?.id || ""}`;
  if (!cached || cached.signature !== signature) {
    const bySpan = new Map();
    for (const item of events)
      if (item.phase === "enter" && item.trace) {
        const key = `${item.trace.trace_id}:${item.trace.span_id}`;
        if (!bySpan.has(key)) bySpan.set(key, item);
      }
    cached = { signature, bySpan };
    spanCaches.set(events, cached);
  }
  return (event?.trace?.links || []).flatMap((link) => {
    const source = cached.bySpan.get(`${link.trace_id}:${link.span_id}`);
    return source ? [{ event: source, type: link.relation || "trigger" }] : [];
  });
}

/** An explicit entry ID can cross entity identities; a reused call ID cannot. */
export function referencedParent(event, byId) {
  const parent = event?.parent_event_id && byId.get(event.parent_event_id);
  if (!parent || parent.id === event.id || parent.phase !== "enter") return null;
  if (
    ["project_id", "build_id", "model_revision"].some(
      (key) => (parent[key] || "") !== (event[key] || ""),
    )
  )
    return null;
  if (event.parent_call_id && parent.call_id !== event.parent_call_id) return null;
  return parent;
}

/** Pick the latest preceding entry in the same producer/entity invocation scope.
 * An ID in another worker or entity does not establish a parent call.
 */
export function parentEvent(event, events) {
  if (!event) return null;
  const scope = callScope(event),
    at = events.findIndex((item) => item.id === event.id);
  if (event.parent_event_id) {
    // Scan once without copying the recording on every animated observation.
    const closed = new Set();
    for (let i = (at < 0 ? events.length : at) - 1; i >= 0; i--) {
      const item = events[i];
      if (item.id === event.parent_event_id) {
        const parent = referencedParent(event, new Map([[item.id, item]]));
        if (!parent) return null;
        if (!closed.has(callKey(parent)) || event.phase === "enter") return parent;
        // An explicit asynchronous child retains its causal parent after that
        // parent ends. A bare point still cannot borrow the ended lifetime.
        for (let j = i + 1; j < (at < 0 ? events.length : at); j++)
          if (events[j].phase === "enter" && callKey(events[j]) === callKey(event)) return parent;
        return null;
      }
      if (["return", "error"].includes(item.phase)) closed.add(callKey(item));
    }
    return null;
  }
  let parentId = event.parent_call_id;
  if (!parentId && ["return", "error"].includes(event.phase)) {
    // Producers may declare parentage at entry only. The completion must still
    // match that exact invocation, not another node with a reused call ID.
    for (let i = (at < 0 ? events.length : at) - 1; i >= 0; i--) {
      const item = events[i];
      if (callKey(item) !== callKey(event)) continue;
      if (["return", "error"].includes(item.phase)) break;
      if (item.phase === "enter") {
        if (item.parent_event_id) return parentEvent(item, events);
        parentId = item.parent_call_id;
        break;
      }
    }
  }
  if (!parentId) return null;
  for (let i = (at < 0 ? events.length : at) - 1; i >= 0; i--) {
    const item = events[i];
    if (
      ["return", "error"].includes(item.phase) &&
      item.call_id === parentId &&
      callScope(item) === scope
    )
      return null;
    if (item.phase === "enter" && item.call_id === parentId && callScope(item) === scope)
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
