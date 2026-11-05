/** Present recorded changes; selecting a row only locates its existing graph owner. */
import { boDisplayValue, boKinds } from "./replay-steps.js";
import { eventLabel } from "./recording.js";
import { t as boTranslate } from "./i18n.js";
import { enableChangePanelDrag } from "./change-panel-position.js";

const panels = new WeakMap();
const previewLimit = 2;

/** Prefer changed state/decisions in the preview; retain every row in the detail list. */
export function previewChangeIndices(rows, limit = previewLimit) {
  const priority = { business: 0, state: 1, decision: 2, resource: 3, value: 4, call: 5 };
  return new Set(
    rows
      .map((row, index) => ({ index, rank: priority[row.kind] ?? 6 }))
      .sort((a, b) => a.rank - b.rank || a.index - b.index)
      .slice(0, limit)
      .map((item) => item.index),
  );
}

/** Keep disclosure choices stable as live events replace the displayed values. */
function panelControls(panel, $) {
  if (panels.has(panel)) return panels.get(panel);
  const state = { expanded: false, collapsed: false, rows: [] };
  state.refresh = () => {
    const preview = previewChangeIndices(state.rows);
    const remaining = Math.max(0, state.rows.length - preview.size);
    panel.dataset.expanded = String(state.expanded);
    panel.dataset.collapsed = String(state.collapsed);
    $("change-content").hidden = state.collapsed;
    $("change-expand").hidden = !remaining || state.collapsed;
    $("change-expand").textContent = state.expanded ? "−" : `+${remaining}`;
    const expansionLabel = boTranslate(state.expanded ? "Show fewer changes" : "Show all changes");
    $("change-expand").title = expansionLabel;
    $("change-expand").setAttribute("aria-label", expansionLabel);
    $("change-expand").setAttribute("aria-expanded", String(state.expanded));
    $("change-collapse").textContent = state.collapsed ? "+" : "−";
    const collapseLabel = boTranslate(
      state.collapsed ? "Show current changes" : "Minimize changes",
    );
    $("change-collapse").title = collapseLabel;
    $("change-collapse").setAttribute("aria-label", collapseLabel);
    $("change-collapse").setAttribute("aria-expanded", String(!state.collapsed));
    [...$("change-rows").children].forEach((line, index) => {
      line.hidden = !state.expanded && !preview.has(index);
    });
  };
  $("change-expand").onclick = () => {
    state.expanded = !state.expanded;
    state.refresh();
  };
  $("change-collapse").onclick = () => {
    state.collapsed = !state.collapsed;
    state.refresh();
  };
  enableChangePanelDrag(panel, panel.querySelector(".change-heading"));
  panels.set(panel, state);
  return state;
}

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
  const controls = panelControls(panel, $);
  $("change-title").textContent =
    boDetail.event.kind === "start"
      ? boTranslate("Recording started")
      : boDetail.event.kind === "end"
        ? boTranslate("Recording stopped")
        : eventLabel(boDetail.event, model);
  $("change-title").title = $("change-title").textContent;
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
      value.title = `${row.field}: ${boText(row.before, row)} → ${boText(row.after, row)}`;
      value.append(document.createTextNode(row.field + ": "));
      const before = document.createElement("del"),
        after = document.createElement("ins");
      before.textContent = boText(row.before, row);
      after.textContent = boText(row.after, row);
      // The first observed value has no known predecessor. Keep that distinction
      // without repeating "Not recorded" before every initial field.
      const previous = document.createElement("span");
      previous.className = "change-before";
      previous.dataset.unknown = String(row.before === undefined);
      previous.append(before, document.createTextNode(" → "));
      value.append(previous, after);
      line.append(kind, node, value);
      return line;
    }),
  );
  controls.rows = boDetail.rows;
  controls.refresh();
  for (const button of $("semantic").children) {
    const rows = boDetail.rows.filter((r) =>
      (r.owners || [r.owner]).includes(button.dataset.nodeId),
    );
    button.dataset.changes = JSON.stringify(
      rows.map((r) => ({ field: r.field, before: r.before, after: r.after, kind: r.kind })),
    );
  }
}
