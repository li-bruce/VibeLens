/** Readable definitions for a selected node, independent of either renderer.
 * Only declared transitions, dependencies and mappings appear here. The detail
 * panel never turns a shared implementation into semantic equivalence or flow.
 */
import { t } from "./i18n.js";
import { machineParents } from "./machine-projection.js";

const list = (value) => (value == null ? [] : Array.isArray(value) ? value : [value]);
const text = (value) => (typeof value === "string" ? value : JSON.stringify(value));

export function nodeFacts(node, view, all, edges = []) {
  const facts = [],
    definition = node.concept_definition || {},
    name = (id) => all.get(id)?.label || id,
    add = (label, values) => {
      const items = [
        ...new Set(
          list(values)
            .filter((v) => v != null && v !== "")
            .map(text),
        ),
      ];
      if (items.length) facts.push({ label: t(label), values: items });
    },
    attached = edges.filter((edge) => edge.from === node.id || edge.to === node.id),
    targets = (types, incoming = false, businessOnly = false) =>
      attached
        .filter((e) => {
          if (!types.includes(e.type) || (incoming ? e.to : e.from) !== node.id) return false;
          if (!businessOnly) return true;
          const neighbor = all.get(incoming ? e.from : e.to);
          // Native call edges may also use the generic "flow" type. They are
          // implementation dependencies, not the next user-facing operation.
          return (
            (neighbor?.concept_layer || neighbor?.layer) === "business" &&
            (!node.concept_kind || e.origin === "concept-design")
          );
        })
        .map((e) => name(incoming ? e.from : e.to));
  add("Meaning", definition.meaning || node.documentation?.summary);
  if (node.concept_kind === "state_model") {
    add("Object", definition.subject?.object);
    add("Identity", definition.subject?.identity);
    add("Initial state", definition.initial);
    add(
      "States",
      list(definition.members?.states).map((s) => s.name || s),
    );
    add("Events", definition.members?.events);
  }
  if (node.kind === "state" && node.value !== undefined) {
    add("State value", node.value);
    const conceptual = node.origin === "concept-design";
    const ancestors = new Set(),
      parents = machineParents(view.model.machine || {});
    for (let value = node.value; value != null && !ancestors.has(value); value = parents.get(value))
      ancestors.add(value);
    const transitions = conceptual
      ? attached
          .filter((e) => e.from === node.id && e.type === "transition")
          .map((e) => ({
            trigger: e.trigger || e.label,
            dest: name(e.to),
            conditions: e.conditions,
            unless: e.unless,
          }))
      : (view.model.machine?.transitions || []).filter((tr) =>
          list(tr.source).some((s) => s === "*" || ancestors.has(s)),
        );
    add(
      "Transitions",
      transitions.map((tr) => {
        const guard = [...list(tr.conditions), ...list(tr.unless).map((g) => "¬" + g)].join(" ∧ ");
        return `${tr.trigger} → ${tr.dest ?? node.value}${guard ? " · " + guard : ""}`;
      }),
    );
  }
  if (node.concept_kind === "transition") {
    add("From", definition.source);
    add("Event", definition.trigger);
    add("To", definition.dest);
    add("Requires true", definition.conditions);
    add("Requires false", definition.unless);
    add("Effects", definition.effects);
  }
  if (node.concept_kind?.startsWith("rule_") || node.concept_kind === "guard") {
    add("Operator", { all: "AND", any: "OR", not: "NOT" }[definition.op] || definition.op);
    add("Inputs", targets(["guard", "data"], true));
    add(
      "Arguments",
      definition.arguments &&
        Object.entries(definition.arguments).map(([k, v]) => `${k}: ${name("policy:" + v)}`),
    );
    add("Reads", targets(["decision_reads_fact", "reads_state"]));
    add(
      "Used by",
      targets(["requires_decision", "guard_resolves_decision", "transition_guarded_by"], true),
    );
  }
  add("Value type", definition.input_type || definition.type || node.value_type);
  add("Read timing", definition.read_basis?.timing);
  if (node.layer === "business" || node.concept_layer === "business") {
    add("Previous", targets(["flow", "event", "retry", "cancel"], true, true));
    add("Next", targets(["flow", "event", "retry", "cancel"], false, true));
    add("Triggers", targets(["action_requests_event"]));
    add("Requires", targets(["requires_decision"]));
  }
  add(
    "Implemented by",
    attached
      .filter((e) => e.from === node.id && e.mapping_role === "implements")
      .map((e) => name(e.to)),
  );
  if (node.source?.path)
    add("Source", `${node.source.path}${node.source.symbol ? " · " + node.source.symbol : ""}`);
  if (node.capture) {
    add(
      "Input fields",
      Object.entries(node.capture.in || {}).map(([k, v]) => `${k}: ${text(v)}`),
    );
    add(
      "Output fields",
      Object.entries(node.capture.out || {}).map(([k, v]) => `${k}: ${text(v)}`),
    );
  }
  return facts;
}

/** Keep runtime feedback beside definitions without repeating canvas captions. */
export function detailRows(node, rows, facts) {
  const shown = new Set([node.label, ...facts.flatMap((fact) => fact.values)]);
  return rows.filter((row) => {
    if (!row.text || row.definition || shown.has(row.text)) return false;
    shown.add(row.text);
    return true;
  });
}

/** Safe DOM rendering keeps large definitions scrollable and off the canvas. */
export function nodeFactsElement(node, view, all, edges, document = globalThis.document) {
  const facts = nodeFacts(node, view, all, edges);
  if (!facts.length) return null;
  const result = document.createElement("dl");
  result.className = "node-facts";
  for (const fact of facts) {
    const label = document.createElement("dt"),
      value = document.createElement("dd");
    label.textContent = fact.label;
    value.textContent = fact.values.join("\n");
    result.append(label, value);
  }
  return result;
}
