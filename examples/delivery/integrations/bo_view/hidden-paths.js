/** Read-only, bounded typed paths through abstracted planes.
 * An indirect connector is structural evidence, never a direct call, permission
 * grant, transition or execution. Canonical edges and runtime IDs stay intact.
 */
import { relationType } from "./graph-core.js";
import { t } from "./i18n.js";
import { conceptRelationTypes } from "./concept-relations.js";

const supported = new Set([
  "call",
  "flow",
  "transition",
  "guard",
  "data",
  "resource",
  "join",
  "contains",
  "reads",
  "writes",
  "maps",
  "references",
  "transforms",
  "code-contains",
  "code-defines",
  "code-handles",
  "code-calls",
  "code-imports",
  "code-inherits",
  "code-parameter",
  "code-maps",
  "code-links",
  "code-exports",
  "code-dependency",
  ...conceptRelationTypes,
]);
const hash = (value) => {
  let result = 2166136261;
  for (const char of JSON.stringify(value))
    result = Math.imul(result ^ char.charCodeAt(0), 16777619);
  return (result >>> 0).toString(16).padStart(8, "0");
};
const contextOf = (edge) =>
  Object.fromEntries(
    [
      "scope",
      "context",
      "condition",
      "conditions",
      "unless",
      "event",
      "mapping_role",
      "operation",
      "policy_operation",
    ]
      .filter((key) => edge[key] !== undefined)
      .map((key) => [key, edge[key]]),
  );

export function projectHiddenPaths(
  graph,
  {
    visibleIds,
    accepts,
    hiddenNodes = [],
    hiddenEdges = [],
    nodeAllowed = () => true,
    edgeTypes = null,
    maxWork = 25000,
    maxEdges = 800,
    maxDepth = 12,
    maxWitnesses = 4,
  } = {},
) {
  const nodes = graph.all,
    excluded = new Set(hiddenNodes),
    excludedEdges = new Set(hiddenEdges);
  const allowedTypes = edgeTypes && new Set(edgeTypes);
  const canonical = (id) => nodes.get(id)?.referenceOf || id;
  const allowed = (id) => {
    const seen = new Set();
    let current = nodes.get(id);
    if (!current || !nodeAllowed(current)) return false;
    while (current && !seen.has(current.id)) {
      seen.add(current.id);
      if (excluded.has(current.id) || excluded.has(current.referenceOf)) return false;
      current = nodes.get(current.parent);
    }
    return true;
  };
  const owner = (id) => {
    if (!allowed(id) || !accepts(nodes.get(id))) return null;
    const seen = new Set();
    while (id && !seen.has(id)) {
      if (visibleIds.has(id)) return id;
      seen.add(id);
      id = nodes.get(id)?.parent;
    }
    return null;
  };
  const adjacency = new Map(),
    seeds = new Map(),
    edges = new Map();
  let work = 0,
    searchComplete = true,
    witnessesComplete = true;
  const add = (from, to, edge, type, direction) => {
    if (!adjacency.has(from)) adjacency.set(from, []);
    adjacency.get(from).push({ to, edge, type, direction });
  };
  for (const edge of graph.rawEdges || graph.edges) {
    const type = relationType(edge),
      from = canonical(edge.from),
      to = canonical(edge.to);
    if (
      edge.derived ||
      excludedEdges.has(edge.id) ||
      !supported.has(type) ||
      (allowedTypes && !allowedTypes.has(type)) ||
      !allowed(from) ||
      !allowed(to) ||
      from === to
    )
      continue;
    add(from, to, edge, type, 1);
    // A read edge points from a dataset to its consumer. Its declared inverse
    // supports consumer-to-dataset inspection; other directions stay literal.
    if (type === "reads" && nodes.get(from)?.data_role === "dataset") add(to, from, edge, type, -1);
  }
  for (const id of nodes.keys()) {
    const target = owner(id);
    if (!target) continue;
    if (!seeds.has(target)) seeds.set(target, new Set());
    seeds.get(target).add(canonical(id));
  }
  const revision = hash(
    (graph.rawEdges || graph.edges).map((edge) => [
      edge.id,
      edge.from,
      edge.to,
      relationType(edge),
      contextOf(edge),
    ]),
  );
  outer: for (const [from, starts] of seeds) {
    const queue = [...starts].map((id) => ({
      id,
      nodes: [id],
      steps: [],
      contexts: [],
    }));
    const seen = new Set();
    for (let cursor = 0; cursor < queue.length; cursor++) {
      const path = queue[cursor];
      for (const step of adjacency.get(path.id) || []) {
        if (++work > maxWork) {
          searchComplete = false;
          break outer;
        }
        if (path.nodes.includes(step.to)) {
          witnessesComplete = false;
          continue;
        }
        const steps = [...path.steps, step],
          ids = [...path.nodes, step.to];
        const context = contextOf(step.edge);
        const contexts = Object.keys(context).length ? [...path.contexts, context] : path.contexts;
        const to = owner(step.to);
        if (to) {
          // A visible intermediate ends this segment. One original edge is
          // already represented by folding and must not become a duplicate path.
          if (from === to || steps.length < 2) continue;
          const meaning =
            steps.at(-1).type === "reads"
              ? "reads-via"
              : steps.at(-1).type === "writes"
                ? "writes-via"
                : "structural-path";
          const key = JSON.stringify([from, to, meaning, contexts]);
          if (!edges.has(key)) {
            if (edges.size >= maxEdges) {
              searchComplete = false;
              break outer;
            }
            const id = "view-path:" + hash(key);
            if (excludedEdges.has(id)) continue;
            edges.set(key, {
              id,
              from,
              to,
              type: "indirect",
              derived: true,
              origin: "view-projection",
              label: t("Indirect path"),
              labels: new Set([t("Indirect path")]),
              observed: false,
              current: false,
              evidence_kind: "structural",
              meaning,
              graph_revision: revision,
              members: [],
              witnesses: [],
              sourceRegion: false,
              targetRegion: false,
            });
          }
          const edge = edges.get(key);
          if (edge.witnesses.length >= maxWitnesses) {
            witnessesComplete = false;
            continue;
          }
          const witness = {
            id: "view-witness:" + hash([revision, ids, steps.map((s) => [s.edge.id, s.direction])]),
            nodes: ids,
            edges: steps.map((s) => s.edge.id),
            types: steps.map((s) => s.type),
            directions: steps.map((s) => s.direction),
            contexts,
            constraints: ids
              .filter((id) => nodes.get(id)?.operator || nodes.get(id)?.execution_role)
              .map((id) => ({
                node: id,
                operator: nodes.get(id).operator,
                execution_role: nodes.get(id).execution_role,
              })),
          };
          edge.witnesses.push(witness);
          edge.members.push({
            ...edge,
            members: undefined,
            witnesses: undefined,
            id: witness.id,
            from: ids[0],
            to: ids.at(-1),
            witness,
          });
          continue;
        }
        // Explicit filters cut traversal. Only a layer/facet abstraction permits
        // walking through a hidden node; folding alone never grants reachability.
        if (accepts(nodes.get(step.to))) continue;
        if (steps.length >= maxDepth) {
          searchComplete = false;
          continue;
        }
        const state = JSON.stringify([step.to, step.type, contexts]);
        if (seen.has(state)) {
          witnessesComplete = false;
          continue;
        }
        seen.add(state);
        queue.push({ id: step.to, nodes: ids, steps, contexts });
      }
    }
  }
  return {
    edges: [...edges.values()].map((edge) => ({
      ...edge,
      search_complete: searchComplete,
      witnesses_complete: witnessesComplete,
    })),
    graph_revision: revision,
    search_complete: searchComplete,
    witnesses_complete: witnessesComplete,
    work,
    limits: { maxWork, maxEdges, maxDepth, maxWitnesses },
  };
}
