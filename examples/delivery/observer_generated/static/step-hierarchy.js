/** Display indentation follows witnessed calls, not layer depth or static edges. */
import { callScope, referencedParent, callKey } from "./trace-evidence.js";
import { layerOf } from "./graph-layers.js";
import { layerPalette, colorHex } from "./layer-style.js";

export function stepHierarchy(items, all, context = []) {
  const entries = new Map(),
    byId = new Map();
  const depths = new Map(),
    result = new Map();
  const visit = (event) => {
    const own = entries.get(callKey(event));
    const explicit = referencedParent(event, byId);
    const parent =
      explicit || entries.get(JSON.stringify([callScope(event), event.parent_call_id]));
    const depth = own ? depths.get(own.id) || 0 : parent ? (depths.get(parent.id) || 0) + 1 : 0;
    const layer = layerOf(all.get(event.node) || {});
    depths.set(event.id, depth);
    if (event.phase === "enter") {
      entries.set(callKey(event), event);
      entries.set(JSON.stringify([callScope(event), event.call_id]), event);
    }
    if (["return", "error"].includes(event.phase)) {
      entries.delete(callKey(event));
      entries.delete(JSON.stringify([callScope(event), event.call_id]));
    }
    byId.set(event.id, event);
    return { depth, layer, parent: parent?.id || null, color: colorHex(layerPalette[layer]) };
  };
  for (const event of context) visit(event);
  for (const [raw, event] of items.entries()) {
    result.set(raw, event.kind === "probe" ? visit(event) : { depth: 0, layer: "business" });
  }
  return result;
}
