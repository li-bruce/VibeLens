/** Exact native graph identities selected for this demonstration's local views. */
export function focusIds({ versions = true, effects = true, states = false } = {}) {
  const ids = ["publish", "review-policy", "field:review-policy:out:verdict"];
  if (versions)
    ids.push("field:review-policy:in:reviewed_version", "field:review-policy:in:current_version");
  if (effects)
    ids.push(
      "choose-version",
      "field:choose-version:out:selected",
      "version-selection",
      "save-exhibition",
      "db:gallery:table%3Aexhibition",
    );
  if (states) ids.push("state.pending", "state.displayed");
  return new Set(ids);
}

export const focusTypes = ["state", "decision", "data", "query", "transform", "dataset"];
export const focusRelations = [
  "call",
  "flow",
  "guard",
  "data",
  "transition",
  "reads",
  "writes",
  "transforms",
  "maps",
];
