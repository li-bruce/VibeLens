# Spatial graph

The 3D viewport is another renderer of the existing graph. It uses a real perspective camera, ray picking and orbit/pan/zoom controls. The business/state model and recorded evidence are unchanged.

## Module ownership

| Module | Responsibility |
|---|---|
| graph-links.js | Merge optional source slices by stable identity; follow explicit source/handler links to capture owners. |
| graph-inventory.js | Assemble authored nodes, capture fields, machine states/transitions and shared references before filtering. |
| graph-layers.js | Classify semantic layers and close a layer slice over actual edge endpoints. |
| spatial-model.js | Produce renderer-neutral nodes, edges and cross-layer containment projections. |
| spatial-layout.js / spatial-worker.js | Run deterministic 3D forces with layer, cluster, collision and pin constraints outside the UI thread. |
| spatial-renderer.js | Own camera, GPU objects, picking, bounded labels and runtime transfer particles. |
| semantic-view.js | Expose the same graph to keyboard/screen-reader controls and maintain linear-time geometry lookup. |
| viewer.js | Coordinate API snapshots, user actions, source panels and recording/replay. |

These files are in assets/stategraph-viewer. Python parsers and language adapters remain under scripts/bo_observer. They produce source facts; the viewer does not parse application source or decide business rules.

## Interaction

- The bottom-left **2D / 3D** switch changes renderer. Entering 3D starts from above; drag empty space to orbit, right-drag to pan, scroll to dolly. **Top view** restores the overhead view. Layer buttons select any combination in either mode; saved single-layer settings migrate without resetting personal positions.
- Drag a node or the empty area of its region to move its whole branch, preserving layer elevations. Double-click to expand/collapse. Keyboard/context actions share the same IDs and handlers.
- An expanded owner has a colored volume on its layer and corresponding volumes around its descendants on other layers. Projected regions retain the owner's ID and highlight together. Click a layer caption to isolate it; **All** restores every layer. The bottom-right legend follows the active renderer and shares its type-to-geometry definitions.
- Calls and actual data relations use solid curves. Logical/mapping/containment relations use dashed curves. An observed transfer can display its payload on a curve; static source relations never become executed merely because a nearby anchor ran.
- Spatial positions/pins and the perspective camera live with personal project preferences. Incremental layout fixes existing positions while placing new nodes. Explicit Arrange releases unpinned coordinates. The independent 2D layout remains intact.

Arrange, undo, fit, zoom and expansion use the same toolbar in both modes. Spatial undo cancels pending layout work before restoring positions and camera. Dragging a label uses the same node/branch identity as dragging its geometry.

## Operations, functions and event fields

The **Data operations** layer contains Q queries, writes, transactions and transformations, together with their selected event fields. A data operation can wrap multiple calls or driver events; it is not a function signature. **Functions and values** contains authored function anchors; **Source code** contains indexed declarations, formal parameters and static calls. Explicit source mapping edges connect these levels.

For example, `inputs.parameters.count` is a selected observation summary. It does not assert that the business function declares a parameter named `count`. `outputs.committed` belongs only to a transaction outcome, never to an individual write that may later roll back. Recorded input/output edges describe payload membership with dashed strokes; actual arguments/calls retain their solid relation types.

When an event field has no explicit source-symbol binding, Source loads the operation owner's complete file as context, scrolls to the owner, and highlights no token. An exact source parameter binding still highlights only its declared range. Do not invent a lexical source location for an adapter-produced value.

## Rendering and verification

Three.js 0.186.1 and d3-force-3d 3.0.6 are bundled locally. Dependencies and build tooling are pinned in tools/spatial/package-lock.json; SPATIAL-LICENSES.txt retains all runtime notices. No source, graph or layout data is sent to a remote renderer.

Nodes/arrows use instancing; wide curved segments share a GPU buffer. Selection/runtime refreshes reuse geometry. Labels are bounded and culled by screen cells. Static layout runs in a worker and has no perpetual simulation. Rendering pauses when hidden or idle; disposal releases workers, controls, buffers and contexts.

Test real perspective rotation, ray-picked drag, group movement, cross-layer containment, source highlighting, live edits, recording/replay, version invalidation, preferences, EN/ZH, and mobile controls. Measure interaction latency and frame cost at stated node/edge counts on a named GPU. Synthetic measurements are not a guarantee for arbitrary graphs or devices. Preserve original mapping, state, business and project checks.
