import { nodeTypes } from "./graph-core.js";
import { layerOf } from "./graph-layers.js";
import {
  displayName,
  annotationFor,
  ancestorsToReveal,
  relationStyle,
  edgePorts,
} from "./layout.js";
import { glyphAppearance } from "./glyphs.js";
import { t } from "./i18n.js";

/** Accessible graph controls share the same identities and handlers as WebGL.
 * Indexes make geometry updates linear; unchanged attributes cause no DOM writes.
 */
export class SemanticView {
  constructor(nodes, edges, { onSelect, onEdge }) {
    this.nodes = nodes;
    this.edges = edges;
    this.onSelect = onSelect;
    this.onEdge = onEdge;
  }

  render({ graph, presentation, preferences, selected, spatial }) {
    this.selected = selected;
    const focused = document.activeElement?.dataset.nodeId;
    this.nodes.replaceChildren();
    this.edges.replaceChildren();
    this.nodeElements = new Map();
    this.edgeElements = new Map();
    for (const box of graph.boxes) {
      if (!presentation.glyphs.has(box.id) && !presentation.regions.has(box.id)) continue;
      const el = document.createElement("button"),
        name = displayName(box.node, preferences);
      this.data(el, {
        nodeId: box.id,
        nodeType: box.type,
        plane: spatial ? layerOf(box.node) : "flat",
        representation: presentation.regions.has(box.id)
          ? presentation.glyphs.has(box.id)
            ? "self"
            : "circle"
          : "node",
        color: "#" + nodeTypes[box.type].color.toString(16).padStart(6, "0"),
        core: !!annotationFor(preferences, box.node.referenceOf || box.id).core,
        referenceOf: box.node.referenceOf || "",
        runState: box.state,
        childCount: box.kids.length,
        depth: ancestorsToReveal(graph.all, box.id).length,
      });
      el.textContent = name;
      el.setAttribute("aria-label", name);
      el.setAttribute("aria-expanded", String(!!box.open));
      el.setAttribute("aria-pressed", String(selected === box.id));
      el.onclick = () => this.onSelect(box.id);
      el.onfocus = () => {
        // Selection feedback can change without rebuilding these controls.
        if (this.selected !== box.id) this.onSelect(box.id);
      };
      this.nodes.append(el);
      this.nodeElements.set(box.id, el);
    }
    for (const edge of presentation.edges) {
      const el = document.createElement("button"),
        style = relationStyle(edge);
      el.textContent = t(
        "{0}: {1} → {2}, {3} relations",
        style.label,
        displayName(graph.byId.get(edge.from).node, preferences),
        displayName(graph.byId.get(edge.to).node, preferences),
        edge.members.length,
      );
      this.data(el, {
        edgeId: edge.id,
        from: edge.from,
        to: edge.to,
        relationType: edge.type,
        stroke: style.dash.length ? "dashed" : "solid",
        layer: edge.crossing ? "foreground" : "internal",
        sourceRegion: edge.sourceRegion,
        targetRegion: edge.targetRegion,
        count: edge.members.length,
      });
      el.onclick = () => this.onEdge(edge);
      this.edges.append(el);
      this.edgeElements.set(edge.id, { el, edge });
    }
    this.nodeElements.get(focused)?.focus({ preventScroll: true });
  }

  /** Selection feedback is immediate, independent of throttled camera geometry. */
  select(id) {
    this.nodeElements?.get(this.selected)?.setAttribute("aria-pressed", "false");
    this.selected = id;
    this.nodeElements?.get(id)?.setAttribute("aria-pressed", "true");
  }

  /** Update screen coordinates after either camera moves, without rebuilding controls. */
  geometry({
    graph,
    presentation,
    displayGraph,
    preferences,
    selected,
    focusContext,
    discussion,
    spatial,
    canvas,
    point,
    scale,
    pan,
  }) {
    const rect = canvas.getBoundingClientRect();
    const regions = new Map(displayGraph.regions.map((region) => [region.id, region]));
    for (const [id, el] of this.nodeElements || []) {
      const box = graph.byId.get(id);
      if (!box) continue;
      const p = point(box),
        appearance = glyphAppearance(nodeTypes[box.type].color, {
          core: annotationFor(preferences, box.node.referenceOf || id).core,
          selected: selected === id,
          related: focusContext.nodes.has(id),
        });
      const region = presentation.regions.has(id) ? regions.get(id) : null,
        world = spatial?.positions[id];
      this.data(el, {
        x: box.x,
        y: box.y,
        pinned: !!box.pinned,
        parent: box.node.parent || "",
        screenX: rect.left + p.x * scale + pan.x,
        screenY: rect.top + p.y * scale + pan.y,
        fill: "#" + appearance.fill.toString(16).padStart(6, "0"),
        fillEmphasis: appearance.emphasis,
        discussion: discussion.includes(id),
        emphasis: focusContext.active
          ? selected === id
            ? "selected"
            : focusContext.nodes.has(id)
              ? "related"
              : "dimmed"
          : "normal",
        groupRadius: region?.radius || "",
        groupCenterX: region?.cx ?? "",
        groupCenterY: region?.cy ?? "",
        worldX: world?.x ?? "",
        worldY: world?.y ?? "",
        worldZ: world?.z ?? "",
      });
      const pressed = String(selected === id);
      if (el.getAttribute("aria-pressed") !== pressed) el.setAttribute("aria-pressed", pressed);
    }
    for (const { el, edge } of this.edgeElements?.values() || []) {
      const ports = spatial
        ? spatial.screenEdge(edge.id)
        : edgePorts(displayGraph, edge, Math.max(32, 15 / scale));
      if (ports.start && ports.end)
        this.data(el, {
          startX: ports.start.x,
          startY: ports.start.y,
          endX: ports.end.x,
          endY: ports.end.y,
        });
    }
  }

  data(el, values) {
    for (const [key, value] of Object.entries(values)) {
      const text = String(value);
      if (el.dataset[key] !== text) el.dataset[key] = text;
    }
  }
}
