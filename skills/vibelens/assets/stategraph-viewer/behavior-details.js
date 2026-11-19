/** On-demand behavior detail shared by 2D/3D and recorded contexts.
 * These are definitions and the last recorded verification, never inferred live
 * execution. Values are rendered as text; expressions remain available on demand.
 */
import { t } from "./i18n.js";

const text = (value) => (typeof value === "string" ? value : JSON.stringify(value));

export function behaviorRecords(node, view) {
  const context = view.behavior_context;
  if (context?.schema !== "bo-behavior-details/v1") return [];
  const ids = new Set(
    [node.id, node.concept_id, node.referenceOf, node.event_node].filter(Boolean),
  );
  const keys = new Set([...ids].flatMap((id) => context.nodes[id] || []));
  return [...keys]
    .map((key) => ({ key, record: context.records[key] }))
    .filter((item) => item.record);
}

export function behaviorDetailElement(
  node,
  view,
  { document = globalThis.document, open = new Set(), onToggle = () => {}, onHighlight } = {},
) {
  if (view.behavior_context?.status === "unavailable") {
    const message = document.createElement("p");
    message.className = "behavior-details";
    message.textContent = t("Behavior details unavailable") + ": " + view.behavior_context.error;
    return message;
  }
  const entries = behaviorRecords(node, view);
  if (!entries.length) return null;
  const root = document.createElement("section"),
    title = document.createElement("h4");
  root.className = "behavior-details";
  root.dataset.definition = view.behavior_context.definition_sha256;
  title.textContent = t("Behavior details");
  root.append(title);
  const row = (label, value, parent = root) => {
    if (value == null || (Array.isArray(value) && !value.length)) return;
    const line = document.createElement("p"),
      name = document.createElement("strong");
    name.textContent = t(label) + ": ";
    line.append(
      name,
      document.createTextNode(Array.isArray(value) ? value.map(text).join(" · ") : text(value)),
    );
    parent.append(line);
  };
  for (const { key, record } of entries) {
    const detail = document.createElement("details"),
      summary = document.createElement("summary");
    detail.dataset.behaviorId = key;
    detail.open = open.has(key);
    detail.addEventListener("toggle", () => onToggle(key, detail.open));
    const kind = key.split("/")[0];
    summary.textContent = `${t({ variable: "Value", action: "Action", property: "Property", interaction: "Interaction" }[kind])} · ${record.label || record.id}`;
    detail.append(summary);
    if (onHighlight) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = t("Highlight dependencies");
      button.addEventListener("click", () =>
        onHighlight(
          Object.entries(view.behavior_context.nodes)
            .filter(([, keys]) => keys.includes(key))
            .map(([id]) => id),
        ),
      );
      detail.append(button);
    }
    row("Meaning", record.meaning || record.completion?.meaning, detail);
    row(
      "Possible values",
      record.domain?.values ||
        (record.domain?.type === "boolean" ? [false, true] : record.domain?.type),
      detail,
    );
    row(
      "Changes",
      record.transition
        ? `${text(record.transition.source)} → ${text(record.transition.dest)}`
        : record.writes,
      detail,
    );
    row("Completion", record.completion?.kind, detail);
    row("Reads", record.reads, detail);
    row("Unchanged", record.unchanged, detail);
    row("Properties", record.properties, detail);
    row("Binding", record.binding ? t("Declared") : t("Not bound"), detail);
    const specification = document.createElement("details"),
      heading = document.createElement("summary"),
      code = document.createElement("pre");
    heading.textContent = t("Definition and bindings");
    specification.open = open.has(key + "/definition");
    specification.addEventListener("toggle", () =>
      onToggle(key + "/definition", specification.open),
    );
    code.textContent = JSON.stringify(record, null, 2);
    code.tabIndex = 0;
    specification.append(heading, code);
    detail.append(specification);
    root.append(detail);
  }
  row("Unresolved", view.behavior_context.unresolved);
  row("Outside scope", view.behavior_context.exclusions);
  const checked = view.behavior_context.last_verification;
  if (checked?.checked_at) {
    row("Last verification", checked.checked_at);
    row("Checked candidate", checked.candidate_id);
    for (const [key, value] of Object.entries(checked.categories || {})) row(key, t(value.status));
  } else row("Last verification", t("Not recorded"));
  return root;
}
