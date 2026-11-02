# Graph and Timeline repair · 2026-11-02

Status: local repairs and acceptance complete. The final full repository gate passed, including databases, installation, source/model synchronization and observer-free packages. Earlier failures and retests remain intact. No publication is part of this round.

## Scope and implementation

| Request | Cause and repair | Evidence |
| --- | --- | --- |
| Icons follow their layer | One shared nine-layer palette feeds Pixi icons, instanced 3D objects, planes, regions and layer keys. Shapes continue to identify node types. Explicit API-layer function nodes use API colors. | `tools/test_graph_usability.mjs`, `clusters-02/` |
| Readable dense layout | ELK orders a coarse graph of layer/type groups using crossing minimization; D3 packs complete containment subtrees locally. External connections bias gateway nodes toward neighboring groups. Manual pins survive; both renderers use the same planar seeds. | `clusters-02/results.json`, `spatial-performance-02/results.json` |
| Complete project structure | A separate cached file/import projection accompanies live views and new recording context. Shared Python AST and TypeScript/Vue parsing retain imports, re-exports, containment, file links and package references without creating the optional function/call index. Saved replay merges its own captured projection. Layer visibility is independent per view, so a narrow legacy overview cannot empty a focused project preset. Modern per-view lists do not repeat the legacy migration after a page reload. | `file-dependencies-01.log`, `code-graph-02.log`, `view-visibility-browser-07/result.json` |
| Timeline lifetimes and connections | Match state/activity residence by actual snapshot identity; pack parallel intervals into nonoverlapping tracks inside one layer row. Render very short intervals with a selectable minimum width; retain real durations. Horizontal handoffs have visible hooks/arrows. Clipped intervals use the display boundary without altering raw timestamps. | `lifecycle-browser-01/`, `execution-bands-03/`, `tools/test_graph_usability.mjs` |
| Layer order and distinct colors | Business → States → Rules → API → Functions/values → Project structure → Code symbols → Data operations → Data structure. Recognized former defaults migrate; explicit custom orders remain. | `tools/test_layer_order.mjs`, `layer-style.js` |
| Hierarchical recorded steps | Indentation follows qualified invocation parents and explicit entry references. Each option uses its layer color; raw event IDs/order remain unchanged. | `step-hierarchy.js`, native browser evidence |
| 3D visual balance | Larger instanced objects retain a minimum screen size; ordinary links are thinner and translucent. Selected/runtime links remain emphasized. Resize-cache dimensions avoid per-node DOM layout reads. | `spatial-performance-02/results.json` |

The prior stop-recording defect is included. Python and Node flush a fixed submitted queue prefix, including snapshots, within the original timeout. Continuing native traffic cannot extend that prefix. Settlement reports target/completed/submitted/pending counters. Real errors, drops and a stalled prefix still fail. Native refresh traffic is not filtered out as observer traffic.

A real continuous-refresh run subsequently exposed queue overflow. The shared collector now separates bounded recording ingress from JSON file serialization and clones the pinned history payload outside the admission lock. Metadata and event references still share one consistent boundary; public values remain independent. Blocked-writer and blocked-copy regressions verify that delivery continues. Queue capacity and validation rules are unchanged. Backlog groups now use the existing 64-event bound; committed batches reuse their fully validated preflight cursor and one append-log handle. Every event, source boundary, queue limit, log rotation rule and timeout remains checked. Isolated admission profiling improved from 13.78 s to 5.53 s for 2,048 old recorded events; this is not a new business run. The actual native run in `native-busy-browser-09/` then saved 15,278 events without gaps, errors or drops; all 18 exercised HTTP response boundaries joined exactly once.

Recording reads are now separated by purpose: catalog/version reads use current
graph metadata, runtime checkpoints omit the static tree, and capture start saves
its file/import context once. The public no-argument `view()` override contract
remains intact, including project-native frame/journal transformations. Ordinary
live graph views still rescan source. Source inventory now prunes only the already
ignored generated/cache trees before descent; ordinary exclusions still undergo
hidden implementation and route checks. Source changes during capture selection
reject start. Regressions cover each boundary.

Managed upgrades and both example graph generators now stage and replace files atomically, including copied viewer assets. Ownership JSON uses the existing atomic writer. Mid-upgrade failure must restore original files and metadata. This also repairs Windows errors encountered when truncating mapped files during this acceptance.

## Final acceptance

[Acceptance index](acceptance.json) · [Full gate](full-gate-09.json) · [Full log](full-gate-09.log) · [Protected files and IDs](invariants-final.json).

The two bundled projects passed verify/accept/check/recall and froze their latest managed checkpoint. The independent trial passed the same commands; its 75 protected files and 244 node IDs are unchanged. All managed runtime/viewer copies match canonical sources.

## Tested results

- Python event batching: 11 tests; capture settlement: 14; grouped log retention: 3; source graph: 31; engineering/file dependencies: 16 (one platform-specific skip); managed atomic upgrade: 2.
- Existing Node lifecycle, execution bands, routing center/rim anchors, layer migration, recorded views and shared layout checks remain enabled.
- Real SQLite/OTel registered lifecycle: running/waiting intervals, native nested call/return, mid-span recording, interval drag/seek/zoom and graph cursor parity in 2D/3D passed.
- Real concurrent SQLite workers: two complete five-layer bands, independent folding, cross-band resource handoff, same-layer links, all four route styles in both renderers, source-record immutability and zero business events from viewer controls passed.
- 20,000-event Canvas benchmark: paint P95 **24.2 ms**, seek P95 **73.9 ms**, 41 actual pointer seeks, nine layer rows. First paint failure (66.9 ms) remains in `timeline-performance-01/`.
- 4,000 nodes / 16,000 edges: render P95 **20.8 ms**, selection **22.7 ms**, **9 draw calls**, zero repeated viewport dimension reads during camera motion. Includes real picking, routing styles and a separate integrated graph. These are measurements on this host, not universal frame-rate guarantees.
- Syntax, lint and formatting: `source-quality-15.json` (126 Python modules, 94 JavaScript modules).

### Native load and all-layer evidence

- [Native recording and response comparisons](native-busy-browser-09/result.json): upload, delayed review/share notifications, authorized download, active and pending revoke, denied recipient access, and independent administrator access. Three real pages continued refreshing through Stop. [Settlement](native-busy-browser-09/stop-settlement.json) completed its fixed submitted prefix with zero pending events.
- [Visual correction](native-busy-browser-09/visual-review.json): the original native run's project screenshot was empty even though its raw-graph assertion passed. The retained result is capture evidence; the [installed-view retest](view-visibility-browser-07/result.json) verifies actual visible files, edges and 2D/3D glyphs after repairing per-view layer visibility.
- [Installed-view checks](layer-presets-browser-02/result.json): all nine primary presets render nodes and relations, including expanded file and database containers. Existing one-hop relation boundary nodes remain part of their views.
- [Nine-layer audit](layer-audit-final.json): no missing mapped source files or observed state values. State evidence comes from 11 exact native snapshot frames. Structural layers have source evidence rather than invented event activity. The optional live code slice is explicitly bounded to 400 of 844 nodes.
- [Full-layer iteration](all-layer-iteration-02/iteration.json): actual file-sharing operations and a rename iteration; source refresh, links and all nine layer memberships verified. The unmapped iteration first fails its unchanged strict gate, then passes with the source/model/probe mappings updated.

## Review boundaries

Business/state declarations and execution engines are protected by the baseline hashes in `baseline.json`. Drive/observe modes, original cases and required captures remain. The independent trial originally froze 75 files and 244 graph IDs; acceptance receipts check preservation.

Static structure does not fabricate runtime events. A short measured business function remains short. A conceptual activity spanning asynchronous work needs its own actual lifecycle registration; the viewer cannot infer that duration from a later notification. A missing historical file tree is not reconstructed from today's source.

Manual layouts/filters are retained across upgrades. Use **Arrange** to apply the new layout to an existing view; pinned positions remain fixed. Native application browser tests isolate test-only view preferences so existing project layouts are not overwritten. They use real business services, source, state, HTTP responses and recordings.

## Failure and repair trail

| Retained failure | Resolution |
| --- | --- |
| `clusters-01.log` | Sandbox could not start Chromium; actual browser tests ran on the host. |
| `timeline-performance-01/` | Indexed track boundaries instead of scanning every interval for every edge; original thresholds passed on retest. |
| `spatial-performance-01/` | Reused cached viewport dimensions; original responsiveness/geometry checks passed. |
| `examples-upgrade-01.log`, `-02.log` | Atomic file replacement and rollback avoid truncating mapped files. |
| `examples-acceptance-01.log` | Review helper now supplies both viewer paths in one managed upgrade call; original observer-source exclusions remain strict. |
| `examples-acceptance-02.log` | Ownership artifact publication uses the common atomic writer. |
| `full-gate-01.log` | Refreshed the two shipped small-example native capture adapters. |
| `full-gate-02.log` | Restored file import/re-export analysis; retained all original engineering assertions. |
| `full-gate-03.log` | Exact settlement assertion now checks all five new watermark fields. Full gate 04 passed before the final ingress-isolation change. |
| `execution-bands-01/` | Accounted for the newly automatic file layer with exact five-layer expectations. |
| `execution-bands-02/` | Replayed the captured file tree on every seek/render, not only during transient observation. |
| `native-busy-browser-01/` | Harness now opens a user-hidden Timeline through its real button before testing it; no business action occurred in that failed run. |
| `native-busy-browser-02/` | Real refresh load caused 501 queue drops. The interrupted raw recording is retained; shared admission/serialization locks were separated. Exact saved-response matching replaces the bounded live-history wait. |
| `native-busy-browser-03/` | No drops, but the two-second submitted-prefix barrier still timed out. Profiled source checks and reused safe path readers; bounded backlog batches remain at most 64. |
| `native-busy-browser-04/` | Native automatic navigation superseded a harness reload. Replaced network-idle waits with actual workspace DOM checks; stopped and retained that recording without gaps. |
| `native-busy-browser-05/` | Reusing the process disclosed the existing 2,000-event pre-context boundary and an incomplete parent. Real stop also left 287 target events pending. All gaps remain; batched publication now amortizes log I/O and avoids rerunning preflight. Each independent retest starts a new owned process and preserves old recordings/data. |
| `examples-publication-acceptance-01.log` | A mapped graph JSON file rejected in-place truncation on Windows. The archive generator now uses the existing atomic JSON writer. The delivery receipt already passed and remains frozen; archive retesting is independent. |
| `native-busy-browser-06/` | The original prefix deadline still failed with zero drops/errors; final receive counters caught up. No gap was hidden. Subsequent profiling exposed full source/history assembly during recording metadata polling and checkpoints; those readers are now independent. |
| `native-busy-browser-07/` | External diagnostic instrumentation stopped before browser settlement. Thread stacks and the retained 10,604-event interrupted file are diagnostic evidence, not a successful browser run; final acceptance uses an ordinary uninstrumented process. |
| `full-gate-05.log` | A real native project subclass implemented the existing no-argument `view()`. Kept that contract and routed checkpoint reads through the native override, with an isolated per-session context for source-tree inclusion. Added a regression; 14 capture-boundary tests passed. |
| `full-gate-06.log` | Gate launched before managed copy synchronization finished and correctly rejected stale `session.py`. Later gates start after copy synchronization and accepted example checkpoints. |
| `native-busy-browser-08/` | Real refresh overload still lost 221 events. Reused compiled packaged JSON Schema validators, read current secure source bytes with four bounded Windows I/O workers, and reuse parsed declarations only by fresh byte hashes. Schema, node, field, path and source freshness checks remain enabled. |
| `native-busy-browser-09/visual-review.json` | Raw project nodes existed, but a legacy shared visibility filter hid the rendered project layer. Per-view visibility preserves the old overview while focused views remain independently configurable. Installed-browser retest checks the display projection, actual glyphs, file nodes and edges. |
| `view-visibility-browser-01/` | Test asset interception had an incorrect Playwright callback signature; corrected the harness and retained its failure before successful candidate and installed-copy tests. |
| `examples-visibility-reload-acceptance-01.log` | The delivery graph generator still copied viewer assets by truncating existing files; Windows rejected a mapped `cluster-layout.js`. Reused the existing atomic JSON writer and `replace_copy` for generated graph/assets; business sources and scenario checks remain unchanged. |
| `visibility-reload-negative-01.log`, `view-visibility-browser-05/` | Hiding only Project in a modern per-view list was mistaken for an old eight-layer default after reload. Marked that list as current schema; unit retest and installed-browser test 07 preserve the explicit hidden layer, including after refresh. |
| `full-gate-08.log` | Installation of a relative project returned exit 2 once. The original test captured but discarded stderr in its failure message. Retained the failed gate; installation code is unchanged, a direct diagnostic install and three complete six-test isolated runs pass. Added failure-output diagnostics with the original exit/file assertions retained. The original cause is unconfirmed; the final broad gate 09 passes all six installation tests. The original failure cause remains unconfirmed. |
| `layer-presets-browser-01/` | The harness expected visible table relations while the database container was folded. Expanded the real container before testing its existing relations; nine-preset retest 02 passed. |
| `source-quality-13.log` | The two final JS files had been formatted without the repository configuration. Reapplied the pinned configuration; source-quality-14 passes unchanged lint and formatting rules. |

### Source-validation cost

Packaged protocol validators are compiled once per observer process; every envelope
still executes schema and current project/node/capture checks. A managed schema
upgrade reloads that process. Source checks continue reading current bytes on each
pass, including same-size/same-timestamp changes. Only byte-identical validated
models and exclusion AST facts are reused. Existing globally ignored cache trees
are pruned before descent; ordinary exclusions still expose hidden implementations.

## Layout references

The implementation reuses the bundled open-source engines:

- [ELK Layered](https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html): group ordering and crossing minimization.
- [ELK crossing minimization](https://eclipse.dev/elk/reference/groups/org-eclipse-elk-layered-crossingMinimization.html) and [spacing model](https://eclipse.dev/elk/documentation/tooldevelopers/graphdatastructure/spacingdocumentation.html).
- [D3 many-body force](https://d3js.org/d3-force/many-body): local bounded Barnes–Hut forces and collision packing.
- [Cytoscape layout guidance](https://blog.js.cytoscape.org/2020/05/11/layouts/): reviewed compound-graph alternatives; no additional graph engine was required.
