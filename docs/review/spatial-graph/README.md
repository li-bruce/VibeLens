# Spatial graph: implementation and acceptance

Branch: `feature/spatial-graph`. The previous planar layer projection has been replaced with a real Three.js perspective scene. Business, state, rule, function/value, data, API and optional source layers share the same graph identities and evidence.

[Architecture review](architecture.md) · [Module/source guide](../../source-guide.en.md) · [Interaction guide](../../../skills/vibelens/references/spatial-graph.md)

![Business, state, execution and data layers](browser-delivery/3d-angled.png)

## What changed

- Common inventory before filtering, ID-based source merging, common node-type classification and explicit handler/source-to-runtime links. No name-based joins.
- Real perspective camera, orbit/pan/dolly, ray picking, typed smooth curves and instanced node/arrow geometry. Runtime payloads and selected relations can show text directly on the graph.
- Parent → child depth within a layer; colored containment volumes on each affected layer; repeated regions preserve the owner's identity and highlight together. Dragging a group also moves saved folded descendants. Double-click expands actual 3D geometry.
- Worker-based 3D layout with semantic elevation, parent clusters, repulsion/collision, links, stable saved coordinates and pins. Spatial mode skips hidden 2D packing; existing 2D positions remain independent.
- Shared selection, context actions, source highlighting, filters, notes, recording/replay and project preferences. Static source declarations remain distinguishable from recorded execution.
- Indexed accessible controls and throttled geometry updates replace repeated edge searches. Nodes/arrows are instanced, curves are batched, labels are bounded/collision-filtered, and dense whole-graph views use fewer samples/faces. Runtime selection changes reuse GPU geometry.
- Native page teardown ignores visibility/animation work after disposal. Background/idle rendering pauses; buffers, controls, workers and contexts are disposed.

## Dependency decision

Three.js 0.186.1 supplies the camera, GPU rendering, picking and wide-line shaders. d3-force-3d 3.0.6 supplies the spatial solver. Both are MIT licensed; transitive notices are retained in SPATIAL-LICENSES.txt. Packages/build tooling are pinned in tools/spatial. Existing Pixi/ELK remain for the 2D view.

[3d-force-graph](https://github.com/vasturiano/3d-force-graph) was reviewed. Direct [Three.js](https://threejs.org/docs/pages/InstancedMesh) + [d3-force-3d](https://github.com/vasturiano/d3-force-3d) allows VibeLens to keep its existing graph controller, typed facts, capture ownership and cross-layer containment. Every renderer/layout asset is local; no application data goes to a graph service.

## Final verification

The [full receipt](validated/verification-summary.json) records all four phases with exit code 0. [Repository log](validated/repository-verification.log) includes `tools/verify.py --database`, the original language/protocol/state/mapping/white-box tests, database adapter contracts, both complete examples, HTTP/installation and observer-free package execution. Real SQLite operations are covered by the browser tests. This run does not claim a fresh live MongoDB/Redis/Neo4j/PostgreSQL matrix.

After that full run, a small frontend-only follow-up cached viewport dimensions and made accessible selection immediate instead of waiting for throttled camera geometry. The [exact change boundary](cache-change-boundary.json) confirms that runtime scripts, protocols and authored graph models are unchanged. The [follow-up receipt](cache-verification-final/summary.json) records fresh strict review/verification/acceptance of both complete examples, package/link checks and the relevant original frontend suites. All browser and performance evidence below is from the delivered follow-up. Original checks and independent expectations remain intact; the earlier framework receipt is not relabeled as a later candidate.

| Browser evidence | Coverage |
|---|---|
| [3D viewer](browser-delivery/result.json) | Perspective orbit, actual ray-picked drag, whole-group movement, native double-click expansion, cross-layer regions, 2D preservation, saved 3D reload, recording/replay, EN/ZH, mobile. |
| [Code/API](code-delivery/browser-result.json) | Real 3D, local/full code, source mappings, full-file parameter highlight, added/invalid/deleted source, literal API handler relations, parser failures, recording boundaries and retention. |
| [Controls](controls-delivery/result.json) | Real context menus/keyboard, notes/core/pins, language, recording failures/deletion, zero observer-only events and 390px layout. |
| [Database](database-delivery/) | Real SQLite read/process/write, commit/rollback, schema/source update, layout/filter persistence, replay and observer exclusion. |
| [Performance](performance-delivery/results.json) | Synthetic GPU and full-viewer measurements, worker responsiveness, bounded labels, geometry reuse, page teardown, zero repeated viewport reads during settled camera frames. |

Mapping, state constraints, business assertions and project checks are separate in the final example verification artifacts under [cache-examples](cache-examples/). Accepted changes are frozen under each example's `.release/stategraph/spatial-cache-20261025`.

Unchanged support-symbol classifications retain their original recorded rationale. The current decision section and exact change boundary describe this iteration; inherited wording about an earlier HTTP change is historical provenance.

## Performance boundaries

The synthetic large graph has **4,000 nodes / 16,000 edges**, 9 draw submissions and 250 labels. Selection update: **18.6 ms**. Measured render P95: **20.1 ms**. GPU: ANGLE (Intel, Intel(R) Arc(TM) B390 GPU (0x0000B080) Direct3D11 vs_5_0 ps_5_0, D3D11).

The full UI fixture has 1004 node controls and 4005 relation controls. Selection round trip: **121 ms**; renderer-portion P95 after orbit: **1.2 ms**. Renderer timing includes drawing/labels and excludes the coordinator's later callback. Selection round trip measures full-page feedback separately. Initialization includes shader compilation and DOM/control construction; its first-frame timings remain in the raw record.

These measurements include current host load and do not establish universal 60 FPS. Flat synthetic density is not proof of unlimited deeply nested graphs. Source display budgets, folding, focus and filtering remain necessary. Cold start and dense-view frame cost still leave room for further optimization. No stale or missing observation is converted into success.

## Failure, repair and retest trail

1. [Attempt 01](attempt-01/result.json): 3D scene existed but the mode switch did not schedule its first frame. Fixed the shared frame scheduling.
2. [Attempt 02](attempt-02/result.json): a layer slice retained another layer's region metadata. Filtered region membership with endpoints.
3. [Architecture preflight](preflight-architecture-failure.log): the checker parsed a new minified vendor bundle as application source. Added exact reviewed dependency hashes to both examples' existing vendor registry; the checker remains strict.
4. [Code test failure](code-3d/browser-result.json): an old assertion inspected the removed planar-projection property. Replaced it with actual perspective/semantic layer assertions; source/API expectations remain unchanged.
5. [Lifecycle failure](performance-integrated-retest/results.json): pagehide destroyed Pixi before visibilitychange attempted to clear an animation. Added disposal guards and verified native browser teardown.
6. [Layer classifier failure](layer-classification-before.log) and [repair](layer-classification-after.log): waiting/join classification diverged. The spatial classifier now reuses the common node type registry.
7. [Control test failure](controls-final/result.json): a second navigation aborted imports before the language navigation initialized. The test now waits for the same semantic readiness as its earlier steps. [Retest](controls-retest/result.json) preserves all original assertions.
8. [Dimension-read regression](dimension-read-regression-before/results.json): 1,000 nodes generated 17,440 viewport reads during camera frames. resize() now caches dimensions; screen() performs no layout reads. [Final measurement](performance-delivery/results.json) records zero.
9. [First cache follow-up](performance-cached/results.json): accessible selection could wait for the next poll when a throttled geometry update was skipped. Selection now updates immediately and rebuilt controls initialize their selected state; the original one-second feedback assertion passes without a relaxed threshold.

Earlier accepted candidates and interrupted full-suite logs remain in this directory. They are intermediate evidence, not the final delivery receipt. Performance fixture failures (an early global lookup and a route matcher that omitted query strings) are retained separately from product defects.

## Try it

Refresh the graph page and use **3D**. Drag blank space to orbit, right-drag to pan and scroll to dolly. Drag a node or region to move its branch; double-click to expand. Choose a preset angle or one layer, adjust spacing, or toggle containment projections. Right-click uses the same note/source/focus actions.

Source structure is optional: open **Local code** or **Code structure** first, then use the Source code layer filter. Recording captures actual instrumented events. Static code graphs help locate their exact capture owner; they do not create per-line execution events.

Reproduce from the repository root with Node/Chrome/Playwright configured:

```text
node tools/test_layered_view.mjs
node tools/test_layered_browser.mjs
node tools/test_code_browser.mjs
node tools/test_spatial_performance.mjs
python tools/verify.py --database
```
