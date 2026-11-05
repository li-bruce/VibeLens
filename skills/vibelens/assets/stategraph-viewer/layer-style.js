/** Layer color is one shared identity; geometry continues to identify node type. */
export const layerPalette = Object.freeze({
  business: 0x18866b,
  state: 0x9658b5,
  rules: 0xbb7a13,
  entry: 0x327db9,
  structure: 0x6872ad,
  symbols: 0xb9654c,
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
  "code-endpoint": "entry",
  "code-directory": "structure",
  "code-file": "structure",
  "code-class": "symbols",
  "code-function": "symbols",
  "code-parameter": "symbols",
  "code-unresolved": "symbols",
  "code-reference": "symbols",
  query: "symbols",
  write: "symbols",
  transaction: "symbols",
  transform: "symbols",
  unknown: "unknown",
  store: "data",
  dataset: "data",
  column: "data",
});
export const typeColor = (type) => layerPalette[typeLayer[type] || "symbols"];
export const colorHex = (color) => "#" + color.toString(16).padStart(6, "0");
