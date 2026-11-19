/** Inspect an exported model counterexample on a logical axis.
 * Importing is a read-only display operation. It never inserts runtime events,
 * changes the application or issues verification evidence.
 */
import { logicalStep, logicalTimeline } from "./logical-trace.js";
import { layers } from "./graph-layers.js";
import { t } from "./i18n.js";
const cssColor = (value) =>
  typeof value === "number" ? `#${value.toString(16).padStart(6, "0")}` : value || "#456";

export function createAnalysisPanel({ read, highlight, pause }) {
  const button = document.getElementById("analysis-trace-open"),
    input = document.getElementById("analysis-trace-file"),
    panel = document.getElementById("analysis-trace-panel");
  let trace = null,
    index = 0,
    previous = [],
    dragging = false;
  const element = (name, text) => {
    const node = document.createElement(name);
    if (text != null) node.textContent = text;
    return node;
  };
  const close = () => {
    trace = null;
    panel.hidden = true;
    highlight(previous);
  };
  function render() {
    if (!trace) return;
    const context = read(),
      same = context.definition === trace.definition_sha256,
      step = logicalStep(trace, index, context.all, context.edges),
      timeline = logicalTimeline(trace, context.all, context.edges, context.layers),
      header = element("div"),
      title = element("strong", t("Model counterexample")),
      status = element(
        "span",
        same
          ? t("Logical step {0}/{1}", index, trace.states.length - 1)
          : t("Model definition changed"),
      ),
      exit = element("button", "×"),
      slider = element("input");
    exit.title = t("Close");
    exit.onclick = close;
    header.className = "analysis-trace-header";
    header.append(title, status, exit);
    slider.type = "range";
    slider.min = 0;
    slider.max = trace.states.length - 1;
    slider.value = index;
    slider.disabled = !same;
    slider.setAttribute("aria-label", t("Logical step"));
    slider.oninput = () => {
      index = Number(slider.value);
      render();
    };
    const rows = timeline.rows.filter((row) => row.marks.length),
      ns = "http://www.w3.org/2000/svg",
      svg = document.createElementNS(ns, "svg"),
      width = 1000,
      margin = 115,
      rowHeight = 30;
    svg.setAttribute("viewBox", `0 0 ${width} ${Math.max(1, rows.length) * rowHeight + 20}`);
    svg.setAttribute("aria-label", t("Logical model timeline"));
    const x = (step) =>
        margin + (step / Math.max(1, trace.states.length - 1)) * (width - margin - 20),
      y = (row) => 20 + row * rowHeight,
      rowFor = new Map();
    const shape = (name, attrs, label) => {
      const item = document.createElementNS(ns, name);
      for (const [key, value] of Object.entries(attrs)) item.setAttribute(key, value);
      if (label != null) item.textContent = label;
      svg.append(item);
      return item;
    };
    rows.forEach((row, i) => {
      const style = layers.find((layer) => layer.id === row.layer);
      shape(
        "text",
        { x: 0, y: y(i) + 4, fill: cssColor(style?.color) },
        t(style?.label || row.layer),
      );
      shape("line", { x1: margin, x2: width - 10, y1: y(i), y2: y(i), stroke: "#dce2ea" });
      for (const mark of row.marks) rowFor.set(mark.node, i);
    });
    // Lines represent the original definition links at this logical step.
    // Runtime durations, causal calls and transfer particles are not fabricated.
    for (const link of timeline.links) {
      if (!rowFor.has(link.from) || !rowFor.has(link.to)) continue;
      shape("path", {
        d: `M ${x(link.index) - 8} ${y(rowFor.get(link.from))} Q ${x(link.index) - 22} ${(y(rowFor.get(link.from)) + y(rowFor.get(link.to))) / 2} ${x(link.index)} ${y(rowFor.get(link.to))}`,
        fill: "none",
        stroke: "#7894b5",
        "stroke-width": 1,
        "stroke-dasharray": "3 3",
      });
    }
    rows.forEach((row, i) => {
      for (const mark of row.marks) {
        const dot = shape("circle", {
            cx: x(mark.index),
            cy: y(i),
            r: mark.index === index ? 6 : 3,
            fill: cssColor(layers.find((layer) => layer.id === row.layer)?.color),
          }),
          tooltip = document.createElementNS(ns, "title");
        tooltip.textContent = `${mark.action} · ${context.all.get(mark.node)?.label || mark.node}`;
        dot.append(tooltip);
      }
    });
    shape("line", {
      x1: x(index),
      x2: x(index),
      y1: 0,
      y2: rows.length * rowHeight + 12,
      stroke: "#3b65aa",
      "stroke-width": 1.5,
    });
    const seek = (event) => {
      if (!same) return;
      const bounds = svg.getBoundingClientRect();
      index = Math.max(
        0,
        Math.min(
          trace.states.length - 1,
          Math.round(
            ((((event.clientX - bounds.left) / bounds.width) * width - margin) /
              (width - margin - 20)) *
              (trace.states.length - 1),
          ),
        ),
      );
      render();
    };
    // The stable panel owns capture while the SVG is redrawn during a drag.
    svg.onpointerdown = (event) => {
      dragging = true;
      panel.setPointerCapture(event.pointerId);
      seek(event);
    };
    panel.onpointermove = (event) => {
      if (dragging) seek(event);
    };
    panel.onpointerup = () => {
      dragging = false;
    };
    const changes = element(
      "p",
      step.changes
        .map(
          (change) =>
            `${change.variable}: ${JSON.stringify(change.before)} → ${JSON.stringify(change.after)}`,
        )
        .join(" · ") || t("Initial state"),
    );
    if (step.loopBack != null)
      changes.append(document.createTextNode(` · ${t("Loop to step {0}", step.loopBack)}`));
    if (step.hidden.length)
      changes.append(
        document.createTextNode(` · ${t("{0} references outside this view", step.hidden.length)}`),
      );
    const values = element("details"),
      summary = element("summary", t("Values")),
      code = element("pre", JSON.stringify(step.values, null, 2));
    values.append(summary, code);
    panel.replaceChildren(header, svg, slider, changes, values);
    panel.hidden = false;
    if (same) highlight(step.nodes);
  }
  button.onclick = () => input.click();
  input.onchange = async () => {
    try {
      const file = input.files[0];
      if (!file || file.size > 8 * 1024 * 1024)
        throw new Error(t("Model trace exceeds display limit"));
      const candidate = JSON.parse(await file.text()),
        context = read();
      if (candidate.states?.length > 10000) throw new Error(t("Model trace exceeds display limit"));
      logicalStep(candidate, 0, context.all, context.edges);
      if (candidate.definition_sha256 !== context.definition)
        throw new Error(t("Model definition changed"));
      previous = [...context.selection];
      pause();
      trace = candidate;
      index = 0;
      render();
    } catch (error) {
      panel.replaceChildren(element("p", error.message));
      panel.hidden = false;
      const exit = element("button", t("Close"));
      exit.onclick = close;
      panel.append(exit);
    } finally {
      input.value = "";
    }
  };
  return {
    get active() {
      return trace !== null;
    },
    refresh() {
      const context = read();
      button.hidden = !context.definition;
      if (trace && trace.definition_sha256 !== context.definition) {
        trace = null;
        panel.replaceChildren(element("p", t("Model definition changed")));
        const exit = element("button", t("Close"));
        exit.onclick = close;
        panel.append(exit);
        highlight([]);
      }
    },
  };
}
