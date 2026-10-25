# Spatial graph

The 3D viewport is another renderer of the existing graph. It uses a real perspective camera, ray picking and orbit/pan/zoom controls. The business/state model and recorded evidence are unchanged.

## Module ownership

| Module | Responsibility |
|---|---|
| graph-links.js | Merge optional source slices by stable identity; follow explicit source/handler links to capture owners. |
| graph-inventory.js | Assemble authored nodes, capture fields, machine states/transitions and shared references before filtering. |
| graph-layers.js | Classify semantic layers and close a layer slice over actual edge endpoints. |
| layer-ruler.js / edge-routing.js | Save layer order and gaps; share routed path geometry while retaining graph identities. |
| replay-selection.js | Filter playback steps and loop ranges by event ID without modifying recordings. |
| spatial-model.js | Produce renderer-neutral nodes, edges and cross-layer containment projections. |
| spatial-layout.js / spatial-worker.js | Run deterministic 3D forces with layer, cluster, collision and pin constraints outside the UI thread. |
| spatial-renderer.js | Own camera, GPU objects, picking, bounded labels and runtime transfer particles. |
| spatial-geometry.js / spatial-labels.js / spatial-paths.js | Share mesh/legend geometry, camera-relative region captions and coplanar curves. |
| machine-projection.js | Project real states, hierarchy, events and conditional transitions without executing them. |
| semantic-view.js | Expose the same graph to keyboard/screen-reader controls and maintain linear-time geometry lookup. |
| viewer.js | Coordinate API snapshots, user actions, source panels and recording/replay. |

These files are in assets/stategraph-viewer. Python parsers and language adapters remain under scripts/bo_observer. They produce source facts; the viewer does not parse application source or decide business rules.

## Interaction

- Breadcrumbs stay at the top. The bottom-centered bar shares 2D/3D, arrangement/undo, expansion, fit, zoom and edge shape. The left ruler keeps complete labels visible: click a name to select a layer, an eye to toggle visibility, drag a grip to reorder, and drag the tick below a layer to adjust its gap. Alt + Up/Down reorders the selected row; Up/Down on a gap changes spacing. The ruler header reveals a uniform gap slider. Default gaps are fixed at 260 units. Hiding a layer retains its elevation slot. Save order, individual gaps and visibility independently of coordinates.
- 3D starts from above; drag empty space to orbit, right-drag to pan, scroll to dolly. Top view restores the overhead view. Layer elevations remain stable when other layers are hidden.
- Every node center, region and same-layer curve stays on its semantic plane. Hierarchy is shown by nested colored regions, not artificial vertical offsets. Cross-layer connections keep their real endpoints. A projected region retains its owner's ID.
- Counts and live state badges accompany nodes and expanded circles in both renderers. Expanded 2D badges sit below the circle. External 3D relations end on the owner circle boundary; a real internal self relation keeps its center endpoint.
- Select a node, edge or ruler layer and press Delete to hide it in either renderer. Text fields keep normal Delete behavior. All elements restores element and layer exclusions.
- Drag geometry, a label or empty region space to move the branch. Double-click expands/collapses. Expanded regions show their name below the projected circumference; this anchor follows the camera. Ordinary labels sit below nodes with transparent backgrounds.
- The upper-right legend is vertical. Its 3D icons are WebGL renders from the same geometry factory and material family as the graph; the temporary thumbnail context is disposed after caching. Switching to 2D restores the planar glyphs.
- Spatial positions/pins/camera remain separate from 2D positions. Arrange releases unpinned coordinates; undo cancels pending layout work before restoring them. Preserve hidden descendants and their saved positions.

## Executable state projection

`machine-projection.js` reads the validated machine declaration. Every declared state has one canonical state node, and every declared transition retains its event, source, destination, conditions and exclusions. Active leaf states also activate their declared ancestors; parallel leaves remain separate. Actual nested declarations establish ancestry; underscores in flat names do not. Keep conditional transitions with the same event/source as distinct edges. Internal transitions have visible coplanar loops.

The state graph is a view of the executable declaration, not an AI business summary or a second executor. Only real journal evidence marks an executed path. If several conditional declarations share the same endpoints and the journal does not identify which was used, keep branch execution ambiguous rather than lighting every candidate. Business summaries, function calls and recorded fields remain connected but have different node roles.

The backend rejects state-value projections that omit or invent executable states. Verify declaration coverage, actual state queries, successful and rejected events, guard branches and relevant hierarchy cases. Rendering a complete declaration alone does not prove business correctness.

For each exercised drive-mode transition, correlate the native event, actual before/after state, evaluated conditions and commit witness with the public query and recording frames. Preserve skipped guards as unevaluated. A query returning only the final state and an empty journal cannot pass path-coverage checks. Add a negative case that removes a real transition witness while retaining the final state; that case must report missing evidence rather than pass from the declaration.

## Operations, functions and event fields

The **Data operations** layer contains Q queries, writes, transactions and transformations, together with their selected event fields. A data operation can wrap multiple calls or driver events; it is not a function signature. **Functions and values** contains authored function anchors; **Source code** contains indexed declarations, formal parameters and static calls. Explicit source mapping edges connect these levels.

For example, `inputs.parameters.count` is a selected observation summary. It does not assert that the business function declares a parameter named `count`. `outputs.committed` belongs only to a transaction outcome, never to an individual write that may later roll back. Recorded input/output edges describe payload membership with dashed strokes; actual arguments/calls retain their solid relation types.

When an event field has no explicit source-symbol binding, Source loads the operation owner's complete file as context, scrolls to the owner, and highlights no token. An exact source parameter binding still highlights only its declared range. Do not invent a lexical source location for an adapter-produced value.

## Rendering and verification

Three.js 0.186.1 and d3-force-3d 3.0.6 are bundled locally. Dependencies and build tooling are pinned in tools/spatial/package-lock.json; SPATIAL-LICENSES.txt retains all runtime notices. No source, graph or layout data is sent to a remote renderer.

Nodes/arrows use instancing; wide curved segments share a GPU buffer. Selection/runtime refreshes reuse geometry. Labels are bounded and culled by screen cells. Static layout runs in a worker and has no perpetual simulation. Rendering pauses when hidden or idle; disposal releases workers, controls, buffers and contexts.

Test real perspective rotation, ray-picked drag, group movement, cross-layer containment, source highlighting, live edits, recording/replay, version invalidation, preferences, EN/ZH, and mobile controls. Measure interaction latency and frame cost at stated node/edge counts on a named GPU. Synthetic measurements are not a guarantee for arbitrary graphs or devices. Preserve original mapping, state, business and project checks.

## Edge routing and replay controls

Straight, curved, orthogonal and bus paths share original endpoint IDs and solid/dashed evidence styles. Bus paths share a trunk only for edges with the same source and relation kind; each edge remains separately selectable. These are lightweight presentation routes, without obstacle-avoidance guarantees. ELK still positions nodes; saved pins and containment can move them after its solve, so stale ELK bend points are not reused.

References: [ELK routing styles](https://eclipse.dev/elk/reference/options/org-eclipse-elk-edgeRouting.html), [ELK Layered and compound graphs](https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html), [yWorks bus routing and bundling](https://www.yworks.com/products/yfiles/features.html). yWorks informs the interaction and algorithm comparison; no proprietary yFiles code is bundled. Force/hierarchical edge bundling can summarize dense overviews, but is deferred because shared curves need additional selection/disambiguation work.

Pause repeats only the current step's presentation. Steps opens inclusion checkboxes and an optional loop range. Skipped steps remain in the raw recording and in subsequent snapshot reconstruction; skipping a step never undoes its actual effects. Change details compare against the previous unfiltered view step, so skipped facts are not silently merged into another step. A loop has ordered raw event bounds, may wrap within a changed view's visible step plan, and stops safely if every step is excluded. Selections are private settings by recording ID; exported recordings remain unchanged. Reduced motion suppresses transfer animation.
