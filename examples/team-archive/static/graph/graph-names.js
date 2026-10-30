/** Presentation-only names. Source identifiers and recorded facts remain unchanged.
 * AI authors concise labels during graph maintenance, never during a render.
 */
import { locale } from "./i18n.js";
const originals = new WeakMap();

export function explainedName(value) {
  if (typeof value === "string") return value.trim();
  return value?.[locale()] || value?.en || "";
}

/** Prefer lexical names, then native schema names, then the graph identity.
 * Captured JSON fields are not the function which collected them.
 */
export function sourceName(node, binding) {
  if (node.field) return node.field_path?.at(-1) || node.field;
  if (node.kind === "state" && node.value !== undefined) return String(node.value);
  if (node.code_role === "endpoint")
    return node.api
      ? [...(node.api.methods || []), node.api.path].filter(Boolean).join(" ")
      : node.authored_label || node.label || node.id;
  if (node.code_role === "parameter") return node.authored_label || node.label || node.id;
  if (node.project_path) return node.project_path;
  if (["store", "dataset", "column"].includes(node.data_role))
    return node.data_key === "store" ? node.data_store : node.data_key || node.id;
  return binding?.selection?.symbol || node.source?.symbol || binding?.symbol || node.id;
}

export function nameNode(node, model, bindings = {}) {
  const source = sourceName(node, bindings[node.referenceOf || node.id]),
    authored = node.authored_label ?? node.label,
    explained =
      (node.kind === "state"
        ? explainedName(model.presentation?.names?.states?.[node.value])
        : "") ||
      explainedName(model.presentation?.names?.nodes?.[node.referenceOf || node.id]) ||
      authored ||
      source;
  return {
    ...node,
    authored_label: authored,
    source_name: source,
    explained_name: explained,
    label: model.presentation?.name_mode === "source" ? source : explained,
  };
}

/** Clone display fields only. This is never written back to a model or recording. */
export function namedView(view, explained = true) {
  const original = originals.get(view.model) || view.model,
    mode = explained ? "explained" : "source",
    names = original.presentation?.names || {},
    model = { ...original, presentation: { ...original.presentation, name_mode: mode } };
  model.nodes = original.nodes.map((node) => nameNode(node, model, view.manifest?.bindings));
  model.edges = original.edges.map((edge) => ({
    ...edge,
    authored_label: edge.authored_label ?? edge.label,
    label: explained
      ? explainedName(names.edges?.[edge.id]) || edge.authored_label || edge.label || edge.type
      : edge.event || edge.code_relation || edge.data_relation || edge.type,
  }));
  const chart = original.machine;
  model.machine = {
    ...chart,
    labels: Object.fromEntries(
      (chart.values || []).map((value) => [
        value,
        explained ? explainedName(names.states?.[value]) || chart.labels?.[value] || value : value,
      ]),
    ),
    event_labels: Object.fromEntries(
      Object.keys(chart.events || {}).map((event) => [
        event,
        explained
          ? explainedName(names.events?.[event]) || chart.event_labels?.[event] || event
          : event,
      ]),
    ),
  };
  originals.set(model, original);
  return { ...view, model };
}
