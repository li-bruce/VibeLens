/** Inspect a confirmed definition without adding its fields to the canvas.
 * JSON preserves payload types, guard order and read timing exactly. textContent
 * is intentional: user-authored model text must never become executable markup.
 */
import { t } from "./i18n.js";

export function conceptDefinitionElement(
  node,
  { document = globalThis.document, open = false, onToggle = () => {} } = {},
) {
  if (!node.concept_definition || typeof node.concept_definition !== "object") return null;
  const details = document.createElement("details"),
    summary = document.createElement("summary"),
    code = document.createElement("pre");
  details.className = "concept-definition";
  details.dataset.nodeId = node.id;
  details.open = open;
  summary.textContent = t("Model definition");
  code.textContent = JSON.stringify(node.concept_definition, null, 2);
  code.tabIndex = 0;
  details.append(summary, code);
  details.addEventListener("toggle", () => onToggle(details.open));
  return details;
}
