# Spatial graph

New spatial views reuse known planar node centers as their initial X/Z coordinates.
Arrange uses the same semantic cluster/subtree solver in both dimensions. Existing
spatial edits take precedence during incremental refresh; explicit spatial pins
also survive Arrange. Cameras and subsequent manual edits remain independent.
Bridge nodes keep their local packing distribution and receive a bounded outward
bias, so many links to one neighboring type do not collapse onto one rim point.

The 3D viewport is another renderer of the existing graph. It uses a real perspective camera, ray picking and orbit/pan/zoom controls. The business/state model and recorded evidence are unchanged.

## Module ownership

| Module | Responsibility |
|---|---|
| graph-links.js | Merge optional source slices by stable identity; follow explicit source/handler links to capture owners. |
| graph-inventory.js | Assemble authored nodes, capture fields, machine states/transitions and shared references before filtering. |
| graph-layers.js | Classify semantic layers and close a layer slice over actual edge endpoints. |
| layer-ruler.js / edge-routing.js | Draw a canvas layer navigator; save order and visibility; share routed path geometry while retaining graph identities. |
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

- Breadcrumbs stay at the top. The bottom-centered bar shares 2D/3D, arrangement/undo, expansion, fit, zoom, edge shape and a uniform layer-spacing slider. The left canvas navigator draws colored plane tokens: click a token to toggle, a label to select, and drag a row to reorder. It collapses to a narrow strip. Arrows select; Space toggles; Alt + arrows reorders. A parallel hidden action tree provides keyboard and screen-reader access. No extra WebGL context is used.
- 3D starts from above; drag empty space to orbit, right-drag to pan, scroll to dolly. Top view restores the overhead view. Only visible, populated layers occupy consecutive height slots in the selected order, at the uniform gap (default 260). Legacy individual gaps are discarded; node X/Z positions, order, visibility and camera are preserved.
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

Straight, curved, orthogonal and bus modes share one worker routing engine for 2D and X/Z planes in 3D. Orthogonal/bus modes use R-tree obstacle checks to certify the actual rendered segments. Simple paths are tested first; larger planes reuse Delaunay channels with ngraph A*, and blocked local cases use separately replaceable libavoid Wasm. Typed bundles group parent scopes or spatial cells; multiple original source/target edges can share a trunk, including vertical cross-layer columns. Selecting a shared stroke exposes the original choices, rather than manufacturing a model junction.

Drag, expand/collapse, source topology and layer order/gap/visibility changes publish a new geometry epoch. Cached paths are rechecked against all current obstacles, including unrelated moved nodes. Stale routes are discarded. Routing results replace only edge buffers; node meshes, labels and camera remain intact. A blocked/overlapping endpoint or exhausted bounded search remains an explicit routing gap with a visible count; the model relation and accessible control remain available. No unsafe fallback is presented as a verified avoidance route. Straight mode connects the two current ports directly, including across layers; it never introduces doglegs. Curve mode uses sampled cubic paths with monotone elevation. It tries alternate bows around obstacles, retains curvature when space is crowded, and reports geometric intersections separately. Shape previews use current ports during routing, never old-style cached paths. This is a presentation choice, not evidence that a line is obstacle-free.

Circles containing an endpoint represent a scope that may be exited, rather than a solid obstacle. Cross-layer columns are tested against intermediate planes. Same-plane routes remain exactly on that plane. Region endpoints remain on the boundary. Smoothing is accepted only after testing its actual sampled segments. Detailed glyphs, labels and parameter text are not obstacles; the node/region silhouettes are. This is not a guarantee of minimum crossings, globally optimal paths or collision-free labels.

The canvas navigator can collapse to a narrow plane-token strip, preserving named tooltips, keyboard access, ordering and visibility. Spacing belongs to the bottom toolbar. Physical dash lengths continue across polyline vertices, with bounded tessellation on large graphs; whole path segments are never discarded to simulate dashes. Expanded child counts are plain numbers. Field labels show their native type; a gold marker identifies an actual primary-key declaration. Required/nullable/key constraints stay in details. Never infer a key from graph position.

Tabler Icons 3.49.0 supplies the 19 planar icons. Three uses original compound solid objects: tiered cylinders for a database, stacked crates for resources, a table grid, gear, state orb, hourglass and corresponding source objects. These are merged primitives, not thickened planar vectors. One geometry/material family per type is instanced across all nodes, with reduced radial detail above 2,000 nodes. The legend renders these same objects. Bodies retain type colors; actual runtime status remains a separate badge. Objects are centered on their semantic plane.

## Planar type clustering

Arrange packs actual containment subtrees first. Repeated sibling types receive local packing neighborhoods. Complete top-level subtrees then form type clusters: D3 forces position coarse cluster centers, collision forces separate footprints, and external relationships bias bridge nodes toward the relevant neighboring cluster's rim. This borrows the circular-cluster idea from [CiSE](https://github.com/iVis-at-Bilkent/cytoscape.js-cise); it does not embed that package or create synthetic model containers. The existing D3 implementation is reused in a short-lived worker. Existing manual positions and pins survive incremental updates; only an explicit Arrange recomputes unpinned placements. Dense all-to-all connections can still cross; type grouping does not change graph semantics.

References: [libavoid-js](https://github.com/Aksem/libavoid-js), [D3 bundle curves](https://d3js.org/d3-shape/curve#curveBundle), [D3 Delaunay](https://github.com/d3/d3-delaunay), [ngraph A*](https://github.com/anvaka/ngraph.path), [Tabler](https://github.com/tabler/tabler-icons), [dependency sources and replacement](vendor/README.md). No proprietary yFiles code is bundled.

Pause repeats only the current step's presentation. Steps opens inclusion checkboxes and an optional loop range. Skipped steps remain in the raw recording and in subsequent snapshot reconstruction; skipping a step never undoes its actual effects. Change details compare against the previous unfiltered view step, so skipped facts are not silently merged into another step. A loop has ordered raw event bounds, may wrap within a changed view's visible step plan, and stops safely if every step is excluded. Selections are private settings by recording ID; exported recordings remain unchanged. Reduced motion suppresses transfer animation.
