/** Layer color is one shared identity; geometry continues to identify node type. */
export const layerPalette = Object.freeze({
  business: 0x18866b,
  state: 0x9658b5,
  rules: 0xbb7a13,
  implementation: 0x327db9,
  unknown: 0x7b8490,
  data: 0x71963c,
});
export const defaultLayerOrder = Object.keys(layerPalette);
export const typeLayer = Object.freeze({
  business: "business",
  state: "state",
  wait: "state",
  decision: "rules",
  resource: "state",
  "code-endpoint": "implementation",
  "code-directory": "implementation",
  "code-file": "implementation",
  "code-class": "implementation",
  "code-function": "implementation",
  "code-parameter": "implementation",
  "code-unresolved": "implementation",
  "code-reference": "implementation",
  query: "implementation",
  write: "implementation",
  transaction: "implementation",
  transform: "implementation",
  unknown: "unknown",
  store: "data",
  dataset: "data",
  column: "data",
});
export const typeColor = (type) => layerPalette[typeLayer[type] || "implementation"];
export const colorHex = (color) => "#" + color.toString(16).padStart(6, "0");
