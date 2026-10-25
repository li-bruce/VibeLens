# Viewer controls and capture semantics

Status: all 15 final verification phases passed, including the full repository suite.

Date: 2026-10-25. Branch: `feature/spatial-graph`.

## Delivered behavior

- One bottom-left toolbar: 2D/3D, multiple visible layers, arrange/undo, expand/collapse, fit, top view and zoom. The camera/layer dropdowns and layout popover are removed.
- 3D starts from above. Drag empty space to orbit; use Top view to return. Both renderers apply the same layer selection. Existing single-layer preferences migrate; personal 2D and spatial positions remain separate.
- The bottom-right legend switches between planar glyphs and the actual 3D geometry families. Narrow screens reserve the measured toolbar height for the legend and replay changes.
- Q represents a data operation (query, write or transaction), rather than a function signature. Data operations and their recorded fields have a separate layer. Actual source functions/parameters keep their own declarations and explicit source mapping edges.
- Recorded input/output edges describe event payload membership. A selected field such as `inputs.parameters.count` may be an adapter summary; it does not declare a function parameter named `count`.
- `outputs.committed` is declared only for transaction operations. Individual writes may still roll back. Invalid commit declarations on other operation types fail the strict data projection validator.
- A captured field without an explicit lexical binding opens the owner's complete file as context, with no token highlight. Explicit lexical bindings retain exact parameter highlighting. Files are still loaded on demand.
- Spatial rendering uses instanced meshes, batched curves/arrows, bounded labels and worker layout. This change does not introduce point-sprite rendering. See the primary [InstancedMesh documentation](https://threejs.org/docs/pages/InstancedMesh.html) and [Points documentation](https://threejs.org/docs/pages/Points.html).

## Failure, repair and retest

| Evidence | Finding | Resolution |
|---|---|---|
| [Initial regression](initial-failure.log) | A write incorrectly offered `committed` as a field. | Restrict generated declarations and validation to transactions; old unregenerated declarations remain readable in the viewer without showing that impossible field. |
| [Browser 01](browser-01/result.json), [02](browser-02/result.json), [03](browser-03/result.json) | A group-center test actually hit another visible field label. Text also lacked shared dragging. | Record the actual pointer target; exercise blank-region dragging in an isolated business layer. Labels now use the same drag handler as geometry. |
| [Browser 04](browser-04/result.json) | The final throttled camera update could leave new semantic controls without finite screen coordinates. | Always deliver a trailing geometry update, without delaying selection state. |
| [Browser 05](browser-05/result.json) | A visible-only layout solve discarded hidden spatial positions. | Merge its positions and retain settled IDs; verify hidden descendants move with their parent. |
| [Controls first run](controls/result.json) | The old test assumed a CSS class could never be used again, although it now contains the shared view toolbar. | Retain the original context-menu requirement and check node actions stay outside this toolbar. |
| [Strict verification first run](verification/summary.json) | The old source test required the event-field binding to be the same object as a function definition. | Assert every owner-binding attribute is retained, plus explicit context provenance. Separate browser/unit tests require zero misleading highlights and retain exact lexical highlighting. |
| [Interrupted verification](verification-retest/summary.json), [mobile screenshot](browser-final/layers-mobile-zh.png) | Human screenshot review found the new layer toolbar overlapping the mobile legend. Verification was stopped before acceptance. | Reserve actual toolbar height using ResizeObserver; add a geometric non-overlap assertion. |
| [Preview recovery](preview-recovery.json) | The first background preview was no longer reachable during a later HTTP check. | Relaunch in a persistent hidden process, preserve preferences, then verify HTTP content against nine canonical assets. Its exact termination cause was not captured. |

No business assertions were changed. The same change baseline was retained throughout; previous accepted snapshots were not rewritten.

## Final evidence

- [Strict examples and repository suite](verification-final/summary.json), including `tools/verify.py --database`.
- [Real 3D interaction and capture provenance](browser-delivery/result.json): overhead camera, mode legends, shared multi-layer controls and saved combinations across reload/mode switches, arrange/undo, real ray/label/group drag, hidden descendants, persistence, recording/replay, exact transaction outcomes, EN/ZH and 390 px non-overlap.
- [Final independent browser suites](browser-suites-final.json): original controls, optional code/source/API views, live edits and performance.
- [Real SQLite schema/query/transform/commit/rollback](database/database-browser-results.json).
- [Latest benchmark](performance-final/results.json). Timing is host-specific; renderer timing excludes coordinator callback work. This synthetic graph does not represent every nested graph or production workload.
- [Local Skill installation](local-installation.json): 190 files match the accepted source; the previous installation is backed up.
- [Live preview identity](live-preview.json). Five personal preference entries were transferred unchanged when restarting the disposable preview. No user view was reset.
- New `tools/test_viewer_semantics.mjs` runs in the repository gate. Database tests also reject a nontransaction `committed` declaration.

Fresh database execution in this round is SQLite; other adapter contract tests run in the repository suite. This report does not claim a fresh live PostgreSQL/MongoDB/Redis/Neo4j run. Captured summaries without source-symbol bindings remain context links, not exact lexical definitions.

## Use

Open [the local graph](http://127.0.0.1:8882/graph?lang=zh-CN) and refresh existing tabs. Choose 2D/3D at the bottom left; click layer buttons to combine layers, or All to restore them. Use Top view after rotating. Expand a Q to inspect recorded inputs/outputs. Source parameters appear under their actual source function in Local code / Code structure. The source panel states when it is displaying operation context.

## Maintained modules

| Module | Responsibility |
|---|---|
| `graph-layers.js` | Shared semantic classification and saved-mask migration. |
| `capture-fields.js` | Nested event fields, owner roles, input/output membership and provenance. |
| `graph-core.js`, `source-view.js` | Distinguish exact lexical bindings from owner-context navigation; load complete files lazily. |
| `glyphs.js` | Shared 2D glyphs and 3D geometry families for the legend and renderer. |
| `spatial-renderer.js` | Mesh/region/label interaction, worker results, preserved hidden positions and spatial undo. |
| `viewer.js`, `viewer.css`, `index.html` | Shared toolbar, mode coordination, final semantic geometry, responsive reservations and localization. |
| `data/contract.py`, `data/protocol.py` | Action-specific capture declaration and strict validation. |

The Skill's spatial and capture references describe these distinctions without adding business rules or another authoritative state machine.
