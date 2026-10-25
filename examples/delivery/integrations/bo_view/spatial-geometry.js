import * as T from "./spatial-three.vendor.js";
import { iconFor } from "./node-icons.js";

/** One factory owns both the graph meshes and genuine WebGL legend thumbnails. */
export function nodeGeometry(type, dense = false) {
  const vertices = [],
    indices = [],
    sides = dense ? 4 : 6;
  // Volumetric strokes lie on X/Z, centered on the semantic layer. They are
  // genuine lit meshes, not camera-facing images or per-node DOM objects.
  for (const stroke of iconFor(type).strokes) {
    const points = stroke.filter((_, i) => !dense || i % 2 === 0 || i === stroke.length - 1);
    const base = vertices.length / 3;
    for (let i = 0; i < points.length; i++) {
      const a = points[Math.max(0, i - 1)],
        b = points[Math.min(points.length - 1, i + 1)];
      const length = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
      for (let j = 0; j < sides; j++) {
        const angle = (j * Math.PI * 2) / sides,
          r = 0.075;
        vertices.push(
          points[i][0] / 12 - ((b[1] - a[1]) / length) * Math.cos(angle) * r,
          Math.sin(angle) * 0.24,
          points[i][1] / 12 + ((b[0] - a[0]) / length) * Math.cos(angle) * r,
        );
      }
      if (i)
        for (let j = 0; j < sides; j++) {
          const n = base + i * sides + j,
            next = base + i * sides + ((j + 1) % sides);
          indices.push(n - sides, next - sides, n, next - sides, next, n);
        }
    }
    // End caps make open paths closed solids when viewed from the side.
    for (let j = 1; j < sides - 1; j++) {
      indices.push(base, base + j + 1, base + j);
      const end = base + (points.length - 1) * sides;
      indices.push(end, end + j, end + j + 1);
    }
  }
  const geometry = new T.BufferGeometry();
  geometry.setAttribute("position", new T.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  geometry.computeBoundingSphere();
  geometry.userData = { icon: iconFor(type).name, family: "Tabler", dense };
  return geometry;
}

let thumbnails;
/** Render once, then release the tiny context. No perpetual legend animation. */
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
  camera.position.set(1.4, 3.8, 2.4);
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
