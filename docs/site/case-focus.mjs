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
  // A business action contains its observed database operation. Keeping this
  // declared relation avoids presenting two disconnected parts of one action.
  "contains",
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
