/** Resolve registered observation meanings without interpreting business outcomes.
 * The model validator rejects dangling states, uncaptured fields and overlapping
 * selectors. Original events and values remain untouched by this display layer.
 */
const generic = {
  enter: { boundary: "start", state: "running", label: "Running", kind: "active" },
  wait: { boundary: "update", state: "waiting", label: "Waiting", kind: "waiting" },
  read: { boundary: "update", state: "running", label: "Running", kind: "active" },
  return: { boundary: "end", state: "returned", label: "Returned", kind: "ended" },
  error: { boundary: "end", state: "exception", label: "Exception exit", kind: "ended" },
};

/** Display names are overlays; source mode exposes the registered state identity. */
export function lifecycleCaption(state, sourceNames = false) {
  return sourceNames && state?.registered ? state.state : state?.label;
}

export function lifecycleTransition(node, event) {
  if (event.context_only && ["start", "end"].includes(event.context_boundary)) {
    const ended = event.context_boundary === "end";
    return {
      boundary: event.context_boundary,
      state: ended ? (event.phase === "error" ? "exception" : "returned") : "running",
      label: ended ? (event.phase === "error" ? "Exception exit" : "Ended") : "Running",
      kind: ended ? "ended" : "active",
      registered: false,
      context_only: true,
      ...(ended ? { termination: "boundary" } : {}),
    };
  }
  const definition = node?.lifecycle;
  const binding = definition?.bindings.find((item) => {
    if (item.phase !== event.phase) return false;
    if (!item.when) return true;
    const { direction, field, equals } = item.when;
    const values = direction === "in" ? event.inputs : event.outputs;
    return Object.hasOwn(values || {}, field) && values[field] === equals;
  });
  const termination =
    event.phase === "error" ? "exception" : event.phase === "return" ? "return" : "declared";
  if (binding) {
    const state = definition.states.find((item) => item.id === binding.state);
    return {
      ...state,
      state: state.id,
      boundary: binding.boundary,
      registered: true,
      ...(binding.boundary === "end" ? { termination } : {}),
    };
  }
  // Compatibility for data recordings made before the projector registered
  // adapter lifetimes. Only the native adapter's exact action/status can end it.
  const dataExit =
    !definition &&
    ((node?.data_role === "query" &&
      node.data_metadata?.action === "transaction" &&
      event.phase === "commit" &&
      event.outputs?.status === "committed") ||
      (node?.data_role === "transform" &&
        event.phase === "change" &&
        event.outputs?.status === "transformed"));
  if (dataExit)
    return {
      boundary: "end",
      state: event.outputs.status,
      label: event.phase === "commit" ? "Committed" : "Transformed",
      kind: "ended",
      registered: false,
      termination: event.phase,
    };
  const fallback = generic[event.phase];
  return fallback
    ? { ...fallback, registered: false, ...(fallback.boundary === "end" ? { termination } : {}) }
    : null;
}

/** A legacy commit is an observed boundary, not proof of a successful return. */
export function lifecycleBoundary(node, event) {
  return (
    lifecycleTransition(node, event) || {
      boundary: "end",
      state: "boundary",
      label: "Observed boundary",
      kind: "ended",
      registered: false,
      termination: event.phase,
    }
  );
}
