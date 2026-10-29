import { t } from "./i18n.js";

/** Captures are named event fields, not necessarily source variables or returns. */
export function captureFields(owner) {
  const nodes = [],
    edges = [];
  const database = ["query", "transform"].includes(owner.data_role);
  const primary = new Set(["parameters", "before", "result", "status", "committed"]);
  function add(direction, field, spec, path = [], parent = owner.id, advanced = false) {
    const id =
      `field:${owner.id}:${direction}:${field}` +
      path.map((key) => ":" + encodeURIComponent(key)).join("");
    const record = spec && typeof spec === "object" && !Array.isArray(spec);
    const diagnostic =
      advanced ||
      owner.capture_metadata?.[direction]?.includes(field) ||
      (database && (!primary.has(field) || (record && !Object.keys(spec).length)));
    nodes.push({
      id,
      label: path.at(-1) || field,
      kind: "data",
      layer: "parameter",
      parent,
      field,
      field_path: path,
      fieldType: spec,
      direction,
      event_node: owner.event_node || owner.id,
      origin: "capture-field",
      capture_role: diagnostic ? "diagnostic" : "value",
      capture_owner_role: owner.data_role,
      ...(owner.policy_node ? { capture_owner_policy: owner.policy_node } : {}),
      ...(diagnostic ? { analysis_level: "advanced" } : {}),
      summary: t(direction === "in" ? "Recorded input" : "Recorded output"),
    });
    edges.push({
      id: `capture:${id}`,
      from: direction === "in" ? id : parent,
      to: direction === "in" ? parent : id,
      type: "data",
      label: t(path.length ? "Field" : direction === "in" ? "Recorded input" : "Recorded output"),
      origin: "capture-field",
    });
    if (record)
      for (const [key, child] of Object.entries(spec))
        add(direction, field, child, [...path, key], id, diagnostic);
  }
  for (const [direction, fields] of Object.entries(owner.capture || {}))
    for (const [field, spec] of Object.entries(fields)) {
      // Older declarations listed transaction-only outcomes on every query.
      // Keep those historic files readable without presenting nonexistent values.
      if (
        database &&
        field === "committed" &&
        owner.data_metadata?.action &&
        owner.data_metadata.action !== "transaction"
      )
        continue;
      add(direction, field, spec);
    }
  return { nodes, edges };
}

export function capturedValue(node, values) {
  let value = values;
  for (const key of [node.field, ...(node.field_path || [])]) {
    if (!value || typeof value !== "object" || !Object.hasOwn(value, key))
      return { present: false, value: undefined };
    value = value[key];
  }
  return { present: true, value };
}

/** Describe provenance from stored facts; do not invent business explanations. */
export function nodeExplanation(node, all) {
  if (node.field) {
    const owner = all.get(node.event_node),
      path = [
        node.direction === "in" ? "inputs" : "outputs",
        node.field,
        ...(node.field_path || []),
      ].join(".");
    return [
      t("Recorded field: {0}", path),
      t("Collected during: {0}", owner?.label || node.event_node),
      t("Source context: collection owner. This event field has no declared source symbol."),
      ...(node.capture_role === "diagnostic" ? [t("Collection metadata")] : []),
    ];
  }
  const result = [];
  if (node.machine_state) result.push(t("Executable state: {0}", node.value));
  if (["query", "transform"].includes(node.data_role))
    result.push(t("Data operation · {0}", node.data_metadata?.action || node.data_role));
  if (node.summary) result.push(node.summary);
  if (node.code_role) result.push(t("Static source declaration"));
  if (node.source?.symbol) result.push(`${node.source.path} · ${node.source.symbol}`);
  if (node.parent) result.push(t("Within: {0}", all.get(node.parent)?.label || node.parent));
  return result;
}
