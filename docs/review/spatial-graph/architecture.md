# Layer integration and frontend review

## Findings and changes

| Area | Finding | Result |
|---|---|---|
| Python / JS / TS / React / Vue source | Common independent scope inventory and language-specific parsers already exist under sources.py and adapters. The optional code index shares those parser facts. | Retained. No second browser parser or language-specific rendering model introduced. |
| API entries | Literal routes link to their exact handlers. Names and coincidental text do not establish a mapping. | Retained handler edges; source mappings provide the next link to authored function/business/state/data nodes. Dynamic registrations remain unresolved. |
| Data | Catalog/contract/projection/sync modules separate static metadata from native query/transform observation. | Retained the existing common JSON event and view services; 3D uses those exact nodes and facts. |
| Runtime | Protocol validation, ingress, event history, frames, recording, retention and observer exclusion are common services. | No extra collection channel. Recording is independent of rendering mode. Source nodes remain declarations. |
| Graph assembly | Generated states, capture fields and shared membership were embedded in graph-core's display function. Optional source merge was its own ad hoc operation. | Extracted graph-inventory.js and graph-links.js. All layers assemble before filtering; source slices merge/deduplicate by stable IDs. |
| Capture from code/API | A static code node could not locate a capture owner even when an exact source mapping existed. | runtimeOwners follows explicit handler/source bindings and exact parameter parentage. Missing bindings fail; source names never imply runtime execution. |
| Layer filtering | Old projection logic dropped cross-layer parents, and slicing retained unrelated enclosure entries. | Central layer classification and endpoint-closed slicing preserve canonical parents and remove unrelated regions. |
| Type consistency | The first spatial classifier duplicated node-type conditions and misplaced waiting/join nodes. | layerOf now uses the existing nodeType registry. A failing regression and its repair are retained. |
| 3D | Previous mode projected 2D positions. | Removed layered-view.js and planar projection drawing. Real Three.js perspective scene, ray picking, curves, 3D forces and containment volumes replace it. |
| Accessibility performance | Geometry refresh repeatedly searched all edges for each edge control: quadratic work during camera updates. | Extracted SemanticView with indexed controls, linear lookup, unchanged-attribute suppression and throttled camera geometry refresh. |
| Frame cost / feedback | Per-label viewport reads interleaved with label writes; selected accessibility state also depended on throttled geometry. | Cached dimensions on resize, zero layout-dimension reads in settled camera frames, immediate selection updates and selected state on rebuilt controls. |
| Rendering | Camera and runtime changes must avoid rebuilding large geometry buffers. | Instanced nodes/arrows, batched wide curves, bounded/collision-filtered labels; selection/runtime refresh reuses geometry. Background worker layout; idle/hidden rendering pauses. |
| Dense views | Hidden planar packing and high curve/mesh detail add avoidable work. | Spatial mode skips planar packing. Dense whole-graph views reduce curve samples and sphere/cylinder detail while preserving original cubic paths and relationship identities. |
| Teardown | Native pagehide followed by visibilitychange could clear an already destroyed Pixi animation object. | Disposed viewers ignore subsequent visibility/animation work. Actual browser teardown is part of the performance regression. |
| Preferences | 2D coordinates must survive switching view modes. | Separate validated spatial coordinates/pins/camera in the existing project preference file; incremental placement preserves existing IDs. |

## Boundaries

One graph does not make every edge an execution trace. Calls, imports, states, logic, data relationships, containment and source bindings retain their types and original endpoints. Runtime status comes from actual events/frames. There is no automatic assertion that an API was requested merely because its handler's source is visible.

The code layer remains optional and bounded. When a source slice omits content, its boundary and coverage information remain visible. A failed/stale parse is reported. New application behavior still requires source-to-business reconciliation and the existing strict coding-iteration gates; arbitrary editor changes do not establish confirmed business intent.

The main viewer remains a substantial coordinator of legacy 2D actions, panels and recording. This change extracts graph assembly and accessible controls and isolates all spatial rendering, rather than replacing working ingress/recording code. Further panel decomposition is possible without changing graph semantics.

## Dependency choice

[Three.js](https://threejs.org/) provides perspective cameras, ray picking, instancing and wide-line shaders. [d3-force-3d](https://github.com/vasturiano/d3-force-3d) provides a three-dimensional force solver with spatial-tree acceleration. Both use MIT licenses; transitive notices are bundled. [3d-force-graph](https://github.com/vasturiano/3d-force-graph) was reviewed, but a direct Three.js scene better preserves VibeLens's existing selection, capture, typed edges and cross-layer containment without introducing a second graph controller. Existing ELK layouts remain available in 2D.

No proprietary layout or renderer is used. Bundles are local, reproducible from a lockfile, and checked by SHA-256 alongside existing Pixi/ELK dependencies.
