/** Returning keyboard focus must not repeat an already applied graph selection. */
import assert from "node:assert/strict";
import { SemanticView } from "../skills/vibelens/assets/stategraph-viewer/semantic-view.js";

// Only DOM behavior used by the accessible node list is needed for this unit.
class Element {
  dataset = {};
  attributes = new Map();
  children = [];
  append(child) {
    this.children.push(child);
  }
  replaceChildren() {
    this.children = [];
  }
  setAttribute(key, value) {
    this.attributes.set(key, value);
  }
  getAttribute(key) {
    return this.attributes.get(key);
  }
  focus() {
    document.activeElement = this;
    this.onfocus?.();
  }
}
const previousDocument = globalThis.document;
globalThis.document = { activeElement: null, createElement: () => new Element() };
try {
  const nodes = new Element(),
    edges = new Element(),
    calls = [];
  let panelOpen = false;
  const semantic = new SemanticView(nodes, edges, {
    onSelect: (id) => {
      calls.push(id);
      panelOpen = false;
      semantic.select(id);
    },
    onEdge: () => {},
  });
  const boxes = ["a", "b"].map((id) => ({
    id,
    node: { id, kind: "action", layer: "business", label: id },
    type: "business",
    kids: [],
  }));
  const graph = {
    boxes,
    all: new Map(boxes.map((box) => [box.id, box.node])),
    byId: new Map(boxes.map((box) => [box.id, box])),
  };
  const state = {
    graph,
    presentation: { glyphs: new Set(["a", "b"]), regions: new Set(), edges: [] },
    preferences: { annotations: {} },
    selected: null,
    spatial: false,
  };
  semantic.render(state);
  // Canvas selection updates accessible feedback without reconstructing nodes.
  semantic.select("a");
  panelOpen = true;
  semantic.nodeElements.get("a").focus();
  assert.deepEqual(calls, [], "Menu focus restoration must not reselect the current node");
  assert.equal(panelOpen, true, "Returning focus must keep the source/detail panel open");
  semantic.nodeElements.get("b").focus();
  assert.deepEqual(calls, ["b"], "Keyboard navigation must still select a different node");
  assert.equal(semantic.nodeElements.get("a").getAttribute("aria-pressed"), "false");
  assert.equal(semantic.nodeElements.get("b").getAttribute("aria-pressed"), "true");
  semantic.nodeElements.get("b").focus();
  assert.deepEqual(calls, ["b"]);
  semantic.render({ ...state, selected: "b" });
  assert.deepEqual(calls, ["b"], "A render may restore focus without another selection");
} finally {
  if (previousDocument === undefined) delete globalThis.document;
  else globalThis.document = previousDocument;
}
console.log("PASS: immediate selection, keyboard navigation and menu/render focus restoration.");
