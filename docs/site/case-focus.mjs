/** Select stable identities from the exported story, never from display labels. */
export function focusIds({ inputs = true, effects = true, states = false } = {}, story) {
  return new Set([
    ...story.focus.core,
    ...(inputs ? story.focus.inputs : []),
    ...(effects ? story.focus.effects : []),
    ...(states ? story.states : []),
  ]);
}

export const focusTypes = [
  "business",
  "state",
  "decision",
  "data",
  "function",
  "query",
  "transform",
  "dataset",
  "code-file",
  "code-class",
  "code-function",
  "code-parameter",
  "code-endpoint",
];
export const focusRelations = [
  "call",
  "flow",
  "guard",
  "data",
  "transition",
  "reads",
  "writes",
  "transforms",
  "code-maps",
  "code-calls",
  "code-parameter",
  "code-defines",
  "code-handles",
];
