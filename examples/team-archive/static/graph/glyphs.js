import { iconFor } from "./node-icons.js";
import { t as boTranslate } from "./i18n.js";
// One geometry source for WebGL nodes and the SVG legend.
export const meanings = {
  "code-directory": boTranslate("Project directory and its files"),
  "code-endpoint": boTranslate("HTTP route and its handler"),
  "code-file": boTranslate("Indexed source file"),
  "code-class": boTranslate("Declared class and its methods"),
  "code-function": boTranslate("Function found in source"),
  "code-reference": boTranslate("Reference to a source declaration"),
  unknown: boTranslate("Unclassified node"),
  "code-parameter": boTranslate("Declared parameter and type"),
  "code-unresolved": boTranslate("External or dynamically resolved reference"),
  business: boTranslate("Business operation"),
  function: boTranslate("Function or method"),
  state: boTranslate("State in the state machine"),
  decision: boTranslate("Condition or rule"),
  resource: boTranslate("Available and occupied capacity"),
  data: boTranslate("Selected value or event field"),
  effect: boTranslate("Committed effect"),
  wait: boTranslate("Waiting for a condition"),
  store: boTranslate("Configured database or storage"),
  dataset: boTranslate("Table, collection, key pattern, or graph label"),
  column: boTranslate("Field type and constraints"),
  query: boTranslate("Recorded database command or query"),
  write: boTranslate("Recorded database write"),
  transaction: boTranslate("Database transaction boundary"),
  transform: boTranslate("Application processing of data"),
};
function mix(a, b, amount) {
  return [16, 8, 0].reduce(
    (value, shift) =>
      value |
      (Math.round(((a >> shift) & 255) * (1 - amount) + ((b >> shift) & 255) * amount) << shift),
    0,
  );
}
export function glyphAppearance(color, { core = false, selected = false, related = false } = {}) {
  const strong = core || selected;
  return {
    // Preserve each layer's hue while keeping every normal, related and selected
    // icon above the same 4.5:1 contrast threshold used by the existing viewer.
    fill: strong ? mix(color, 0x142a40, 0.24) : mix(0xffffff, color, related ? 0.24 : 0.12),
    ink: strong ? 0xffffff : mix(color, 0x142a40, 0.42),
    border: color,
    emphasis: selected ? "selected" : core ? "core" : related ? "related" : "normal",
  };
}
/** A single MIT Tabler vocabulary supplies graph icons and the planar legend. */
export const spatialShape = (type) => "tabler:" + iconFor(type).name;
export const glyphShapes = (type) =>
  iconFor(type).strokes.map((points) => ({ kind: "polyline", points }));
export function drawGlyph(g, type, x, y, color, appearance = glyphAppearance(color)) {
  g.circle(x, y, 29)
    .fill({ color: appearance.fill, alpha: 1 })
    .stroke({ color: appearance.border, alpha: 0.38, width: 1.4 });
  for (const path of iconFor(type).strokes) {
    g.moveTo(x + path[0][0] * 2.05, y + path[0][1] * 2.05);
    for (const p of path.slice(1)) g.lineTo(x + p[0] * 2.05, y + p[1] * 2.05);
  }
  g.stroke({ color: appearance.ink, width: 2.8, cap: "round", join: "round" });
}
export function legendGlyph(type, style, options = {}) {
  const ns = "http://www.w3.org/2000/svg",
    svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "-14 -14 28 28");
  svg.setAttribute("aria-hidden", "true");
  svg.dataset.glyph = type;
  svg.dataset.mode = options.spatial ? "3D" : "2D";
  svg.dataset.icon = iconFor(type).name;
  svg.dataset.shape = spatialShape(type);
  const appearance = glyphAppearance(style.color, options),
    ink = appearance.ink;
  const disc = document.createElementNS(ns, "circle");
  disc.setAttribute("r", "13.2");
  disc.setAttribute("fill", "#" + appearance.fill.toString(16).padStart(6, "0"));
  disc.setAttribute("stroke", "#" + appearance.border.toString(16).padStart(6, "0"));
  disc.setAttribute("stroke-opacity", "0.38");
  disc.setAttribute("stroke-width", "0.65");
  svg.append(disc);
  for (const points of iconFor(type).strokes) {
    const path = document.createElementNS(ns, "polyline");
    path.setAttribute("points", points.map((p) => p.join(",")).join(" "));
    path.setAttribute("stroke", "#" + ink.toString(16).padStart(6, "0"));
    path.setAttribute("stroke-width", "1.6");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    path.setAttribute("fill", "none");
    svg.append(path);
  }
  return svg;
}
export function legendRelation(style) {
  const ns = "http://www.w3.org/2000/svg",
    svg = document.createElementNS(ns, "svg"),
    color = "#" + style.color.toString(16).padStart(6, "0");
  svg.setAttribute("viewBox", "0 0 44 20");
  svg.setAttribute("aria-hidden", "true");
  const line = document.createElementNS(ns, "path");
  line.setAttribute("d", "M2 10 H34");
  line.setAttribute("stroke", color);
  line.setAttribute("stroke-width", "2");
  line.setAttribute("stroke-dasharray", style.dash.join(" "));
  svg.append(line);
  if (style.arrow !== "none") {
    const arrow = document.createElementNS(ns, "path");
    arrow.setAttribute(
      "d",
      style.arrow === "bar"
        ? "M36 4 V16"
        : style.arrow === "diamond"
          ? "M40 10 L34 5 L28 10 L34 15 Z"
          : "M31 5 L39 10 L31 15" + (style.arrow === "filled" ? " Z" : ""),
    );
    arrow.setAttribute("stroke", color);
    arrow.setAttribute("stroke-width", "1.8");
    arrow.setAttribute(
      "fill",
      style.arrow === "filled" ? color : style.arrow === "diamond" ? "white" : "none",
    );
    svg.append(arrow);
  }
  return svg;
}
