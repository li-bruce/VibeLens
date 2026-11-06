/** Directional geometry for conceptual planes; never a graph transformation.
 * Stored edge identities/directions remain untouched. ELK handles cycles and
 * crossing reduction; constraints contain only declared ordering relationships.
 */
import { layerOf } from "./graph-layers.js";

const concepts = new Set(["business", "state", "rules"]);
export const conceptLayer = (node) => {
  const layer = layerOf(node);
  return concepts.has(layer) ? layer : null;
};

/** Choose ordering evidence before containment coarsens endpoints for layout. */
export function conceptOrderEdges(graph) {
  const result = [];
  for (const edge of graph.edges) {
    const source = graph.byId.get(edge.from)?.node,
      target = graph.byId.get(edge.to)?.node;
    if (!source || !target || edge.guide || edge.type === "indirect") continue;
    const layer = conceptLayer(source);
    if (!layer || layer !== conceptLayer(target)) continue;
    const allowed =
      layer === "business"
        ? ["flow", "event", "join", "retry", "cancel"]
        : layer === "state"
          ? ["transition", "declares_target"]
          : ["data", "guard", "decision_result", "depends_on"];
    if (!allowed.includes(edge.type)) continue;
    const reverse = layer === "rules" && edge.type === "depends_on";
    result.push({
      id: edge.id,
      from: reverse ? edge.to : edge.from,
      to: reverse ? edge.from : edge.to,
      layer,
    });
    // A transition concept is an explicit part of the state definition. Put it
    // between its source and target instead of treating it as an unrelated label.
    if (layer === "state" && graph.byId.has(edge.transition)) {
      result.push({ id: edge.id + ":source", from: edge.from, to: edge.transition, layer });
    }
  }
  return result;
}

/** Bound each original endpoint to its nearest displayed containment unit. */
export function unitOrderEdges(units, ordering, parents) {
  const ids = new Set(units.map((unit) => unit.id)),
    owners = new Map();
  const owner = (id) => {
    if (owners.has(id)) return owners.get(id);
    const visited = new Set();
    let current = id;
    while (current && !ids.has(current) && !visited.has(current)) {
      visited.add(current);
      current = parents.get(current);
    }
    const result = ids.has(current) ? current : null;
    owners.set(id, result);
    return result;
  };
  const result = [];
  for (const edge of ordering) {
    const from = owner(edge.from),
      to = owner(edge.to);
    if (from && to && from !== to) result.push({ ...edge, from, to });
  }
  return result;
}

/** Return circle centers. Separate components become route bands; shared nodes
 * remain single ELK vertices even when they belong to several named routes.
 */
export async function directionalUnits(elk, units, edges) {
  if (units.length < 2 || !edges.length) return null;
  const ordered = [...units].sort((a, b) => {
    const key = (unit) => (unit.node?.layout_routes || []).join("\0");
    return key(a).localeCompare(key(b)) || a.id.localeCompare(b.id);
  });
  const output = await elk.layout({
    id: "concept-flow",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.randomSeed": "42",
      "elk.edgeRouting": "ORTHOGONAL",
      "elk.spacing.nodeNode": "66",
      "elk.spacing.componentComponent": "120",
      "elk.layered.spacing.nodeNodeBetweenLayers": "105",
      "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
      "elk.layered.nodePlacement.strategy": "BRANDES_KOEPF",
    },
    children: ordered.map((unit) => ({
      id: unit.id,
      width: unit.radius * 2 + 24,
      height: unit.radius * 2 + 56,
    })),
    edges: edges.map((edge, index) => ({
      id: "ordering:" + index,
      sources: [edge.from],
      targets: [edge.to],
    })),
  });
  return new Map(
    output.children.map((node) => [
      node.id,
      {
        x: node.x + node.width / 2,
        y: node.y + node.height / 2,
      },
    ]),
  );
}

/** Recursively align expanded conceptual content before its outer footprint is
 * packed. Structural content continues to use the existing circle packer.
 */
export async function conceptTemplates(elk, graph, tree, pack) {
  const ordering = conceptOrderEdges(graph),
    overrides = new Map();
  let templates = pack(overrides);
  const levels = new Map();
  for (const [id, children] of tree.children) {
    if (children.length < 2 || !conceptLayer(graph.byId.get(id).node)) continue;
    let depth = 0,
      parent = id;
    while (tree.parents.has(parent)) {
      depth++;
      parent = tree.parents.get(parent);
    }
    if (!levels.has(depth)) levels.set(depth, []);
    levels.get(depth).push(id);
  }
  for (const depth of [...levels.keys()].sort((a, b) => b - a)) {
    for (const id of levels.get(depth)) {
      const children = tree.children.get(id).map((key) => ({
        ...templates.get(key),
        node: graph.byId.get(key).node,
      }));
      const layer = conceptLayer(graph.byId.get(id).node);
      const edges = unitOrderEdges(
        children,
        ordering.filter((edge) => edge.layer === layer),
        tree.parents,
      );
      const result = await directionalUnits(elk, children, edges);
      if (result) overrides.set(id, result);
    }
    templates = pack(overrides);
  }
  return templates;
}

/** Refine conceptual planes only; cross-plane links never distort their routes. */
export async function conceptPositions(elk, graph, tree, units, positions) {
  const ordering = conceptOrderEdges(graph);
  const byId = new Map(positions.map((point) => [point.id, point]));
  const occupied = [];
  for (const layer of concepts) {
    const members = units.filter((unit) => conceptLayer(unit.node) === layer);
    const edges = unitOrderEdges(
      members,
      ordering.filter((edge) => edge.layer === layer),
      tree.parents,
    );
    const result = await directionalUnits(elk, members, edges);
    if (!result) continue;
    const old = members.map((unit) => byId.get(unit.id));
    const dx =
      old.reduce((sum, point) => sum + point.x, 0) / old.length -
      [...result.values()].reduce((sum, point) => sum + point.x, 0) / result.size;
    const dy =
      old.reduce((sum, point) => sum + point.y, 0) / old.length -
      [...result.values()].reduce((sum, point) => sum + point.y, 0) / result.size;
    for (const [id, point] of result)
      Object.assign(byId.get(id), { x: point.x + dx, y: point.y + dy });
    // Keep each plane's directed geometry rigid when several concept planes
    // share the 2D canvas. Per-node collision nudges would scramble its ranks.
    const bounds = {
      left: Math.min(...members.map((unit) => byId.get(unit.id).x - unit.radius - 28)),
      right: Math.max(...members.map((unit) => byId.get(unit.id).x + unit.radius + 28)),
      top: Math.min(...members.map((unit) => byId.get(unit.id).y - unit.radius - 28)),
      bottom: Math.max(...members.map((unit) => byId.get(unit.id).y + unit.radius + 28)),
    };
    let shift = 0;
    for (const other of occupied) {
      if (bounds.left > other.right || bounds.right < other.left) continue;
      if (bounds.top + shift <= other.bottom + 120 && bounds.bottom + shift >= other.top - 120)
        shift = other.bottom + 120 - bounds.top;
    }
    for (const unit of members) byId.get(unit.id).y += shift;
    occupied.push({ ...bounds, top: bounds.top + shift, bottom: bounds.bottom + shift });
  }
  return positions;
}
