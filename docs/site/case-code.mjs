/** Restore a native code slice from references into the immutable full index.
 * Each source node is shipped once; opening a region makes detached display
 * copies and retains the native query's exact endpoints and boundary markers.
 */
export function expandCodeSlice(code, slice) {
  if (slice.encoding !== "code-slice-refs/v1") throw Error("Unsupported code slice");
  const nodes = new Map(code.nodes.map((node) => [node.id, node]));
  const edges = new Map(code.edges.map((edge) => [edge.id, edge]));
  const selected = new Set(slice.node_ids),
    boundaries = new Set(slice.boundary_ids);
  const take = (index, id) => {
    if (!index.has(id)) throw Error("Missing recorded code element: " + id);
    return structuredClone(index.get(id));
  };
  const content = slice.node_ids.map((id) => {
    const node = take(nodes, id);
    if (boundaries.has(id)) node.code_boundary = true;
    if (boundaries.has(id) || !selected.has(node.parent)) delete node.parent;
    return node;
  });
  const metadata = Object.fromEntries(
    Object.entries(slice).filter(
      ([key]) =>
        !["encoding", "node_ids", "edge_ids", "boundary_ids", "projection_sha256"].includes(key),
    ),
  );
  return {
    ...metadata,
    nodes: content,
    edges: slice.edge_ids.map((id) => take(edges, id)),
    bindings: structuredClone(
      Object.fromEntries(Object.entries(code.bindings).filter(([id]) => selected.has(id))),
    ),
  };
}
