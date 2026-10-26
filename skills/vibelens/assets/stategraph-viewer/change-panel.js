/** Present recorded changes; selecting a row only locates its existing graph owner. */
import { boDisplayValue, boKinds } from "./replay-steps.js";
import { eventLabel } from "./recording.js";
import { t as boTranslate } from "./i18n.js";

export function renderStepChanges({
  detail,
  model,
  onLocate,
  element = (id) => document.getElementById(id),
}) {
  const $ = element,
    boDetail = detail,
    boText = (value, row) => boDisplayValue(value, model, row);
  const panel = $("step-changes");
  panel.hidden = !boDetail;
  if (!boDetail) return;
  $("change-title").textContent =
    boDetail.event.kind === "start"
      ? boTranslate("Recording started")
      : boDetail.event.kind === "end"
        ? boTranslate("Recording stopped")
        : eventLabel(boDetail.event, model);
  $("change-count").textContent = boDetail.rows.length
    ? boTranslate("{0} changes", boDetail.rows.length)
    : boTranslate("No visible value changes");
  const attempts = new Set(boDetail.rows.map((row) => row.attempt).filter(Boolean));
  $("change-rows").replaceChildren(
    ...boDetail.rows.map((row) => {
      const line = document.createElement("div");
      line.className = "change-row";
      line.dataset.eventId = row.event;
      line.dataset.owner = row.owner;
      line.dataset.owners = JSON.stringify(row.owners || [row.owner]);
      line.dataset.attempt = row.attempt || "";
      line.dataset.kind = row.kind;
      const kind = document.createElement("span");
      kind.className = "change-kind";
      kind.textContent = boKinds[row.kind].label;
      kind.style.color = "#" + boKinds[row.kind].color.toString(16).padStart(6, "0");
      const node = document.createElement("button");
      node.textContent =
        attempts.size > 1 && row.attempt ? `${row.sourceLabel} · ${row.attempt}` : row.sourceLabel;
      node.onclick = () => {
        onLocate(row.owner);
      };
      const value = document.createElement("span");
      value.className = "change-value";
      value.append(document.createTextNode(row.field + ": "));
      const before = document.createElement("del"),
        after = document.createElement("ins");
      before.textContent = boText(row.before, row);
      after.textContent = boText(row.after, row);
      value.append(before, document.createTextNode(" → "), after);
      line.append(kind, node, value);
      return line;
    }),
  );
  for (const button of $("semantic").children) {
    const rows = boDetail.rows.filter((r) =>
      (r.owners || [r.owner]).includes(button.dataset.nodeId),
    );
    button.dataset.changes = JSON.stringify(
      rows.map((r) => ({ field: r.field, before: r.before, after: r.after, kind: r.kind })),
    );
  }
}
