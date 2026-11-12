/** Small, pre-laid-out story graphs. No inventory scans, layout workers or API polling. */
import { iconFor } from "./viewer/node-icons.js";
const ns = "http://www.w3.org/2000/svg";
const svgNode = (tag, attrs = {}, text) => {
  const node = document.createElementNS(ns, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
};
import { edgePoints, curvePath, midpoint, labelOf } from "./case-graph-geometry.mjs";

export function preparedGraph(host, { onInspect = () => {} } = {}) {
  const svg = svgNode("svg", {
    class: "prepared-svg",
    role: "group",
    "aria-label": "VibeLens focused graph",
  });
  const surface = svgNode("g");
  svg.append(surface);
  host.append(svg);
  let graph,
    language = "en",
    step = null,
    mode = "2d",
    interactive = false,
    zoom = 1,
    pan = [0, 0],
    drag = null,
    spatial = null,
    spatialPromise = null,
    generation = 0;
  const transform = () => surface.setAttribute("transform", `translate(${pan}) scale(${zoom})`);
  const nodesDom = new Map();
  function draw() {
    if (!graph) return;
    const index = new Map(graph.nodes.map((n) => [n.id, n]));
    const extents = graph.nodes.reduce(
      (b, n) => [
        Math.min(b[0], n.x - 65),
        Math.min(b[1], n.y - 115),
        Math.max(b[2], n.x + 80),
        Math.max(b[3], n.y + 85),
      ],
      [Infinity, Infinity, -Infinity, -Infinity],
    );
    svg.setAttribute(
      "viewBox",
      `${extents[0]} ${extents[1]} ${extents[2] - extents[0]} ${extents[3] - extents[1]}`,
    );
    const defs = svgNode("defs"),
      lines = svgNode("g", { class: "prepared-edges" }),
      marks = svgNode("g", { class: "prepared-transfers" });
    const active = new Set(step?.transfers || []);
    const colors = [...new Set(graph.edges.map((e) => e.color))];
    for (const [i, color] of colors.entries()) {
      const marker = svgNode("marker", {
        id: `prepared-arrow-${i}`,
        viewBox: "0 0 10 10",
        refX: 8,
        refY: 5,
        markerWidth: 5,
        markerHeight: 5,
        orient: "auto",
      });
      marker.append(
        svgNode("path", { d: "M0 1L9 5L0 9", fill: "none", stroke: color, "stroke-width": 1.7 }),
      );
      defs.append(marker);
    }
    graph.edges.forEach((edge, i) => {
      const a = index.get(edge.from),
        b = index.get(edge.to),
        d = curvePath(edgePoints(edge, index, i));
      const cross = a.layer !== b.layer;
      const path = svgNode("path", {
        d,
        fill: "none",
        stroke: edge.color,
        "stroke-width": active.has(edge.id) ? 2.5 : 1.6,
        "stroke-dasharray": cross ? "5 4" : "none",
        "marker-end": `url(#prepared-arrow-${colors.indexOf(edge.color)})`,
        class: "prepared-edge",
        "data-edge-id": edge.id,
        "data-witnesses": edge.witnesses.join(" "),
      });
      const label =
        edge.labels?.[language === "zh-CN" ? 1 : 0] ||
        edge.label ||
        `${labelOf(a, language)} → ${labelOf(b, language)}`;
      path.append(svgNode("title", {}, [label, edge.condition].filter(Boolean).join(" · ")));
      lines.append(path);
      if (edge.label && !cross) {
        const center = midpoint(edgePoints(edge, index));
        const text = svgNode(
          "text",
          {
            x: center[0],
            y: center[1] - 10,
            "text-anchor": "middle",
            class: "prepared-edge-label",
          },
          label,
        );
        lines.append(text);
      }
      if (active.has(edge.id) && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
        const arrow = svgNode("path", {
          d: "M-6 -4L1 0L-6 4",
          fill: "none",
          stroke: edge.color,
          "stroke-width": 2.7,
          "data-transfer": edge.id,
        });
        arrow.append(
          svgNode("animateMotion", {
            dur: "1.2s",
            repeatCount: "indefinite",
            path: d,
            rotate: "auto",
          }),
        );
        marks.append(arrow);
      }
    });
    surface.replaceChildren(defs, lines, marks);
    const retained = new Set();
    for (const node of graph.nodes) {
      retained.add(node.id);
      let group = nodesDom.get(node.id);
      if (!group) {
        group = svgNode("g", {
          class: "prepared-node",
          tabindex: 0,
          role: "button",
          "data-node-id": node.id,
        });
        nodesDom.set(node.id, group);
      }
      group.style.transform = `translate(${node.x}px,${node.y}px)`;
      group.style.setProperty("--node-color", node.color);
      const running = node.id === step?.node || (node.value && node.value === step?.state);
      group.classList.toggle("is-active", !!running);
      group.setAttribute("aria-label", labelOf(node, language));
      group.setAttribute("data-layer", node.layer);
      group.replaceChildren(
        svgNode("circle", { r: 23, class: "prepared-halo" }),
        svgNode("circle", { r: 18, class: "prepared-face" }),
      );
      for (const stroke of iconFor(node.kind).strokes)
        group.append(
          svgNode("polyline", {
            points: stroke.map((p) => p.join(",")).join(" "),
            fill: "none",
            stroke: node.color,
            "stroke-width": 1.6,
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
          }),
        );
      group.append(
        svgNode(
          "text",
          { y: 37, "text-anchor": "middle", class: "prepared-node-label" },
          labelOf(node, language),
        ),
      );
      if (["AND", "OR"].includes(node.glyph))
        group.append(
          svgNode(
            "text",
            { y: -31, "text-anchor": "middle", class: "prepared-operator" },
            node.glyph,
          ),
        );
      let value = step?.samples?.[node.id]?.value;
      group.dataset.observedEvent = step?.samples?.[node.id]?.eventId || "";
      if (node.id === step?.node && step.outputs?.removed !== undefined)
        value = `removed: ${step.outputs.removed}`;
      if (value !== undefined)
        group.append(
          svgNode(
            "text",
            { y: 54, "text-anchor": "middle", class: "prepared-value" },
            String(value),
          ),
        );
      group.append(
        svgNode(
          "title",
          {},
          `${labelOf(node, language)}${value !== undefined ? ` · ${value}` : ""}`,
        ),
      );
      group.ondblclick = () => onInspect(node);
      group.onkeydown = (event) => {
        if (event.key === "Enter") onInspect(node);
      };
      surface.append(group);
    }
    for (const id of nodesDom.keys()) if (!retained.has(id)) nodesDom.delete(id);
    transform();
    host.dataset.nodeCount = graph.nodes.length;
    host.dataset.eventId = step?.id || "";
    host.dataset.ready = "true";
    if (mode === "3d") spatial?.render(graph, step, language);
  }
  svg.onpointerdown = (event) => {
    if (!interactive || event.button !== 0) return;
    drag = { x: event.clientX, y: event.clientY, pan: [...pan] };
    svg.setPointerCapture(event.pointerId);
  };
  svg.onpointermove = (event) => {
    if (!drag) return;
    const scale = svg.viewBox.baseVal.width / svg.getBoundingClientRect().width;
    pan = [
      drag.pan[0] + (event.clientX - drag.x) * scale,
      drag.pan[1] + (event.clientY - drag.y) * scale,
    ];
    transform();
  };
  svg.onpointerup = () => {
    drag = null;
  };
  svg.addEventListener(
    "wheel",
    (event) => {
      if (!interactive) return;
      event.preventDefault();
      zoom = Math.max(0.4, Math.min(3, zoom * Math.exp(-event.deltaY * 0.001)));
      transform();
    },
    { passive: false },
  );
  return {
    render(next, nextStep, nextLanguage) {
      graph = next;
      step = nextStep;
      language = nextLanguage;
      draw();
    },
    interact(value) {
      interactive = value;
      host.dataset.interactive = String(value);
      spatial?.interact(value);
    },
    async mode(value) {
      mode = value;
      const ticket = ++generation;
      if (value === "3d") {
        spatialPromise ||= import("./case-prepared-spatial.mjs").then((module) =>
          module.spatialGraph(host),
        );
        spatial = await spatialPromise;
        if (ticket !== generation) return;
        spatial.interact(interactive);
        spatial.render(graph, step, language);
      }
      svg.style.display = mode === "3d" ? "none" : "";
      spatial?.visible(mode === "3d");
      host.dataset.mode = mode;
    },
    fit() {
      zoom = 1;
      pan = [0, 0];
      transform();
      spatial?.fit();
    },
    destroy() {
      generation++;
      spatial?.destroy();
      svg.remove();
    },
  };
}
