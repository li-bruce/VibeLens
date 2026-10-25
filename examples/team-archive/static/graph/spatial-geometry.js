import * as T from "./spatial-three.vendor.js";
import { spatialShape } from "./glyphs.js";

/** One factory owns both the graph meshes and genuine WebGL legend thumbnails. */
export function nodeGeometry(type, dense = false) {
  switch (spatialShape(type)) {
    case "capsule":
      return new T.CapsuleGeometry(0.6, 0.7, 5, 10).rotateZ(Math.PI / 2);
    case "octahedron":
      return new T.OctahedronGeometry(1);
    case "icosahedron":
      return new T.IcosahedronGeometry(1, 0);
    case "cylinder":
      return new T.CylinderGeometry(0.85, 0.85, 1.5, dense ? 10 : 18);
    case "box":
      return new T.BoxGeometry(1.4, 1.4, 1.4);
    default:
      return new T.SphereGeometry(1, dense ? 12 : 20, dense ? 8 : 12);
  }
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
  camera.position.set(2.5, 2, 3.2);
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
