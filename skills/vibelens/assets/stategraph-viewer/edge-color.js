/** Edge hue identifies its visible layer; stroke patterns identify its meaning.
 * Resolve displayed endpoints after folding/filtering, without changing the
 * original relation IDs or its path evidence. Both renderers use this rule.
 */
import { displayLayerOf } from "./implementation-planes.js";
import { layerPalette } from "./layer-style.js";

export const crossLayerColor = 0x6f7d8d;

/** Timeline rows already carry display-layer IDs; graph endpoints resolve them. */
export function layerConnectionColor(sourceLayer, targetLayer) {
  return sourceLayer === targetLayer
    ? (layerPalette[sourceLayer] ?? crossLayerColor)
    : crossLayerColor;
}

/** Accept raw model nodes or layout boxes indexed by their stable node IDs. */
export function edgeColor(edge, nodes) {
  // Projection guides connect one owner's representations on different planes;
  // their repeated owner ID does not make them a same-layer relationship.
  if (edge.guide) return crossLayerColor;
  const source = nodes?.get(edge.from),
    target = nodes?.get(edge.to);
  if (!source || !target) return crossLayerColor;
  const sourceLayer = displayLayerOf(source.node || source),
    targetLayer = displayLayerOf(target.node || target);
  return layerConnectionColor(sourceLayer, targetLayer);
}
