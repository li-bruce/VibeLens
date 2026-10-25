import * as T from "./spatial-three.vendor.js";

/** Same-layer curves, including self-transitions, stay exactly on their plane. */
export function edgeCurve(start, end) {
  const a = new T.Vector3(start.x, start.y, start.z);
  const b = new T.Vector3(end.x, end.y, end.z);
  const delta = b.clone().sub(a),
    length = delta.length();
  if (length < 0.001)
    return new T.CubicBezierCurve3(
      a,
      a.clone().add(new T.Vector3(90, 0, 100)),
      a.clone().add(new T.Vector3(-90, 0, 100)),
      b,
    );
  const normal = new T.Vector3(-delta.z, 0, delta.x).normalize();
  if (!normal.lengthSq()) normal.set(1, 0, 0);
  const bend = Math.min(90, length * 0.16);
  return new T.CubicBezierCurve3(
    a,
    a.clone().addScaledVector(delta, 0.32).addScaledVector(normal, bend),
    b.clone().addScaledVector(delta, -0.32).addScaledVector(normal, bend),
    b,
  );
}
