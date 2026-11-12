/** Keep all relationship profiles in one Three.js wide-line batch.
 * Screen-space stripes preserve their appearance as the camera rotates/zooms;
 * per-instance width/mode avoid one material or draw call per relationship.
 */
import * as T from "./spatial-three.vendor.js";
import { strokeProfiles } from "./relation-strokes.js";

function replaceShader(source, anchor, replacement) {
  if (!source.includes(anchor)) throw new Error(`Unsupported line shader: ${anchor}`);
  return source.replace(anchor, replacement);
}

export function relationLineMaterial(options = {}) {
  const material = new T.LineMaterial({ ...options, worldUnits: false });
  material.vertexShader = replaceShader(
    material.vertexShader,
    "uniform float linewidth;",
    `
    uniform float linewidth;
    attribute vec2 boStrokeProfile;
    varying float boStrokeMode;
  `,
  );
  material.vertexShader = replaceShader(
    material.vertexShader,
    "void main() {",
    `
    void main() {
      boStrokeMode = boStrokeProfile.y;
  `,
  );
  material.vertexShader = replaceShader(
    material.vertexShader,
    "offset *= linewidth;",
    "offset *= linewidth * boStrokeProfile.x;",
  );
  material.fragmentShader = replaceShader(
    material.fragmentShader,
    "void main() {",
    `
    varying float boStrokeMode;
    void main() {
  `,
  );
  material.fragmentShader = replaceShader(
    material.fragmentShader,
    "#include <color_fragment>",
    `
    #include <color_fragment>
    float stripe = abs(vUv.x);
    if (boStrokeMode > 1.5) {
      float interior = 1.0 - smoothstep(${strokeProfiles.bordered.inset - 0.08}, ${strokeProfiles.bordered.inset + 0.08}, stripe);
      diffuseColor.rgb = mix(diffuseColor.rgb, vec3(1.0), interior * ${strokeProfiles.bordered.tint});
    }
  `,
  );
  return material;
}
