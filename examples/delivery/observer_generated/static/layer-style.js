/** Layer color is one shared identity; geometry continues to identify node type. */
export const layerPalette = Object.freeze({
  business: 0x18866b,
  state: 0x9658b5,
  rules: 0xbb7a13,
  api: 0xc15463,
  execution: 0x327db9,
  project: 0x8f7047,
  code: 0x6566bd,
  operations: 0x008f98,
  data: 0x71963c,
});
export const defaultLayerOrder = Object.keys(layerPalette);
export const typeLayer = Object.freeze({
  business: "business",
  state: "state",
  wait: "state",
  decision: "rules",
  resource: "rules",
  "code-endpoint": "api",
  "code-directory": "project",
  "code-file": "project",
  "code-class": "code",
  "code-function": "code",
  "code-parameter": "code",
  "code-unresolved": "code",
  query: "operations",
  transform: "operations",
  store: "data",
  dataset: "data",
  column: "data",
});
export const typeColor = (type) => layerPalette[typeLayer[type] || "execution"];
export const colorHex = (color) => "#" + color.toString(16).padStart(6, "0");
