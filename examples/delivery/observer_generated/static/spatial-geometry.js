import * as T from "./spatial-three.vendor.js";
import { iconFor } from "./node-icons.js";

/** Semantic objects share meaning and color with 2D icons, not their geometry. */
export const objectNames = {
  business: "workflow-blocks",
  function: "gear",
  state: "state-orb",
  decision: "decision-crystal",
  resource: "stacked-crates",
  data: "value-vial",
  effect: "commit-check",
  wait: "hourglass",
  store: "tiered-database",
  dataset: "table-grid",
  column: "field-stack",
  query: "query-lens",
  transform: "data-funnel",
  "code-endpoint": "connected-plugs",
  "code-file": "source-document",
  "code-directory": "file-folder",
  "code-class": "class-cabinet",
  "code-function": "function-chip",
  "code-parameter": "parameter-dial",
  "code-unresolved": "broken-link",
};

/** Merge small primitives once per type, allowing a single instanced draw call.
 * Geometry stays centered on its semantic plane. No per-node materials, SVG
 * extrusions, textures or separate scene objects are allocated.
 */
export function nodeGeometry(type, dense = false) {
  const parts = [],
    segments = dense ? 8 : 20;
  const add = (geometry, x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0) => {
    geometry.rotateX(rx);
    geometry.rotateY(ry);
    geometry.rotateZ(rz);
    geometry.translate(x, y, z);
    parts.push(geometry);
  };
  const box = (w, h, d, x = 0, y = 0, z = 0) => add(new T.BoxGeometry(w, h, d), x, y, z);
  const cylinder = (r, h, x = 0, y = 0, z = 0, top = r) =>
    add(new T.CylinderGeometry(top, r, h, segments), x, y, z);
  const ball = (r, x = 0, y = 0, z = 0) =>
    add(new T.SphereGeometry(r, segments, dense ? 6 : 12), x, y, z);
  const ring = (r, tube, x = 0, y = 0, z = 0, rx = Math.PI / 2) =>
    add(new T.TorusGeometry(r, tube, dense ? 4 : 8, segments), x, y, z, rx);
  const rod = (a, b, radius = 0.1) => {
    const from = new T.Vector3(...a),
      to = new T.Vector3(...b),
      delta = to.clone().sub(from);
    const g = new T.CylinderGeometry(radius, radius, delta.length(), dense ? 5 : 10);
    g.applyQuaternion(
      new T.Quaternion().setFromUnitVectors(new T.Vector3(0, 1, 0), delta.normalize()),
    );
    const mid = from.add(to).multiplyScalar(0.5);
    g.translate(mid.x, mid.y, mid.z);
    parts.push(g);
  };
  switch (type) {
    case "store":
      for (const y of [-0.6, 0, 0.6]) cylinder(0.82, 0.45, 0, y);
      break;
    case "resource":
      for (const [x, y, z] of [
        [-0.43, -0.35, 0.25],
        [0.43, -0.35, 0.25],
        [0, 0.43, -0.15],
      ])
        box(0.72, 0.7, 0.72, x, y, z);
      for (const x of [-0.43, 0.43]) cylinder(0.13, 0.12, x, -0.77, 0.25);
      break;
    case "business":
      box(1.8, 0.18, 1.45, 0, -0.55);
      for (const [x, z] of [
        [-0.55, 0.35],
        [0.55, 0.35],
        [0, -0.45],
      ]) {
        box(0.55, 0.65, 0.5, x, -0.12, z);
        ball(0.11, x, 0.29, z);
      }
      rod([-0.55, -0.35, 0.35], [0, -0.35, -0.45]);
      rod([0.55, -0.35, 0.35], [0, -0.35, -0.45]);
      break;
    case "function":
      ring(0.52, 0.19);
      for (let i = 0; i < 8; i++) {
        const a = (i * Math.PI) / 4;
        add(
          new T.BoxGeometry(0.34, 0.48, 0.35),
          Math.cos(a) * 0.75,
          0,
          Math.sin(a) * 0.75,
          0,
          -a,
          0,
        );
      }
      cylinder(0.17, 0.65);
      break;
    case "state":
      ball(0.57);
      ring(0.88, 0.1);
      break;
    case "decision":
      add(new T.OctahedronGeometry(0.98));
      cylinder(0.26, 0.12, 0, -0.85);
      break;
    case "data":
      cylinder(0.42, 0.9);
      ball(0.42, 0, 0.45);
      ball(0.42, 0, -0.45);
      ring(0.43, 0.07);
      break;
    case "effect":
      cylinder(0.86, 0.18, 0, -0.45);
      rod([-0.52, -0.05, 0.15], [-0.12, 0.3, 0.3], 0.17);
      rod([-0.12, 0.3, 0.3], [0.55, 0.65, -0.3], 0.17);
      break;
    case "wait":
      cylinder(0.65, 0.12, 0, -0.8);
      cylinder(0.65, 0.12, 0, 0.8);
      cylinder(0.04, 0.7, 0, 0.35, 0, 0.55);
      cylinder(0.55, 0.7, 0, -0.35, 0, 0.04);
      for (const x of [-0.53, 0.53]) rod([x, -0.75, 0], [x, 0.75, 0], 0.065);
      break;
    case "dataset":
      box(1.8, 0.22, 1.8, 0, -0.3);
      for (const x of [-0.56, 0, 0.56])
        for (const z of [-0.56, 0, 0.56]) box(0.44, 0.24, 0.44, x, -0.02, z);
      cylinder(0.1, 0.14, 0, -0.48);
      break;
    case "column":
      for (const y of [-0.62, 0, 0.62]) box(0.9, 0.4, 0.85, 0, y);
      cylinder(0.13, 1.6, 0.63);
      break;
    case "query":
      ring(0.57, 0.17, -0.18, 0, -0.18);
      rod([0.25, 0, 0.25], [0.92, 0, 0.92], 0.17);
      break;
    case "transform":
      cylinder(0.2, 1.1, 0, 0.15, 0, 0.85);
      cylinder(0.2, 0.6, 0, -0.65);
      break;
    case "code-endpoint":
      for (const x of [-0.65, 0.65]) {
        box(0.5, 0.62, 0.7, x);
        for (const z of [-0.2, 0.2]) rod([x * 0.5, 0, z], [x * 0.85, 0, z], 0.085);
      }
      rod([-0.25, 0, 0], [0.25, 0, 0], 0.12);
      break;
    case "code-file":
      box(1.22, 0.25, 1.65);
      for (const z of [-0.4, 0, 0.4]) box(0.78, 0.13, 0.08, -0.04, 0.2, z);
      ball(0.12, 0.5, 0.19, -0.7);
      break;
    case "code-directory":
      box(1.7, 0.22, 1.25, 0, -0.35);
      box(1.7, 0.95, 0.16, 0, 0.1, -0.62);
      box(0.65, 0.3, 0.16, -0.5, 0.65, -0.62);
      box(1.7, 0.7, 0.16, 0, -0.1, 0.58);
      if (!dense) {
        box(0.12, 0.7, 1.2, -0.8, -0.1);
        box(0.12, 0.7, 1.2, 0.8, -0.1);
        for (const z of [-0.3, 0, 0.3]) box(1.4, 0.08, 0.85, 0, 0.16 + z / 5, z);
      }
      break;
    case "code-class":
      box(1.45, 1.5, 0.95);
      for (const y of [-0.48, 0, 0.48]) {
        box(1.1, 0.28, 0.14, 0, y, 0.55);
        cylinder(0.09, 0.13, 0, y, 0.67);
      }
      break;
    case "code-function":
      box(1.15, 0.55, 1.15);
      cylinder(0.3, 0.18, 0, 0.37);
      for (const n of [-0.38, 0, 0.38]) {
        box(0.32, 0.15, 0.11, -0.72, 0, n);
        box(0.32, 0.15, 0.11, 0.72, 0, n);
      }
      break;
    case "code-parameter":
      cylinder(0.72, 0.3);
      cylinder(0.44, 0.5, 0, 0.35);
      rod([0, 0.65, 0], [0.39, 0.65, -0.39], 0.09);
      break;
    default:
      ring(0.44, 0.14, -0.4, 0, 0, 0);
      ring(0.44, 0.14, 0.4, 0, 0, Math.PI / 2);
  }
  const positions = [],
    normals = [];
  for (const part of parts) {
    const flat = part.index ? part.toNonIndexed() : part;
    positions.push(...flat.attributes.position.array);
    normals.push(...flat.attributes.normal.array);
    if (flat !== part) flat.dispose();
    part.dispose();
  }
  const geometry = new T.BufferGeometry();
  geometry.setAttribute("position", new T.Float32BufferAttribute(positions, 3));
  geometry.setAttribute("normal", new T.Float32BufferAttribute(normals, 3));
  geometry.computeBoundingSphere();
  geometry.userData = {
    object: objectNames[type] || "broken-link",
    icon: iconFor(type).name,
    family: "VibeLens solids",
    dense,
  };
  return geometry;
}

let thumbnails;
/** Render the actual objects once; release the legend's temporary WebGL context. */
export function spatialLegend(styles) {
  if (thumbnails) return thumbnails;
  const renderer = new T.WebGLRenderer({
    alpha: true,
    antialias: true,
    preserveDrawingBuffer: true,
  });
  renderer.setSize(48, 48);
  renderer.setClearColor(0, 0);
  const camera = new T.PerspectiveCamera(36, 1, 0.1, 20);
  camera.position.set(2.2, 3.4, 3.6);
  camera.lookAt(0, 0, 0);
  const scene = new T.Scene();
  scene.add(new T.AmbientLight(0xffffff, 1.3));
  const light = new T.DirectionalLight(0xffffff, 2);
  light.position.set(3, 4, 5);
  scene.add(light);
  thumbnails = new Map();
  try {
    for (const [type, style] of Object.entries(styles)) {
      const mesh = new T.Mesh(
        nodeGeometry(type),
        new T.MeshLambertMaterial({ color: style.color }),
      );
      scene.add(mesh);
      renderer.render(scene, camera);
      thumbnails.set(type, renderer.domElement.toDataURL("image/png"));
      scene.remove(mesh);
      mesh.geometry.dispose();
      mesh.material.dispose();
    }
  } finally {
    renderer.dispose();
    renderer.forceContextLoss();
  }
  return thumbnails;
}
