/** Three concise confirmation views, all derived from the archived declaration. */
import { t, locale } from "./site-ui.mjs?rev=files-1";
import { confirmationModel } from "./case-confirmation-model.mjs";
const namespace = "http://www.w3.org/2000/svg";
function element(tag, attributes = {}, text) {
  const node = document.createElementNS(namespace, tag);
  for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
  if (text) node.textContent = text;
  return node;
}

export function proposedFlow(confirmed, artifact) {
  const figure = document.createElement("figure");
  figure.className = "conversation-flow";
  figure.dataset.confirmed = String(confirmed);
  const caption = document.createElement("figcaption");
  caption.textContent = t(confirmed ? "case.flow.confirmed" : "case.flow.proposed");
  const tabs = document.createElement("div");
  tabs.className = "confirmation-tabs";
  tabs.setAttribute("role", "tablist");
  tabs.setAttribute("aria-label", locale() === "zh-CN" ? "确认模型" : "Confirm models");
  const panel = document.createElement("div");
  panel.id = "confirmation-diagram";
  panel.setAttribute("role", "tabpanel");
  const buttons = [];
  function render(tab) {
    const graph = confirmationModel(artifact, tab, locale());
    const svg = element("svg", {
      viewBox: "0 0 610 285",
      role: "img",
      "aria-label": graph.caption,
    });
    const marker = element("marker", {
      id: "intent-arrow",
      viewBox: "0 0 10 10",
      refX: 8,
      refY: 5,
      markerWidth: 5,
      markerHeight: 5,
      orient: "auto",
    });
    marker.append(element("path", { d: "M0 0L10 5L0 10Z", fill: "#91a99c" }));
    const defs = element("defs");
    defs.append(marker);
    svg.append(defs);
    const byId = new Map(graph.nodes.map((node) => [node.id, node]));
    for (const [index, edge] of graph.edges.entries()) {
      const a = byId.get(edge.from),
        b = byId.get(edge.to);
      const reverse = b.x < a.x;
      const self = a.id === b.id;
      const d = self
        ? `M${a.x - 15},${a.y - 12}C${a.x - 70},${a.y - 82} ${a.x + 70},${a.y - 82} ${a.x + 15},${a.y - 12}`
        : reverse
          ? `M${a.x},${a.y + 22}C${a.x},${a.y + 90} ${b.x},${b.y + 90} ${b.x},${b.y + 22}`
          : a.x === b.x
            ? `M${a.x},${a.y + 22}L${b.x},${b.y - 22}`
            : `M${a.x + 22},${a.y}C${(a.x + b.x) / 2},${a.y} ${(a.x + b.x) / 2},${b.y} ${b.x - 22},${b.y}`;
      const path = element("path", {
        d,
        fill: "none",
        stroke: "#91a99c",
        "stroke-width": 1.5,
        "stroke-dasharray": "4 4",
        "marker-end": "url(#intent-arrow)",
        "data-intent-edge": edge.witnesses.join(" "),
      });
      path.append(element("title", {}, [edge.label, edge.condition].filter(Boolean).join(" · ")));
      svg.append(path);
      // Conditions on overlapping transitions remain in their accessible title.
      if (edge.label && (tab === "business" || (tab === "states" && !self && index < 3))) {
        svg.append(
          element(
            "text",
            {
              x: (a.x + b.x) / 2,
              y: (a.y + b.y) / 2 + (reverse ? 76 : -10),
              "text-anchor": "middle",
              class: "intent-edge-label",
            },
            edge.label,
          ),
        );
      }
    }
    for (const node of graph.nodes) {
      const group = element("g", { "data-intent-node": node.id, class: "intent-" + tab });
      group.append(element("circle", { cx: node.x, cy: node.y, r: 22 }));
      group.append(
        element(
          "text",
          { x: node.x, y: node.y + 4, "text-anchor": "middle", class: "intent-symbol" },
          node.glyph,
        ),
      );
      group.append(
        element("text", { x: node.x, y: node.y + 42, "text-anchor": "middle" }, node.label),
      );
      svg.append(group);
    }
    const note = document.createElement("p");
    note.textContent = graph.caption;
    panel.replaceChildren(svg, note);
    panel.setAttribute("aria-labelledby", "confirm-tab-" + tab);
    for (const button of buttons) {
      const active = button.dataset.confirmation === tab;
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    }
  }
  for (const [id, en, zh] of [
    ["business", "Flow", "业务"],
    ["states", "States", "状态"],
    ["rules", "Rules", "规则"],
  ]) {
    const button = document.createElement("button");
    button.type = "button";
    button.role = "tab";
    button.id = "confirm-tab-" + id;
    button.dataset.confirmation = id;
    button.textContent = locale() === "zh-CN" ? zh : en;
    button.setAttribute("aria-controls", panel.id);
    button.onclick = () => render(id);
    button.onkeydown = (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const index = (buttons.indexOf(button) + (event.key === "ArrowRight" ? 1 : 2)) % 3;
      buttons[index].click();
      buttons[index].focus();
    };
    buttons.push(button);
    tabs.append(button);
  }
  figure.append(caption, tabs, panel);
  render("business");
  return figure;
}
