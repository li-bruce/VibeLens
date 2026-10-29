/** Compact confirmation diagram from the same selected business graph as Web. */
import { t, locale } from "./site-ui.mjs?rev=files-1";
const svgNS = "http://www.w3.org/2000/svg";
function element(tag, attributes = {}, text) {
  const node = document.createElementNS(svgNS, tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  if (text) node.textContent = text;
  return node;
}

export function proposedFlow(confirmed, artifact) {
  const model = artifact.view.model;
  const ids = new Set(artifact.story.business);
  const edges = model.edges.filter(
    (edge) => ids.has(edge.from) && ids.has(edge.to) && edge.type !== "contains",
  );
  const remaining = artifact.story.business.slice();
  const ordered = [];
  // Prefer predecessors before their dependents. A real cycle is retained and
  // drawn as an edge, rather than replaced with an invented linear workflow.
  while (remaining.length) {
    const ready = remaining.find(
      (id) => !edges.some((edge) => edge.to === id && remaining.includes(edge.from)),
    );
    ordered.push(...remaining.splice(ready ? remaining.indexOf(ready) : 0, 1));
  }
  const vertical = innerWidth < 700;
  const columns = vertical ? 1 : Math.min(4, ordered.length);
  const rows = Math.ceil(ordered.length / columns);
  const figure = document.createElement("figure");
  figure.className = "conversation-flow";
  figure.dataset.confirmed = String(confirmed);
  const caption = document.createElement("figcaption");
  caption.textContent = t(confirmed ? "case.flow.confirmed" : "case.flow.proposed");
  const svg = element("svg", {
    viewBox: `0 0 ${vertical ? 340 : 720} ${rows * 105 + 30}`,
    role: "img",
    "aria-label": caption.textContent,
  });
  const defs = element("defs");
  const marker = element("marker", {
    id: "intent-arrow",
    viewBox: "0 0 10 10",
    refX: 8,
    refY: 5,
    markerWidth: 5,
    markerHeight: 5,
    orient: "auto-start-reverse",
  });
  marker.append(element("path", { d: "M0 0L10 5L0 10Z", fill: "#8098b7" }));
  defs.append(marker);
  svg.append(defs);
  const positions = new Map(
    ordered.map((id, index) => [
      id,
      {
        x: vertical ? 40 : 85 + (index % columns) * 180,
        y: 45 + Math.floor(index / columns) * 105,
      },
    ]),
  );
  for (const edge of edges) {
    const a = positions.get(edge.from),
      b = positions.get(edge.to);
    const path = element("path", {
      d: vertical
        ? `M${a.x + 20},${a.y}C290,${a.y} 290,${b.y} ${b.x + 20},${b.y}`
        : `M${a.x},${a.y + 20}C${a.x},${a.y + 58} ${b.x},${b.y - 58} ${b.x},${b.y - 20}`,
      fill: "none",
      stroke: "#8098b7",
      "stroke-width": 1.3,
      "stroke-dasharray": edge.type === "flow" ? "" : "4 4",
      "marker-end": "url(#intent-arrow)",
      "data-intent-edge": edge.id,
    });
    path.append(element("title", {}, edge.label || edge.type));
    svg.append(path);
  }
  for (const [index, id] of ordered.entries()) {
    const source = model.nodes.find((node) => node.id === id);
    const { x, y } = positions.get(id);
    const label = artifact.story.captions[id]?.[locale() === "zh-CN" ? 1 : 0] || source.label;
    const group = element("g", {
      "data-intent-node": id,
      class: "intent-business",
    });
    group.append(element("circle", { cx: x, cy: y, r: 20 }));
    group.append(
      element(
        "text",
        { x, y: y + 5, "text-anchor": "middle", class: "intent-symbol" },
        String(index + 1),
      ),
    );
    group.append(
      element(
        "text",
        {
          x: vertical ? 78 : x,
          y: vertical ? y + 5 : y + 44,
          "text-anchor": vertical ? "start" : "middle",
        },
        label,
      ),
    );
    svg.append(group);
  }
  figure.append(caption, svg);
  return figure;
}
