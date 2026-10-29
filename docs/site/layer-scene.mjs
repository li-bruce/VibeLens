/** A small real WebGL scene: nine planes, shared graph objects, on-demand frames.
 * Only the visible introduction loads Three.js. Offscreen and hidden scenes stop
 * rendering; selection changes emphasis without rebuilding GPU geometry.
 */
import * as T from "./viewer/spatial-three.vendor.js";
import { nodeGeometry } from "./viewer/spatial-geometry.js";

export function layerScene(host, items, onSelect) {
  const renderer = new T.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.setClearColor(0xf5f7fa, 0);
  renderer.domElement.setAttribute("aria-hidden", "true");
  host.prepend(renderer.domElement);
  const scene = new T.Scene();
  const camera = new T.PerspectiveCamera(36, 1, 1, 12000);
  camera.position.set(980, 820, 1280);
  const controls = new T.OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 25, 0);
  controls.enableDamping = true;
  controls.enablePan = false;
  // Keep the introduction's natural page scroll; orbiting uses a drag.
  controls.enableZoom = false;
  controls.minDistance = 800;
  controls.maxDistance = 2600;
  controls.minPolarAngle = 0.28;
  controls.maxPolarAngle = Math.PI * 0.48;
  scene.add(new T.AmbientLight(0xffffff, 2));
  const light = new T.DirectionalLight(0xffffff, 2.2);
  light.position.set(3, 7, 5);
  scene.add(light);
  const planes = [],
    objects = [],
    labels = [],
    numbers = [],
    captions = [];
  const anchors = [];
  const wireMaterial = new T.LineBasicMaterial({
    color: 0x73889a,
    transparent: true,
    opacity: 0.34,
  });
  for (const [index, item] of items.entries()) {
    const group = new T.Group();
    group.position.set((index - 4) * 18, (4 - index) * 74, (index - 4) * 10);
    const surface = new T.Mesh(
      new T.BoxGeometry(570, 3, 300),
      new T.MeshPhysicalMaterial({
        color: item.color,
        transparent: true,
        opacity: 0.1,
        roughness: 0.4,
        depthWrite: false,
        side: T.DoubleSide,
      }),
    );
    surface.userData.index = index;
    group.add(surface);
    const outline = new T.LineSegments(
      new T.EdgesGeometry(surface.geometry),
      new T.LineBasicMaterial({
        color: item.color,
        transparent: true,
        opacity: 0.4,
      }),
    );
    group.add(outline);
    const geometry = nodeGeometry(item.type, true);
    const nodes = [-165, 0, 165].map((x, j) => {
      const object = new T.Mesh(
        geometry,
        new T.MeshStandardMaterial({ color: item.color, roughness: 0.38 }),
      );
      object.position.set(x, 8, j === 1 ? -30 : 25);
      object.scale.setScalar(18);
      object.userData.index = index;
      group.add(object);
      objects.push(object);
      return object;
    });
    const points = nodes.map((node) => node.position.clone());
    group.add(new T.Line(new T.BufferGeometry().setFromPoints(points), wireMaterial));
    scene.add(group);
    planes.push({ surface, outline, nodes });
    anchors.push(nodes[1].position.clone().add(group.position));
    const label = document.createElement("span");
    label.className = "layer-scene-label";
    label.textContent = String(index + 1).padStart(2, "0");
    host.append(label);
    numbers.push(label);
    labels.push({
      element: label,
      point: new T.Vector3(310, 2, 130).add(group.position),
    });
    nodes.forEach((node, column) => {
      const caption = document.createElement("span");
      caption.className = "layer-node-caption";
      host.append(caption);
      labels.push({ element: caption, point: node.position.clone().add(group.position) });
      captions.push({ element: caption, index, column });
    });
  }
  const spine = new T.Line(new T.BufferGeometry().setFromPoints(anchors), wireMaterial);
  scene.add(spine);
  let frame = 0,
    visible = true,
    active = 0;
  function schedule() {
    if (!frame && visible && !document.hidden) frame = requestAnimationFrame(draw);
  }
  function draw() {
    frame = 0;
    const moving = controls.update();
    renderer.render(scene, camera);
    const width = host.clientWidth,
      height = host.clientHeight;
    for (const { element, point } of labels) {
      const p = point.clone().project(camera);
      element.style.transform = `translate(${((p.x + 1) * width) / 2}px,${((1 - p.y) * height) / 2}px)`;
      element.hidden = Math.abs(p.z) > 1;
    }
    if (moving) schedule();
  }
  function select(index, language = 0) {
    active = index;
    planes.forEach(({ surface, outline, nodes }, i) => {
      surface.material.opacity = i === index ? 0.32 : 0.055;
      outline.material.opacity = i === index ? 0.95 : 0.23;
      nodes.forEach((node) => {
        node.material.emissive.setHex(i === index ? items[i].color : 0);
        node.material.emissiveIntensity = i === index ? 0.12 : 0;
      });
      numbers[i].classList.toggle("active", i === index);
    });
    captions.forEach((caption) => {
      caption.element.textContent = items[caption.index].examples[language][caption.column];
      caption.element.style.display = caption.index === index ? "block" : "none";
    });
    schedule();
  }
  const resize = new ResizeObserver(() => {
    const width = host.clientWidth,
      height = host.clientHeight;
    renderer.setSize(width, height, false);
    camera.aspect = width / Math.max(height, 1);
    camera.updateProjectionMatrix();
    schedule();
  });
  resize.observe(host);
  controls.addEventListener("change", schedule);
  let pressed = null;
  renderer.domElement.addEventListener(
    "pointerdown",
    (event) => (pressed = [event.clientX, event.clientY]),
  );
  renderer.domElement.addEventListener("pointerup", (event) => {
    if (!pressed || Math.hypot(event.clientX - pressed[0], event.clientY - pressed[1]) > 6) return;
    const bounds = renderer.domElement.getBoundingClientRect();
    const ray = new T.Raycaster();
    ray.setFromCamera(
      new T.Vector2(
        ((event.clientX - bounds.left) / bounds.width) * 2 - 1,
        (-(event.clientY - bounds.top) / bounds.height) * 2 + 1,
      ),
      camera,
    );
    const hit = ray.intersectObjects([...objects, ...planes.map((plane) => plane.surface)])[0];
    if (hit) onSelect(hit.object.userData.index);
  });
  document.addEventListener("visibilitychange", schedule);
  select(active);
  return {
    select,
    visible(value) {
      visible = value;
      if (!value && frame) {
        cancelAnimationFrame(frame);
        frame = 0;
      } else schedule();
    },
    reset() {
      camera.position.set(980, 820, 1280);
      controls.target.set(0, 25, 0);
      controls.update();
      schedule();
    },
  };
}
