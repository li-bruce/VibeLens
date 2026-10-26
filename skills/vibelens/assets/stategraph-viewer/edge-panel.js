/** Render original relation choices and their evidence without mutating graph facts. */
import { relationStyle, displayName, edgePorts } from "./layout.js";
import { dataRelationEvidence } from "./data-layer.js";
import { t as boTranslate } from "./i18n.js";

/** Runtime and static evidence remain distinct in the same relation list. */
function relationEvidence(member) {
  const dataEvidence = dataRelationEvidence(member);
  if (dataEvidence) return dataEvidence;
  if (["python-ast", "source-ast"].includes(member.origin)) return boTranslate("Static call");
  if (!member.observed) return boTranslate("Declared relation");
  return boTranslate(member.current ? "Observed in this run" : "Observed in a previous run");
}

export function renderEdgeDetail({
  graph,
  displayGraph,
  preferences,
  edges,
  selected,
  choices,
  screen,
  scale,
  pan,
  onChoose,
  onHide,
  element = (id) => document.getElementById(id),
}) {
  const $ = element;
  const panel = $("edge-details"),
    edge = edges.find((e) => e.id === selected);
  if (!edge) {
    panel.hidden = true;
    return false;
  }
  const style = relationStyle(edge);
  $("edge-title").textContent = boTranslate(
    "{0} \u00B7 {1} relations",
    style.label,
    edge.members.length,
  );
  $("edge-members").replaceChildren(
    ...choices
      .filter((choice) => choice.id !== edge.id)
      .map((choice) => {
        const item = document.createElement("li"),
          button = document.createElement("button");
        const a = graph.all.get(choice.from),
          b = graph.all.get(choice.to);
        button.textContent = `${a ? displayName(a, preferences) : choice.from} → ${b ? displayName(b, preferences) : choice.to}`;
        button.onclick = () => onChoose({ ...choice, alternatives: choices });
        item.append(button);
        return item;
      }),
    ...edge.members.map((member) => {
      const item = document.createElement("li"),
        a = graph.all.get(member.from),
        b = graph.all.get(member.to);
      item.textContent = `${a ? displayName(a, preferences) : member.from} → ${b ? displayName(b, preferences) : member.to}：${member.label || style.label}（${relationEvidence(member)}）`;
      const hide = document.createElement("button");
      hide.textContent = boTranslate("Hide relation");
      hide.onclick = () => {
        onHide(member.id);
      };
      item.append(hide);
      return item;
    }),
  );
  const ports = edgePorts(displayGraph || graph, edge);
  panel.hidden = false;
  panel.style.left =
    Math.max(
      12,
      Math.min(
        screen.width - panel.offsetWidth - 12,
        ((ports.start.x + ports.end.x) / 2) * scale + pan.x,
      ),
    ) + "px";
  panel.style.top =
    Math.max(
      45,
      Math.min(
        screen.height - panel.offsetHeight - 12,
        ((ports.start.y + ports.end.y) / 2) * scale + pan.y,
      ),
    ) + "px";
  return true;
}
