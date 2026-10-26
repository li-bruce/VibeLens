import * as T from "./spatial-three.vendor.js";
import { routePoints, polylineAt } from "./edge-routing.js";

/** Same-layer curves, including self-transitions, stay exactly on their plane. */
export function edgeCurve(start, end, style = "curve", trunk) {
  const a = new T.Vector3(start.x, start.y, start.z);
  const b = new T.Vector3(end.x, end.y, end.z);
  const delta = b.clone().sub(a),
    length = delta.length();
  if (length < 0.001)
    return planar(
      new T.CubicBezierCurve3(
        a,
        a.clone().add(new T.Vector3(90, 0, 100)),
        a.clone().add(new T.Vector3(-90, 0, 100)),
        b,
      ),
      start.y,
      end.y,
    );
  if (style !== "curve") {
    const points = routePoints(start, end, style, trunk);
    const curve = new T.Curve();
    curve.getPoint = (t, target = new T.Vector3()) => target.copy(polylineAt(points, t));
    curve.boPoints = points;
    return curve;
  }
  const normal = new T.Vector3(-delta.z, 0, delta.x).normalize();
  if (!normal.lengthSq()) normal.set(1, 0, 0);
  const bend = Math.min(90, length * 0.16);
  const curve = new T.CubicBezierCurve3(
    a,
    a.clone().addScaledVector(delta, 0.32).addScaledVector(normal, bend),
    b.clone().addScaledVector(delta, -0.32).addScaledVector(normal, bend),
    b,
  );
  return planar(curve, start.y, end.y);
}

/** Preserve an exact semantic plane even after floating-point spline interpolation. */
function planar(curve, from, to) {
  if (from === to) {
    const point = curve.getPoint.bind(curve);
    curve.getPoint = (t, target) => {
      const p = point(t, target);
      p.y = from;
      return p;
    };
  }
  return curve;
}
