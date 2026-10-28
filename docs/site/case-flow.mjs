/** The intent diagram proposed inside the scripted requirement conversation.
 * Stable identities link this proposal to the later implementation graph.
 */
import { t } from "./site-ui.mjs?rev=controls-1";
const svgNS = "http://www.w3.org/2000/svg";
function svgNode(tag, attributes = {}, text) {
  const element = document.createElementNS(svgNS, tag);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
  if (text) element.textContent = text;
  return element;
}
export function proposedFlow(confirmed) {
  const vertical = innerWidth < 700;
  const figure = document.createElement("figure");
  figure.className = "conversation-flow";
  figure.dataset.confirmed = String(confirmed);
  const caption = document.createElement("figcaption");
  caption.textContent = t(confirmed ? "case.flow.confirmed" : "case.flow.proposed");
  const svg = svgNode("svg", {
    viewBox: vertical ? "0 0 340 590" : "0 0 720 200",
    role: "img",
    "aria-label": t("case.flow.proposed"),
  });
  const defs = svgNode("defs");
  const marker = svgNode("marker", {
    id: "intent-arrow",
    viewBox: "0 0 10 10",
    refX: 8,
    refY: 5,
    markerWidth: 5,
    markerHeight: 5,
    orient: "auto-start-reverse",
  });
  marker.append(svgNode("path", { d: "M0 0L10 5L0 10Z", fill: "#8098b7" }));
  defs.append(marker);
  svg.append(defs);
  const items = [
    ["upload", "case.flow.upload", "business"],
    ["state.pending", "case.flow.pending", "state"],
    ["review", "case.flow.review", "business"],
    ["review-policy", "case.flow.check", "decision"],
    ["publish", "case.flow.publish", "business"],
    ["exhibit", "case.flow.exhibit", "business"],
  ];
  items.forEach(([id, label, type], index) => {
    const x = vertical ? 65 : 60 + index * 120;
    const y = vertical ? 45 + index * 95 : 95;
    if (index < items.length - 1)
      svg.append(
        svgNode("path", {
          d: vertical ? `M${x} ${y + 20}V${y + 73}` : `M${x + 20} 95H${x + 98}`,
          fill: "none",
          stroke: "#8098b7",
          "stroke-width": 1.5,
          "marker-end": "url(#intent-arrow)",
        }),
      );
    const group = svgNode("g", { "data-intent-node": id, class: "intent-" + type });
    group.append(svgNode("circle", { cx: x, cy: y, r: 20 }));
    group.append(
      svgNode(
        "text",
        { x, y: y + 5, "text-anchor": "middle", class: "intent-symbol" },
        type === "decision" ? "?" : type === "state" ? "◷" : String(index + 1),
      ),
    );
    group.append(
      svgNode(
        "text",
        {
          x: vertical ? 102 : x,
          y: vertical ? y + 5 : 142,
          "text-anchor": vertical ? "start" : "middle",
        },
        t(label),
      ),
    );
    svg.append(group);
  });
  svg.append(
    svgNode("path", {
      d: vertical ? "M85 330H292V235H85" : "M420 73V34H300V73",
      fill: "none",
      stroke: "#bd925c",
      "stroke-width": 1.5,
      "stroke-dasharray": "4 4",
      "marker-end": "url(#intent-arrow)",
    }),
  );
  svg.append(
    svgNode(
      "text",
      {
        x: vertical ? 205 : 360,
        y: vertical ? 285 : 18,
        "text-anchor": "middle",
        class: "intent-return",
      },
      t("case.flow.reopen"),
    ),
  );
  const states = document.createElement("p");
  states.textContent = t("case.flow.states");
  figure.append(caption, svg, states);
  return figure;
}
