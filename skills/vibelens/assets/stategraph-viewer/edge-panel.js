/** Render original relation choices and their evidence without mutating graph facts. */
import { relationName, displayName, edgePorts } from "./layout.js";
import { dataRelationEvidence } from "./data-layer.js";
import { t as boTranslate } from "./i18n.js";
import { hasRelationId, originalRelations } from "./edge-identities.js";

/** Runtime and static evidence remain distinct in the same relation list. */
function relationEvidence(member) {
  if (member.derived) return boTranslate("Structural path; execution is not inferred");
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
  onReveal,
  onHide,
  element = (id) => document.getElementById(id),
}) {
  const $ = element;
  const panel = $("edge-details"),
    edge = edges.find((e) => hasRelationId(e, selected));
  if (!edge) {
    panel.hidden = true;
    return false;
  }
  $("edge-title").textContent = boTranslate(
    "{0} \u00B7 {1} relations",
    relationName(edge, preferences),
    (edge.members || [edge]).length,
  );
  if (edge.derived && edge.search_complete === false)
    $("edge-title").textContent += " · " + boTranslate("Path search incomplete");
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
    ...(edge.members || [edge]).map((member) => {
      const item = document.createElement("li"),
        a = graph.all.get(member.from),
        b = graph.all.get(member.to);
      item.textContent = `${a ? displayName(a, preferences) : member.from} → ${b ? displayName(b, preferences) : member.to}：${relationName(member, preferences)}（${relationEvidence(member)}）`;
      const definitions = originalRelations(member);
      if (definitions.length > 1) {
        const details = document.createElement("details"),
          summary = document.createElement("summary");
        summary.textContent = boTranslate("{0} definitions · one relation", definitions.length);
        details.append(summary);
        for (const definition of definitions) {
          const row = document.createElement("div"),
            identity = document.createElement("code");
          identity.textContent = definition.id;
          row.append(
            boTranslate(definition.origin === "concept-design" ? "Design" : "Implementation") +
              ": ",
            identity,
          );
          row.title = JSON.stringify(definition.source_refs || []);
          details.append(row);
        }
        item.append(details);
      } else if (!member.derived && edge.members?.length > 1) {
        // Parallel relations can share labels. Expose the original ID and any
        // call site/condition so the user can tell which assertion each row is.
        const identity = document.createElement("code");
        identity.textContent = member.id;
        const context = ["callsite", "conditions", "condition", "unless", "scope", "arguments"]
          .filter((key) => member[key] !== undefined)
          .map((key) => `${key}: ${JSON.stringify(member[key])}`)
          .join(" · ");
        item.append(" ", identity, context ? " · " + context : "");
      }
      if (member.witness) {
        const path = document.createElement("div");
        path.textContent = member.witness.nodes
          .map((id) => (graph.all.has(id) ? displayName(graph.all.get(id), preferences) : id))
          .join(" → ");
        const reveal = document.createElement("button");
        reveal.textContent = boTranslate("Reveal path");
        reveal.onclick = () => onReveal?.(member.witness);
        item.append(path, reveal);
      }
      const hide = document.createElement("button");
      hide.textContent = boTranslate("Hide relation");
      hide.onclick = () => {
        onHide(member.derived ? edge.id : member.id);
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
