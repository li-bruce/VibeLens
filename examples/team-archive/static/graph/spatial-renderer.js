import { strokeSegments } from "./route-shapes.js";
import { edgeCurve } from "./spatial-paths.js";
import * as T from "./spatial-three.vendor.js";
import {
  spatialModel,
  containmentVolumes,
  descendants,
  nodeElevation,
  planarSeeds,
} from "./spatial-model.js";
import { cleanLayers, layerHeights } from "./graph-layers.js";
import { cleanRoute, polylineAt } from "./edge-routing.js";
import { RoutingClient } from "./routing-client.js";
import { spatialScene } from "./routing-scene.js";
import { nodeTypes } from "./graph-core.js";
import { nodeGeometry } from "./spatial-geometry.js";
import { regionLabelAnchor } from "./spatial-labels.js";
import { relationStyle, displayName, annotationFor } from "./layout.js";
import { t } from "./i18n.js";

const vector = (p) => new T.Vector3(p.x, p.y, p.z);
const cameraDirections = {
  angled: [1.2, 0.85, 1.5],
  front: [0, 0.2, 2],
  side: [2, 0.3, 0.1],
  top: [0, 2, 0.0001],
};

/** Owns the real WebGL scene and nothing in the business/state model.
 * Nodes and arrows are instanced; curves share one wide-line buffer; labels are
 * bounded, screen-facing DOM. Camera movement does not rebuild graph geometry.
 */
export class SpatialRenderer {
  /** Allocate one viewport and workers; callbacks report UI changes without changing the model. */
  constructor(host, callbacks = {}) {
    this.host = host;
    this.callbacks = callbacks;
    this.router = new RoutingClient((stats) => {
      // Large scenes upload the finished edge buffer once. Rebuilding a growing
      // buffer on every progress packet creates quadratic work and allocation.
      if (stats.busy && this.model?.edges.length > 2000) this.callbacks.onRender?.();
      else this.refreshEdges();
    });
    this.scene = new T.Scene();
    this.scene.background = new T.Color(0xf6f8fa);
    this.scene.add(new T.AmbientLight(0xffffff, 1.3));
    const light = new T.DirectionalLight(0xffffff, 2);
    light.position.set(3, 4, 5);
    this.scene.add(light);
    this.camera = new T.PerspectiveCamera(43, 1, 1, 100000);
    this.camera.position.set(1400, 1000, 1800);
    this.renderer = new T.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.setClearColor(0xf6f8fa);
    this.canvas = this.renderer.domElement;
    this.canvas.className = "spatial-canvas";
    this.canvas.setAttribute("aria-hidden", "true");
    this.labels = document.createElement("div");
    this.labels.className = "spatial-labels";
    host.append(this.canvas, this.labels);
    this.controls = new T.OrbitControls(this.camera, this.canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.16;
    this.controls.screenSpacePanning = true;
    this.controls.minDistance = 60;
    this.controls.maxDistance = 60000;
    this.controls.addEventListener("change", () => this.schedule());
    this.controls.addEventListener("end", () => this.callbacks.onSave?.());
    this.raycaster = new T.Raycaster();
    this.positions = {};
    this.epoch = 0;
    this.frames = [];
    this.frameCount = 0;
    this.worker = new Worker(new URL("./spatial-worker.js", import.meta.url), {
      type: "module",
    });
    this.worker.onmessage = ({ data }) => {
      if (data.epoch !== this.epoch || this.disposed) return;
      this.busy = false;
      if (data.error) {
        this.callbacks.onError?.(data.error);
        return;
      }
      // A solve covers only visible nodes. Keep folded/filtered positions so
      // hiding a layer cannot erase a layout or break whole-branch movement.
      this.positions = { ...this.positions, ...data.positions };
      this.layoutMs = data.elapsed;
      this.rebuild();
      if (this.pendingFit) {
        this.fit();
        this.pendingFit = false;
      }
      this.callbacks.onSave?.();
    };
    this.worker.onerror = (error) => {
      this.busy = false;
      this.callbacks.onError?.(error.message);
    };
    this.installPointer();
    this.onVisibility = () => (document.hidden ? this.pause() : this.schedule());
    document.addEventListener("visibilitychange", this.onVisibility);
    this.canvas.addEventListener("webglcontextlost", (event) => {
      event.preventDefault();
      this.lost = true;
      this.pause();
      this.callbacks.onError?.(t("Graphics connection lost; recovering"));
    });
    this.canvas.addEventListener("webglcontextrestored", () => {
      this.lost = false;
      this.rebuild();
    });
    this.resize();
    this.setVisible(false);
  }

  /** Suspend hidden viewports while retaining camera, buffers and saved positions. */
  setVisible(visible) {
    this.visible = visible;
    this.canvas.hidden = this.labels.hidden = !visible;
    this.controls.enabled = visible;
    if (visible) {
      this.resize();
      this.schedule();
    } else this.pause();
  }

  /** Reuse positions by stable ID. A new revision changes facts, not a user's layout. */
  update(input) {
    this.input = input;
    const next = spatialModel(input.graph, input.presentation);
    const topology = JSON.stringify([
      next.nodes.map((n) => [n.id, n.parent, n.layer]),
      next.edges.map((e) => [e.id, e.from, e.to]),
      input.settings.gap,
      input.settings.order,
      input.settings.visible,
    ]);
    const scopeChanged = this.scope !== input.scope;
    if (scopeChanged) {
      this.scope = input.scope;
      this.positions = structuredClone(input.preferences.spatial?.positions || {});
      this.settled = new Set(Object.keys(this.positions));
      const saved = input.preferences.spatial?.camera;
      if (
        saved?.position?.length === 3 &&
        saved?.target?.length === 3 &&
        [...saved.position, ...saved.target].every(Number.isFinite)
      ) {
        this.camera.position.fromArray(saved.position);
        this.controls.target.fromArray(saved.target);
        this.controls.update();
        this.pendingFit = false;
      } else this.pendingFit = true;
    }
    this.model = next;
    this.settings = cleanLayers(input.settings);
    const content = JSON.stringify([
      topology,
      input.selected,
      [...input.focusContext.nodes],
      next.nodes.map((n) => [n.id, n.state, n.rows]),
      input.preferences.annotations,
      this.settings.projections,
      input.routing,
      [...input.boTransfers],
    ]);
    if (scopeChanged || topology !== this.topology) {
      this.topology = topology;
      // Seed immediately for responsive expansion; settle in a worker afterwards.
      this.seedMissing();
      this.layout();
    }
    const geometry = JSON.stringify([
      input.scope,
      topology,
      input.preferences.annotations,
      this.settings.projections,
      input.routing,
    ]);
    if (geometry !== this.geometryKey) {
      this.geometryKey = geometry;
      this.rebuild();
    } else if (content !== this.content) this.updateEmphasis();
    this.content = content;
  }

  /** Place new identities near their parent; existing coordinates keep their X/Z values. */
  seedMissing() {
    const count = Math.max(1, this.model.nodes.length);
    const heights = layerHeights(this.settings, this.model.layers);
    for (const [i, node] of this.model.nodes.entries()) {
      const y = nodeElevation(node, this.model.byId, heights.get(node.layer), this.settings.gap);
      if (!this.positions[node.id]) {
        const parent = this.positions[node.parent],
          angle = i * 2.3999632297;
        this.positions[node.id] = {
          x: (parent?.x || 0) + Math.cos(angle) * (parent ? 130 : Math.sqrt(count) * 100),
          y,
          z: (parent?.z || 0) + Math.sin(angle) * (parent ? 130 : Math.sqrt(count) * 100),
        };
      } else this.positions[node.id].y = y;
    }
  }

  /** Send constrained layout work off-thread; only explicit Arrange releases saved positions. */
  layout(arrange = false, shared = null) {
    if (!this.model) return;
    this.busy = true;
    // Newly added nodes are not fixed; saved manual positions and pins survive.
    const existing = arrange
      ? this.positions
      : Object.fromEntries(Object.entries(this.positions).filter(([id]) => this.settled?.has(id)));
    this.worker.postMessage({
      epoch: ++this.epoch,
      started: performance.now(),
      nodes: this.model.nodes,
      edges: this.model.edges.map(({ from, to, type }) => ({ from, to, type })),
      layers: this.model.layers,
      gap: this.settings.gap,
      settings: this.settings,
      positions: existing,
      planar: shared || planarSeeds(this.input.graph, this.input.preferences.positions),
      arrange,
    });
    this.settled = new Set([...(this.settled || []), ...this.model.nodes.map((n) => n.id)]);
  }

  /** Dispose replaced topology/position buffers once; runtime colors reuse them. */
  clearScene() {
    if (!this.group) return;
    const geometries = new Set(),
      materials = new Set();
    this.group.traverse((object) => {
      if (object.geometry) geometries.add(object.geometry);
      for (const material of Array.isArray(object.material) ? object.material : [object.material])
        if (material) materials.add(material);
    });
    this.scene.remove(this.group);
    geometries.forEach((g) => g.dispose());
    materials.forEach((m) => m.dispose());
    this.labels.replaceChildren();
  }

  /** Replace topology/position buffers once; keep semantic ownership separate from geometry. */
  rebuild() {
    if (!this.model || !this.input || this.disposed) return;
    this.clearScene();
    this.group = new T.Group();
    this.scene.add(this.group);
    this.pickable = [];
    this.labelItems = [];
    this.curves = new Map();
    const { graph, preferences, selected, focusContext } = this.input;
    const matrix = new T.Object3D();
    const typeGroups = new Map();
    for (const node of this.model.nodes.filter((node) => node.glyph)) {
      if (!typeGroups.has(node.type)) typeGroups.set(node.type, []);
      typeGroups.get(node.type).push(node);
    }
    for (const [type, nodes] of typeGroups) {
      const geometry = this.nodeGeometry(type);
      const mesh = new T.InstancedMesh(geometry, new T.MeshLambertMaterial(), nodes.length);
      mesh.userData.ids = nodes.map((n) => n.id);
      for (const [i, node] of nodes.entries()) {
        const p = this.positions[node.id];
        if (!p) continue;
        const box = graph.byId.get(node.id),
          core = annotationFor(preferences, box.node.referenceOf || node.id).core;
        const size = selected === node.id ? 27 : core ? 24 : 19;
        matrix.position.copy(vector(p));
        matrix.scale.setScalar(size);
        matrix.updateMatrix();
        mesh.setMatrixAt(i, matrix.matrix);
        const color = new T.Color(nodeTypes[type].color);
        if (focusContext.active && !focusContext.nodes.has(node.id))
          color.lerp(new T.Color(0xe1e7eb), 0.8);
        mesh.setColorAt(i, color);
      }
      mesh.instanceMatrix.needsUpdate = true;
      mesh.computeBoundingSphere();
      this.group.add(mesh);
      this.pickable.push(mesh);
    }
    this.volumes = containmentVolumes(this.model, this.positions, this.settings.gap);
    const circle = new T.CircleGeometry(1, 64);
    for (const volume of this.volumes) {
      if (volume.projection && !this.settings.projections) continue;
      const node = this.model.byId.get(volume.id),
        color = nodeTypes[node.type].color;
      const active = selected === volume.id || focusContext.regions.has(volume.id);
      const shell = new T.Mesh(
        circle,
        new T.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: active ? 0.13 : volume.projection ? 0.035 : 0.065,
          depthWrite: false,
          side: T.DoubleSide,
        }),
      );
      shell.position.copy(vector(volume.center));
      shell.rotation.x = -Math.PI / 2;
      shell.scale.set(volume.radius, volume.radius, 1);
      shell.userData.volume = volume;
      shell.renderOrder = -2;
      this.group.add(shell);
      const points = Array.from(
        { length: 97 },
        (_, i) =>
          new T.Vector3(
            volume.center.x + Math.cos((i * Math.PI) / 48) * volume.radius,
            volume.center.y,
            volume.center.z + Math.sin((i * Math.PI) / 48) * volume.radius,
          ),
      );
      const ring = new T.Line(
        new T.BufferGeometry().setFromPoints(points),
        new T.LineBasicMaterial({
          color,
          transparent: true,
          opacity: active ? 0.85 : 0.35,
          depthWrite: false,
        }),
      );
      this.group.add(ring);
    }
    this.drawLayerGuides();
    this.router.request(
      spatialScene(this.model, this.positions, this.volumes, cleanRoute(this.input.routing)),
    );
    this.drawEdges(matrix);
    // Projected regions repeat the owner's label, not the owner node or its facts.
    const labelNodes = [...this.model.nodes].sort(
      (a, b) => (b.id === selected) - (a.id === selected) || Number(b.region) - Number(a.region),
    );
    for (const node of labelNodes.filter((n) => n.glyph && !n.region).slice(0, 220)) {
      const box = graph.byId.get(node.id),
        label = document.createElement("div");
      label.className = "spatial-label" + (node.id === selected ? " selected" : "");
      label.dataset.spatialLabel = node.id;
      label.style.setProperty(
        "--node-color",
        "#" + nodeTypes[node.type].color.toString(16).padStart(6, "0"),
      );
      const title = document.createElement("span");
      title.className = "spatial-label-title";
      title.textContent = displayName(box.node, preferences);
      label.append(title);
      this.updateBadges(label, box);
      const rows = node.rows
        .filter((row) => ["value", "bad", "state"].includes(row.role))
        .slice(0, node.id === selected ? 5 : 2)
        .map((row) => row.text)
        .filter(Boolean);
      if (rows.length) {
        const values = document.createElement("small");
        values.textContent = rows.join(" · ");
        label.append(values);
      }
      label.title = displayName(box.node, preferences);
      label.dataset.nodeId = node.id;
      label.onpointerdown = (event) => this.startDrag(event, { id: node.id });
      label.onclick = () => this.callbacks.onSelect?.(node.id);
      label.ondblclick = () => this.callbacks.onToggle?.(node.id);
      this.labels.append(label);
      this.labelItems.push({ el: label, id: node.id, offset: 18 });
    }
    for (const volume of this.volumes.filter((v) => !v.projection || this.settings.projections)) {
      if (this.labelItems.length >= 300) break;
      const label = document.createElement("div");
      label.className = "spatial-label region-label";
      label.dataset.spatialRegion = volume.id;
      label.dataset.regionLayer = volume.layer;
      const owner = this.model.byId.get(volume.id);
      label.textContent = displayName(graph.byId.get(volume.id).node, preferences);
      this.updateBadges(label, graph.byId.get(volume.id));
      label.style.setProperty(
        "--node-color",
        "#" + nodeTypes[owner.type].color.toString(16).padStart(6, "0"),
      );
      label.onpointerdown = (event) => this.startDrag(event, { region: volume.id });
      label.onclick = () => this.callbacks.onSelect?.(volume.id);
      this.labels.append(label);
      this.labelItems.unshift({ el: label, id: volume.id, volume, offset: 0 });
    }
    this.updateTransferLabels();
    this.schedule();
  }

  nodeGeometry(type) {
    return nodeGeometry(type, this.model.nodes.length > 2000);
  }

  /** Routing results replace only edge buffers; node meshes and DOM labels survive. */
  refreshEdges() {
    if (!this.group || this.disposed) return;
    for (const object of [this.lines, this.arrowMesh])
      if (object) {
        this.group.remove(object);
        object.geometry.dispose();
        object.material.dispose();
      }
    this.curves.clear();
    this.drawEdges(new T.Object3D());
    this.updateTransferLabels();
    this.schedule();
    this.callbacks.onRender?.();
  }

  /** Counts and runtime status use the same source box as the planar renderer. */
  updateBadges(label, box) {
    if (!box) return;
    let badges = label.querySelector(".node-badges");
    if (!badges) {
      badges = document.createElement("span");
      badges.className = "node-badges";
      label.append(badges);
    }
    const count = Array.isArray(box.kids) ? box.kids.length : null;
    const glyph = { ok: "✓", active: "▶", blocked: "!", historical: "·" }[box.state] || "";
    badges.textContent = [count ? `${box.open ? "" : "+ "}${count}` : "", glyph]
      .filter(Boolean)
      .join("  ");
    badges.dataset.childCount = count === null ? "" : String(count);
    badges.dataset.runState = box.state;
    badges.title = [count ? t("{0} children", count) : "", t(box.state || "declared")]
      .filter(Boolean)
      .join(" · ");
    badges.hidden = !badges.textContent;
    label.classList.toggle("primary-key", box.node?.data_metadata?.primary_key === true);
    label.dataset.primaryKey = String(box.node?.data_metadata?.primary_key === true);
  }

  /** Runtime/selection changes reuse GPU geometry; only instance colors and labels change. */
  updateEmphasis() {
    const { graph, preferences, selected, focusContext } = this.input;
    const matrix = new T.Object3D();
    for (const mesh of this.pickable || []) {
      for (const [i, id] of mesh.userData.ids.entries()) {
        const node = this.model.byId.get(id),
          box = graph.byId.get(id),
          p = this.positions[id];
        if (!node || !box || !p) continue;
        const core = annotationFor(preferences, box.node.referenceOf || id).core;
        matrix.position.copy(vector(p));
        matrix.scale.setScalar(selected === id ? 27 : core ? 24 : 19);
        matrix.updateMatrix();
        mesh.setMatrixAt(i, matrix.matrix);
        const color = new T.Color(nodeTypes[node.type].color);
        if (focusContext.active && !focusContext.nodes.has(id))
          color.lerp(new T.Color(0xe1e7eb), 0.8);
        mesh.setColorAt(i, color);
      }
      mesh.instanceColor.needsUpdate = true;
      mesh.instanceMatrix.needsUpdate = true;
    }
    for (const item of this.labelItems || []) {
      const node = this.model.byId.get(item.id);
      if (!node) continue;
      item.el.classList.toggle("selected", item.id === selected);
      this.updateBadges(item.el, graph.byId.get(item.id));
      const values = node.rows
        .filter((row) => ["value", "bad", "state"].includes(row.role))
        .slice(0, item.id === selected ? 5 : 2)
        .map((row) => row.text);
      let detail = item.el.querySelector("small");
      if (values.length && !detail) {
        detail = document.createElement("small");
        item.el.append(detail);
      }
      if (detail) detail.textContent = values.join(" · ");
    }
    for (const shell of this.group.children.filter((object) => object.userData.volume)) {
      const volume = shell.userData.volume,
        active = selected === volume.id || focusContext.regions.has(volume.id);
      shell.material.opacity = active ? 0.13 : volume.projection ? 0.035 : 0.065;
    }
    const colorStart = this.lines?.geometry.attributes.instanceColorStart;
    const colorEnd = this.lines?.geometry.attributes.instanceColorEnd;
    if (colorStart && colorEnd) {
      for (const item of this.edgeSegments || []) {
        const color = this.edgeColor(item.edge);
        for (let i = item.start; i < item.end; i++) {
          colorStart.setXYZ(i, color.r, color.g, color.b);
          colorEnd.setXYZ(i, color.r, color.g, color.b);
        }
      }
      colorStart.data.needsUpdate = true;
    }
    for (const [i, edge] of (this.arrowEdges || []).entries())
      this.arrowMesh?.setColorAt(i, this.edgeColor(edge));
    if (this.arrowMesh?.instanceColor) this.arrowMesh.instanceColor.needsUpdate = true;
    this.updateTransferLabels();
    this.schedule();
  }

  /** Only focused or currently transferring edges need text in a dense graph. */
  updateTransferLabels() {
    this.labelItems = (this.labelItems || []).filter((item) => {
      if (!item.edge) return true;
      item.el.remove();
      return false;
    });
    for (const edge of this.model.edges) {
      const transfer = this.input.boTransfers.get(edge.id);
      if (!transfer && edge.from !== this.input.selected && edge.to !== this.input.selected)
        continue;
      const curve = this.curves.get(edge.id);
      if (!curve || this.labelItems.length >= 330) continue;
      const el = document.createElement("div");
      el.className = "spatial-label edge-label";
      el.textContent = transfer?.label || edge.label || relationStyle(edge).label;
      el.onclick = () => this.callbacks.onEdge?.(edge);
      this.labels.append(el);
      this.labelItems.push({
        el,
        edge: edge.id,
        position: curve.getPoint(0.5),
        offset: -10,
      });
    }
  }

  /** Draw only populated, visible semantic planes at their current compacted heights. */
  drawLayerGuides() {
    const values = this.model.nodes.map((node) => this.positions[node.id]).filter(Boolean);
    if (!values.length) return;
    const bounds = new T.Box3().setFromPoints(values.map(vector)),
      size = bounds.getSize(new T.Vector3());
    const center = bounds.getCenter(new T.Vector3());
    for (const layer of this.model.layers) {
      // Keep the guide on the same plane as its nodes. A hidden/empty layer
      // leaves neither a background mesh nor a caption behind.
      if (!this.model.nodes.some((node) => node.layer === layer.id)) continue;
      const y = layerHeights(this.settings, this.model.layers).get(layer.id);
      const plane = new T.Mesh(
        new T.PlaneGeometry(Math.max(500, size.x + 180), Math.max(500, size.z + 180)),
        new T.MeshBasicMaterial({
          color: layer.color,
          transparent: true,
          opacity: 0.025,
          side: T.DoubleSide,
          depthWrite: false,
        }),
      );
      plane.rotation.x = -Math.PI / 2;
      plane.position.set(center.x, y, center.z);
      plane.userData.boLayer = layer.id;
      plane.renderOrder = -3;
      this.group.add(plane);
      const label = document.createElement("div");
      label.className = "spatial-layer-label";
      label.textContent = t(layer.label);
      this.labels.append(label);
      label.title = t("Focus layer");
      label.onclick = () => this.callbacks.onLayer?.(layer.id);
      this.labelItems.push({
        el: label,
        position: { x: bounds.min.x - 85, y, z: bounds.max.z + 60 },
        offset: 0,
      });
    }
  }

  /** Smooth curves are batched into one GPU draw, with gaps for conceptual relations. */
  edgeColor(edge) {
    const { selected, focusContext } = this.input;
    const color = new T.Color(relationStyle(edge).color);
    const related = edge.members?.some((member) => focusContext.edges.has(member.id));
    const dim =
      focusContext.active &&
      !focusContext.edges.has(edge.id) &&
      !related &&
      edge.from !== selected &&
      edge.to !== selected;
    if (dim || edge.guide) color.lerp(new T.Color(0xf6f8fa), edge.guide ? 0.55 : 0.8);
    return color;
  }

  /** Batch the accepted or current-preview paths used by both picking and playback. */
  drawEdges(matrix) {
    const selected = this.input.selected;
    const positions = [],
      colors = [],
      arrows = [];
    this.edgeSegments = [];
    this.lines = null;
    this.arrowMesh = null;
    this.arrowEdges = [];
    const guides = this.settings.projections
      ? this.volumes
          .filter((volume) => volume.projection)
          .map((volume) => ({
            id: `projection:${volume.id}:${volume.layer}`,
            from: volume.id,
            to: volume.id,
            type: "contains",
            guide: true,
            fromPosition: this.positions[volume.id],
            toPosition: volume.center,
          }))
      : [];
    for (const edge of [...this.model.edges, ...guides]) {
      let start = edge.fromPosition || this.positions[edge.from],
        end = edge.toPosition || this.positions[edge.to];
      if (!start || !end) continue;
      let curve;
      if (edge.guide) curve = edgeCurve(start, end, "curve");
      else {
        const routed = this.router.routes.get(edge.id);
        if (!routed) continue;
        const points = routed.map((p) => ({ x: p.x, y: p.level, z: p.y }));
        curve = new T.Curve();
        curve.getPoint = (t, target = new T.Vector3()) => target.copy(polylineAt(points, t));
        curve.boPoints = points;
      }
      this.curves.set(edge.id, curve);
      const style = relationStyle(edge),
        color = this.edgeColor(edge),
        segmentStart = positions.length / 6;
      // At whole-graph scale, fewer curve samples reduce GPU overdraw. Focused
      // relations retain full detail; their underlying cubic path is unchanged.
      const focused = edge.from === selected || edge.to === selected;
      const samples =
        curve.boPoints || curve.getPoints(this.model.edges.length > 5000 && !focused ? 10 : 24);
      const dash = edge.guide ? [10, 7] : style.dash;
      for (const [a, b] of strokeSegments(
        samples,
        dash,
        this.model.edges.length > 5000 ? 12 : 64,
      )) {
        positions.push(a.x, a.y, a.z, b.x, b.y, b.z);
        colors.push(color.r, color.g, color.b, color.r, color.g, color.b);
      }
      this.edgeSegments.push({
        edge,
        start: segmentStart,
        end: positions.length / 6,
      });
      if (!edge.guide) arrows.push({ edge, curve, color });
    }
    if (positions.length) {
      const geometry = new T.LineSegmentsGeometry();
      geometry.setPositions(positions);
      geometry.setColors(colors);
      const material = new T.LineMaterial({
        vertexColors: true,
        linewidth: 1.4,
        transparent: true,
        opacity: 0.88,
        depthWrite: false,
      });
      material.resolution.set(this.host.clientWidth, this.host.clientHeight);
      this.lines = new T.LineSegments2(geometry, material);
      this.group.add(this.lines);
    }
    if (arrows.length) {
      const mesh = new T.InstancedMesh(
        new T.ConeGeometry(3.4, 11, 7),
        new T.MeshBasicMaterial(),
        arrows.length,
      );
      const up = new T.Vector3(0, 1, 0);
      for (const [i, { curve, color }] of arrows.entries()) {
        matrix.scale.setScalar(1);
        matrix.position.copy(curve.getPoint(0.84));
        matrix.quaternion.setFromUnitVectors(up, curve.getTangent(0.84).normalize());
        matrix.updateMatrix();
        mesh.setMatrixAt(i, matrix.matrix);
        mesh.setColorAt(i, color);
      }
      mesh.computeBoundingSphere();
      this.arrowMesh = mesh;
      this.arrowEdges = arrows.map((item) => item.edge);
      this.group.add(mesh);
    }
  }

  /** Ray picking uses actual perspective geometry; transparent shells yield to inner nodes. */
  pick(clientX, clientY) {
    const rect = this.canvas.getBoundingClientRect();
    this.raycaster.setFromCamera(
      new T.Vector2(
        ((clientX - rect.left) / rect.width) * 2 - 1,
        (-(clientY - rect.top) / rect.height) * 2 + 1,
      ),
      this.camera,
    );
    const hit = this.raycaster.intersectObjects(this.pickable || [], false)[0];
    if (hit) return { id: hit.object.userData.ids[hit.instanceId] };
    // Open icon strokes have empty centers. Keep the full circular interaction
    // target on the node's own plane, rather than requiring a stroke-perfect click.
    const targets = [];
    for (const node of this.model?.nodes || [])
      if (node.glyph) {
        const p = this.positions[node.id];
        if (!p) continue;
        const q = this.raycaster.ray.intersectPlane(
          new T.Plane(new T.Vector3(0, 1, 0), -p.y),
          new T.Vector3(),
        );
        if (q && Math.hypot(q.x - p.x, q.z - p.z) <= 28)
          targets.push({
            id: node.id,
            distance: q.distanceTo(this.raycaster.ray.origin),
          });
      }
    if (targets.length) return targets.sort((a, b) => a.distance - b.distance)[0];
    const under = [];
    for (const volume of this.volumes || []) {
      if (volume.projection && !this.settings.projections) continue;
      const point = this.raycaster.ray.intersectPlane(
        new T.Plane(new T.Vector3(0, 1, 0), -volume.center.y),
        new T.Vector3(),
      );
      if (point && Math.hypot(point.x - volume.center.x, point.z - volume.center.z) < volume.radius)
        under.push({
          ...volume,
          distance: point.distanceTo(this.raycaster.ray.origin),
        });
    }
    // Visible edge strokes take precedence over empty region space. Test the
    // projected segments, not isolated samples that leave gaps in the hit target.
    const choices = [];
    for (const edge of this.model?.edges || []) {
      const curve = this.curves.get(edge.id);
      const points = (curve?.boPoints || curve?.getPoints(16) || []).map((p) => this.screen(p));
      for (let i = 1; i < points.length; i++) {
        const a = points[i - 1],
          b = points[i];
        if (!a.visible || !b.visible) continue;
        const dx = b.x - a.x,
          dy = b.y - a.y;
        const px = clientX - rect.left - a.x,
          py = clientY - rect.top - a.y;
        const ratio = Math.max(0, Math.min(1, (px * dx + py * dy) / (dx * dx + dy * dy || 1)));
        if (Math.hypot(px - ratio * dx, py - ratio * dy) < 5) {
          choices.push(edge);
          break;
        }
      }
    }
    if (choices.length) return { edge: { ...choices[0], alternatives: choices } };
    if (under.length)
      return {
        region: under.sort((a, b) => a.distance - b.distance || a.radius - b.radius)[0].id,
      };
    return null;
  }

  /** Labels and meshes share dragging, so text never starts a browser selection. */
  startDrag(event, hit) {
    if (event.button !== 0) return;
    event.preventDefault();
    const id = hit?.id || hit?.region;
    this.pointer = {
      x: event.clientX,
      y: event.clientY,
      id,
      hit,
      moved: false,
    };
    if (!id) return;
    const rect = this.canvas.getBoundingClientRect();
    this.raycaster.setFromCamera(
      new T.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        1 - ((event.clientY - rect.top) / rect.height) * 2,
      ),
      this.camera,
    );
    this.callbacks.onSelect?.(id);
    this.controls.enabled = false;
    const normal = this.camera.getWorldDirection(new T.Vector3());
    this.dragPlane = new T.Plane().setFromNormalAndCoplanarPoint(
      normal,
      vector(this.positions[id]),
    );
    this.dragOrigin = this.raycaster.ray.intersectPlane(this.dragPlane, new T.Vector3());
    this.dragPositions = structuredClone(this.positions);
    this.dragIds = this.branch(id);
    this.canvas.setPointerCapture(event.pointerId);
    event.stopImmediatePropagation();
  }

  /** Coordinate ray picking, branch drag and camera gestures on the same viewport. */
  installPointer() {
    // Capture runs before OrbitControls: dragging a node/group does not orbit the camera.
    this.canvas.addEventListener(
      "pointerdown",
      (event) => this.startDrag(event, this.pick(event.clientX, event.clientY)),
      true,
    );
    this.canvas.addEventListener("pointermove", (event) => {
      const start = this.pointer;
      if (!start) return;
      if (Math.hypot(event.clientX - start.x, event.clientY - start.y) > 4) start.moved = true;
      if (!start.id || !start.moved || !this.dragOrigin) return;
      const rect = this.canvas.getBoundingClientRect();
      this.raycaster.setFromCamera(
        new T.Vector2(
          ((event.clientX - rect.left) / rect.width) * 2 - 1,
          (-(event.clientY - rect.top) / rect.height) * 2 + 1,
        ),
        this.camera,
      );
      const point = this.raycaster.ray.intersectPlane(this.dragPlane, new T.Vector3());
      if (!point) return;
      const delta = point.sub(this.dragOrigin);
      for (const id of this.dragIds) {
        const p = this.dragPositions[id];
        if (p) this.positions[id] = { ...p, x: p.x + delta.x, z: p.z + delta.z };
      }
      // Invalidate pending worker results before moving the same group.
      this.epoch++;
      this.busy = false;
      this.rebuild();
    });
    const end = (event) => {
      const start = this.pointer;
      if (!start) return;
      this.pointer = null;
      this.controls.enabled = this.visible;
      if (this.canvas.hasPointerCapture(event.pointerId))
        this.canvas.releasePointerCapture(event.pointerId);
      if (!start.moved && !start.id) {
        if (start.hit?.edge) this.callbacks.onEdge?.(start.hit.edge);
        else this.callbacks.onSelect?.(null);
      }
      this.callbacks.onSave?.();
    };
    this.canvas.addEventListener("pointerup", end);
    this.canvas.addEventListener("pointercancel", end);
    this.canvas.addEventListener("dblclick", (event) => {
      const hit = this.pick(event.clientX, event.clientY),
        id = hit?.id || hit?.region;
      if (id) this.callbacks.onToggle?.(id);
    });
    this.canvas.addEventListener("contextmenu", (event) => {
      event.preventDefault();
      const hit = this.pick(event.clientX, event.clientY);
      this.callbacks.onMenu?.(hit, event.clientX, event.clientY);
    });
  }

  /** Read cached dimensions: label writes must not trigger a layout read per point. */
  screen(point) {
    const p = (point instanceof T.Vector3 ? point.clone() : vector(point)).project(this.camera);
    return {
      x: ((p.x + 1) * this.viewportSize.width) / 2,
      y: ((1 - p.y) * this.viewportSize.height) / 2,
      depth: p.z,
      visible: p.z > -1 && p.z < 1 && Math.abs(p.x) < 1.15 && Math.abs(p.y) < 1.15,
    };
  }
  screenEdge(id) {
    const curve = this.curves?.get(id);
    return curve
      ? {
          start: this.screen(curve.getPoint(0)),
          end: this.screen(curve.getPoint(1)),
        }
      : {};
  }

  screenNode(id) {
    return this.positions[id] ? this.screen(this.positions[id]) : null;
  }

  fit(id = null, angle = this.settings?.camera || "top") {
    if (!this.model) return;
    const ids = id ? descendants(this.model, id) : new Set(this.model.nodes.map((n) => n.id));
    const points = [...ids]
      .map((key) => this.positions[key])
      .filter(Boolean)
      .map(vector);
    if (!points.length) return;
    const box = new T.Box3().setFromPoints(points),
      center = box.getCenter(new T.Vector3());
    const radius = Math.max(160, box.getSize(new T.Vector3()).length() / 2 + 100);
    const distance =
      (radius / Math.sin(T.MathUtils.degToRad(this.camera.fov) / 2)) *
      (this.camera.aspect < 1 ? 1 / this.camera.aspect : 1);
    this.controls.target.copy(center);
    this.camera.position
      .copy(center)
      .add(new T.Vector3(...cameraDirections[angle]).normalize().multiplyScalar(distance));
    this.controls.update();
    this.schedule();
  }
  zoom(factor) {
    this.camera.position
      .sub(this.controls.target)
      .multiplyScalar(1 / factor)
      .add(this.controls.target);
    this.controls.update();
    this.schedule();
    this.callbacks.onSave?.();
  }
  setPinned(id, pinned) {
    if (this.positions[id]) this.positions[id].pinned = pinned;
    this.callbacks.onSave?.();
  }
  /** Move a containment branch together while preserving its layer elevations. */
  branch(id) {
    return descendants({ nodes: [...this.input.graph.all.values()] }, id);
  }

  /** Carry visible and saved descendants together without moving unrelated branches. */
  moveGroup(id, dx, dz) {
    if (!this.model) return;
    this.epoch++;
    this.busy = false;
    for (const key of this.branch(id)) {
      const p = this.positions[key];
      if (p) {
        p.x += dx;
        p.z += dz;
      }
    }
    this.rebuild();
    this.callbacks.onSave?.();
  }
  resize() {
    const w = Math.max(1, this.host.clientWidth),
      h = Math.max(1, this.host.clientHeight);
    this.viewportSize = { width: w, height: h };
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.lines?.material.resolution.set(w, h);
    this.schedule();
  }
  animate(ids, transfers) {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    this.animation = { ids, transfers, start: performance.now() };
    const owners = new Set(
      (this.input.boDetail?.rows || []).flatMap((row) => row.owners || [row.owner]),
    );
    for (const item of this.labelItems || [])
      if (owners.has(item.id))
        item.el.animate?.([{ opacity: 0.4 }, { opacity: 1 }, { opacity: 1 }], {
          duration: 650,
        });
    this.schedule();
  }
  stopAnimation() {
    this.animation = null;
    if (this.particles) this.particles.visible = false;
    this.schedule();
  }
  /** Animate retained transfer facts along the same paths as the visible relations. */
  updateParticles(now) {
    if (!this.animation || now - this.animation.start > 650) {
      this.animation = null;
      if (this.particles) this.particles.visible = false;
      return;
    }
    const active = this.animation.ids.filter((id) => this.curves.has(id));
    if (!this.particles || this.particles.instanceMatrix.count < active.length) {
      if (this.particles) {
        this.scene.remove(this.particles);
        this.particles.geometry.dispose();
        this.particles.material.dispose();
      }
      this.particles = new T.InstancedMesh(
        new T.SphereGeometry(4.5, 10, 8),
        new T.MeshBasicMaterial({ color: 0x196f9a }),
        Math.max(1, active.length),
      );
      this.scene.add(this.particles);
    }
    this.particles.visible = true;
    this.particles.count = active.length;
    const matrix = new T.Object3D(),
      progress = (now - this.animation.start) / 650;
    for (const [i, id] of active.entries()) {
      matrix.position.copy(
        this.curves
          .get(id)
          .getPoint(this.animation.transfers.get(id)?.reverse ? 1 - progress : progress),
      );
      matrix.updateMatrix();
      this.particles.setMatrixAt(i, matrix.matrix);
    }
    this.particles.instanceMatrix.needsUpdate = true;
    this.particles.computeBoundingSphere();
  }

  /** Coalesce input and worker updates into at most one pending animation frame. */
  schedule() {
    if (this.frame || !this.visible || this.disposed || this.lost || document.hidden) return;
    this.frame = requestAnimationFrame((now) => this.render(now));
  }
  /** Render on demand, cache viewport measurements and retain bounded timing samples. */
  render(now) {
    this.frame = null;
    if (!this.visible || this.disposed || this.lost || document.hidden) return;
    const start = performance.now(),
      moving = this.controls.update();
    this.updateParticles(now);
    this.renderer.render(this.scene, this.camera);
    // Labels with colliding screen rectangles yield to selected/region labels.
    const occupied = new Set();
    for (const item of this.labelItems || []) {
      const p = item.volume
        ? regionLabelAnchor(item.volume, (p) => this.screen(p))
        : this.screen(item.position || this.positions[item.id]);
      const key = `${Math.round(p.x / 145)}:${Math.round(p.y / 42)}`;
      const visible =
        p.visible && (item.volume || !occupied.has(key) || item.id === this.input.selected);
      item.el.hidden = !visible;
      if (visible) {
        occupied.add(key);
        item.el.style.transform = `translate(${p.x}px,${p.y + item.offset}px) translate(-50%,0)`;
      }
    }
    this.frames.push(performance.now() - start);
    if (this.frames.length > 120) this.frames.shift();
    this.frameCount++;
    this.callbacks.onRender?.();
    if (moving || this.animation) this.schedule();
  }
  pause() {
    cancelAnimationFrame(this.frame);
    this.frame = null;
  }
  /** Return personal spatial settings only; no model or recorded evidence is copied. */
  snapshot() {
    return {
      positions: structuredClone(this.positions),
      camera: {
        position: this.camera.position.toArray(),
        target: this.controls.target.toArray(),
      },
    };
  }
  /** Cancel an in-flight solve before restoring a user's previous spatial layout. */
  restore(snapshot) {
    this.epoch++;
    this.busy = false;
    this.pendingFit = false;
    this.positions = structuredClone(snapshot.positions);
    this.seedMissing();
    this.settled = new Set(Object.keys(this.positions));
    this.camera.position.fromArray(snapshot.camera.position);
    this.controls.target.fromArray(snapshot.camera.target);
    this.controls.update();
    this.rebuild();
    this.callbacks.onSave?.();
  }
  get diagnostics() {
    const sorted = [...this.frames].sort((a, b) => a - b);
    return {
      renderer: "Three.js",
      nodeRendering: "instanced-mesh",
      perspective: this.camera.isPerspectiveCamera,
      webgl: !!this.renderer.getContext(),
      nodes: this.model?.nodes.length || 0,
      edges: this.model?.edges.length || 0,
      labels: this.labelItems?.length || 0,
      drawCalls: this.renderer.info.render.calls,
      geometries: this.renderer.info.memory.geometries,
      frames: this.frameCount,
      renderP95Ms: sorted[Math.floor(sorted.length * 0.95)] || 0,
      layoutMs: this.layoutMs || 0,
      busy: !!this.busy,
      routing: cleanRoute(this.input?.routing),
      routeSolver: this.router.stats,
      animation: this.animation ? { start: this.animation.start, ids: this.animation.ids } : null,
      edgePorts: [...(this.curves || [])].slice(0, 500).map(([id, curve]) => ({
        id,
        start: curve.getPoint(0),
        midpoint: curve.getPoint(0.5),
        end: curve.getPoint(1),
        vertices: curve.boPoints?.length || 25,
      })),
      volumes: this.volumes || [],
      layerPlanes: (this.group?.children || [])
        .filter((item) => item.userData.boLayer)
        .map((item) => ({ id: item.userData.boLayer, y: item.position.y })),
      camera: this.snapshot().camera,
    };
  }
  /** Release workers, controls, buffers and contexts when the viewport is removed. */
  dispose() {
    this.disposed = true;
    this.pause();
    this.worker.terminate();
    this.router.dispose();
    this.controls.dispose();
    this.clearScene();
    if (this.particles) {
      this.particles.geometry.dispose();
      this.particles.material.dispose();
    }
    this.renderer.dispose();
    this.renderer.forceContextLoss();
    document.removeEventListener("visibilitychange", this.onVisibility);
    this.canvas.remove();
    this.labels.remove();
  }
}
