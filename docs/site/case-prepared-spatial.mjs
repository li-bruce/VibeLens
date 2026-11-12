/** Lazy WebGL view of the prepared scene, reusing the tool's semantic objects. */
import * as T from "./viewer/spatial-three.vendor.js";
import { nodeGeometry, nodeMaterial, transferGeometry } from "./viewer/spatial-geometry.js";
import { edgePoints, labelOf } from "./case-graph-geometry.mjs";

export function spatialGraph(host) {
  const renderer = new T.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.domElement.className = "prepared-webgl";
  // A visitor can switch back to 2D while this lazy module is still loading.
  // Keep new surfaces hidden until the current mode explicitly activates them.
  renderer.domElement.hidden = true;
  const labels = document.createElement("div");
  labels.className = "prepared-spatial-labels";
  labels.hidden = true;
  host.append(renderer.domElement, labels);
  const scene = new T.Scene();
  scene.add(new T.HemisphereLight(0xffffff, 0xb6c5cb, 2));
  const light = new T.DirectionalLight(0xffffff, 3);
  light.position.set(400, 700, 500);
  scene.add(light);
  const camera = new T.PerspectiveCamera(38, 1, 1, 8000);
  const target = new T.Vector3();
  let group = new T.Group(),
    enabled = false,
    interactive = true,
    azimuth = 0,
    elevation = 1.12,
    distance = 1450,
    fittedDistance = 1450,
    drag = null,
    frameId = 0,
    graphs = null,
    step = null,
    language = "en",
    moving = [],
    tags = [],
    meshes = [],
    lastKey = "";
  scene.add(group);
  function cameraPosition() {
    camera.position.set(
      target.x + distance * Math.cos(elevation) * Math.sin(azimuth),
      target.y + distance * Math.sin(elevation),
      target.z + distance * Math.cos(elevation) * Math.cos(azimuth),
    );
    camera.lookAt(target);
  }
  function clear() {
    group.traverse((object) => {
      object.geometry?.dispose();
      if (object.material) for (const m of [].concat(object.material)) m.dispose();
    });
    scene.remove(group);
    group = new T.Group();
    scene.add(group);
    labels.replaceChildren();
    moving = [];
    tags = [];
    meshes = [];
  }
  function build() {
    if (!graphs) return;
    clear();
    const layers = [...new Set(graphs.nodes.map((n) => n.layer))];
    const order = ["business", "state", "rule", "function", "data", "source"].filter((id) =>
      layers.includes(id),
    );
    const height = (id) => (order.length - 1 - order.indexOf(id)) * 95;
    const byId = new Map(graphs.nodes.map((n) => [n.id, n]));
    const point = (n) => new T.Vector3(n.x - 420, height(n.layer), n.y - 170);
    for (const layer of order) {
      const nodes = graphs.nodes.filter((n) => n.layer === layer),
        minX = Math.min(...nodes.map((n) => n.x)) - 75,
        maxX = Math.max(...nodes.map((n) => n.x)) + 75,
        minY = Math.min(...nodes.map((n) => n.y)) - 65,
        maxY = Math.max(...nodes.map((n) => n.y)) + 65;
      const plane = new T.Mesh(
        new T.PlaneGeometry(maxX - minX, maxY - minY),
        new T.MeshBasicMaterial({
          color: nodes[0].color,
          transparent: true,
          opacity: 0.055,
          side: T.DoubleSide,
          depthWrite: false,
        }),
      );
      plane.rotation.x = -Math.PI / 2;
      plane.position.set((minX + maxX) / 2 - 420, height(layer) - 2, (minY + maxY) / 2 - 170);
      group.add(plane);
    }
    for (const node of graphs.nodes) {
      const mesh = new T.Mesh(nodeGeometry(node.kind), nodeMaterial(node.color));
      mesh.scale.setScalar(18);
      mesh.position.copy(point(node));
      group.add(mesh);
      meshes.push({ node, mesh });
      const tag = document.createElement("span");
      tag.textContent = labelOf(node, language);
      tag.style.color = node.color;
      tag.dataset.nodeId = node.id;
      labels.append(tag);
      tags.push({ tag, point: mesh.position, node });
    }
    graphs.edges.forEach((edge, i) => {
      const a = byId.get(edge.from),
        b = byId.get(edge.to),
        p = edgePoints(edge, byId, i);
      const pts = p.map(
        ([x, z], j) =>
          new T.Vector3(
            x - 420,
            height(a.layer) + ((height(b.layer) - height(a.layer)) * j) / 3,
            z - 170,
          ),
      );
      const curve = new T.CubicBezierCurve3(...pts),
        geometry = new T.BufferGeometry().setFromPoints(curve.getPoints(40));
      const material =
        a.layer === b.layer
          ? new T.LineBasicMaterial({ color: edge.color, transparent: true, opacity: 0.72 })
          : new T.LineDashedMaterial({
              color: edge.color,
              transparent: true,
              opacity: 0.52,
              dashSize: 7,
              gapSize: 5,
            });
      const line = new T.Line(geometry, material);
      line.computeLineDistances();
      group.add(line);
      const head = new T.ArrowHelper(
        curve.getTangent(0.98).normalize(),
        curve.getPoint(0.98),
        0,
        edge.color,
        9,
        5,
      );
      group.add(head);
      const marker = new T.Mesh(transferGeometry(), new T.MeshBasicMaterial({ color: edge.color }));
      marker.scale.setScalar(0.9);
      group.add(marker);
      moving.push({ edge, curve, marker });
    });
    // Frame only the prepared scope. A narrow state view and the combined
    // overview need different distances, with the same camera direction.
    const bounds = new T.Box3().setFromObject(group),
      size = new T.Vector3();
    bounds.getCenter(target);
    bounds.getSize(size);
    const tangent = Math.tan((camera.fov * Math.PI) / 360);
    const aspect = host.clientWidth / Math.max(1, host.clientHeight);
    fittedDistance =
      Math.max(
        700,
        size.x / (2 * tangent * aspect),
        (size.z * Math.sin(elevation) + size.y * Math.cos(elevation)) / (2 * tangent),
      ) * 1.35;
    distance = fittedDistance;
    cameraPosition();
  }
  function draw(time) {
    if (!enabled) return;
    const width = host.clientWidth,
      height = host.clientHeight;
    if (
      renderer.domElement.width !== Math.round(width * renderer.getPixelRatio()) ||
      renderer.domElement.height !== Math.round(height * renderer.getPixelRatio())
    ) {
      renderer.setSize(width, height, false);
      camera.aspect = width / Math.max(1, height);
      camera.updateProjectionMatrix();
    }
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const active = new Set(step?.transfers || []),
      phase = reduced ? 0.5 : (time % 1200) / 1200;
    for (const { edge, curve, marker } of moving) {
      marker.visible = active.has(edge.id);
      if (marker.visible) {
        marker.position.copy(curve.getPoint(phase));
        marker.quaternion.setFromUnitVectors(
          new T.Vector3(0, 1, 0),
          curve.getTangent(phase).normalize(),
        );
      }
    }
    const pulse = reduced ? 0.2 : (Math.sin(time * 0.006) + 1) * 0.18;
    for (const { node, mesh } of meshes) {
      const active = node.id === step?.node || (node.value && node.value === step?.state);
      mesh.material.emissive?.set(active ? node.color : 0);
      mesh.material.emissiveIntensity = active ? pulse : 0;
    }
    for (const { tag, point, node } of tags) {
      const value = step?.samples?.[node.id]?.value;
      const operator = ["AND", "OR"].includes(node.glyph) ? node.glyph + " · " : "";
      tag.textContent =
        operator + labelOf(node, language) + (value === undefined ? "" : " · " + value);
      const p = point.clone().project(camera);
      tag.style.transform = `translate(${((p.x + 1) * width) / 2}px,${((1 - p.y) * height) / 2 + 22}px) translateX(-50%)`;
      tag.hidden = p.z > 1;
    }
    renderer.render(scene, camera);
    frameId = requestAnimationFrame(draw);
  }
  const canvas = renderer.domElement;
  canvas.oncontextmenu = (event) => event.preventDefault();
  canvas.onpointerdown = (event) => {
    if (!interactive) return;
    drag = {
      x: event.clientX,
      y: event.clientY,
      a: azimuth,
      e: elevation,
      t: target.clone(),
      button: event.button,
    };
    canvas.setPointerCapture(event.pointerId);
  };
  canvas.onpointermove = (event) => {
    if (!drag) return;
    const dx = event.clientX - drag.x,
      dy = event.clientY - drag.y;
    if (drag.button === 2) {
      target.copy(drag.t).add(new T.Vector3(-dx, 0, -dy));
    } else {
      azimuth = drag.a - dx * 0.006;
      elevation = Math.max(0.15, Math.min(1.5, drag.e + dy * 0.006));
    }
    cameraPosition();
    host.dataset.camera = `${azimuth.toFixed(2)},${elevation.toFixed(2)}`;
  };
  canvas.onpointerup = () => {
    drag = null;
  };
  canvas.addEventListener(
    "wheel",
    (event) => {
      if (!interactive) return;
      event.preventDefault();
      distance = Math.max(350, Math.min(3000, distance * Math.exp(event.deltaY * 0.001)));
      cameraPosition();
    },
    { passive: false },
  );
  return {
    render(graph, event, locale) {
      graphs = graph;
      step = event;
      language = locale;
      const key = JSON.stringify([graph, locale]);
      if (lastKey !== key) {
        lastKey = key;
        build();
      }
    },
    interact(value) {
      interactive = value;
    },
    visible(value) {
      enabled = value;
      canvas.hidden = !value;
      labels.hidden = !value;
      cancelAnimationFrame(frameId);
      if (value) frameId = requestAnimationFrame(draw);
    },
    fit() {
      distance = fittedDistance;
      azimuth = 0;
      elevation = 1.12;
      cameraPosition();
    },
    destroy() {
      enabled = false;
      cancelAnimationFrame(frameId);
      clear();
      renderer.dispose();
      canvas.remove();
      labels.remove();
    },
  };
}
