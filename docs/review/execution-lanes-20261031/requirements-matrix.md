# Requested changes and evidence

| Request | Maintained implementation | Verification |
| --- | --- | --- |
| One row per graph layer in each execution band | `trace-executions.js` assigns original call identities to roots; completed sequential executions reuse a band | `tools/test_trace_executions.mjs`; `native-parent-concurrent-browser/result.json` |
| Separate concurrent bands and actual cross-band dependency curves | Explicit parents/dependencies, not labels or shared node IDs | Two native SQLite workers and actual transaction release/acquire; `native-parent-midspan-browser/result.json` |
| Fold each band to its business row | Per-band collapse plus all-band control | The same actual browser tests retain the other band's rows and source recording bytes |
| Node lifetimes and same/cross-layer links | Model lifecycle resolver and shared Graph/Timeline cursor | `tests/test_database_runtime.py`; `tools/test_data_lifecycles.mjs`; actual browser recording tests |
| Straight/curved/orthogonal/bus endpoints at icon centres | Shared `layout.js` and `routing-scene.js` centre ports; expanded enclosures retain rims | All four styles tested in actual 2D/3D renderers in both concurrent browser runs |
| Correct response but missing return capture must fail | Source diagnostic for cleared exception targets, protected producer health and actual invocation closure | `tests/test_observation_continuity.py`; original failing data-exit trial and six retained negative controls |
| Observe according to each layer's properties | Source-derived `observation-plan.json`, exact capture/lifecycle/case requirements and separate per-layer evidence report | Static source and actual runtime checks remain distinct; static layers do not invent runtime facts |
| Preserve observation requirements over iterations | Project-local contracts and AGENTS validation command; `change_sync recall` before edits and from `begin` | Trial 11's withdrawal and rejection-reason requests update state, permissions, probes, native schema and cases without observation reminders. Both accepted builds have independent exact-source/event audits |
| Prevent a single request becoming several execution chains | Shared native call context in Python/Node data callbacks, including transaction bodies | Actual SQLite context regressions; Node native-file callback contract and actual captured Timeline index |
| Include native API registrations and clean project structure | Python AST registration facts, lexical handler bindings, source-first entrypoint guards and temporary-tree exclusion | 29 source-graph tests, actual code/API browser check and read-only projection of all eight real app handlers |
| Defined facts retain their actual execution owner | Python/Node ordinary record and native callbacks carry explicit parent entry IDs while preserving file identity | 18 continuity tests, actual concurrent and mid-operation SQLite/browser checks; missing-owner controls fail despite correct values and closed calls |
| Keep failed old evidence honest | Unassigned point markers retain no fabricated duration; declared external point roots remain in the node model | Read-only replay of 1,800 unchanged events: four actual invocation bands, one diagnostic band, 758 unassigned point facts |
| Focus on a rule without collecting unrelated values | Selected values retain witnessed, value-free enclosing entry/exit metadata; open-call context survives ordinary history expiry | Ten Python capture/session/HTTP regressions, native Node callbacks and `focused-boundaries-browser-04/result.json`; unselected builders remain uncalled |
| Distinguish complete and partial evidence | Complete mapping rejects missing internal owners and substituted partial boundaries; focused capture discloses actual context loss | Existing strict closure checks remain protected. The human allowed disclosed local ownership gaps; no additional mandatory acceptance gate was inferred |
| Controls work after ordinary event growth | Model-only control context preserves the same graph/build identity, observer exclusion and fixed read budget | Original trial 08 activation fails at 9,078,736 response bytes; new 9 MiB HTTP regression, real session query and existing runtime/design control browsers pass |
| Standard service exposes the same control routes | The standard HTTP handler delegates shared GET routes after its existing access/mode checks | Trial 09's original 404 is retained; actual standard-server tests and trial 11's model-only activation pass |
| Typed focus retains necessary cross-type paths | Ordinary neighbors follow requested types; original path bridges have explicit context IDs | Trial 10's rejection remains unchanged; 22 control tests, exact-input replay and fresh trial 11 UI pass with strict visible-node checks |
| Test the repaired Skill in new conversations | Ten stopped trials retain their dialogue and reasons; trial 11 passes v1 and two ordinary business iterations | Accepted stopped intervals have 38/60/61 closed calls in 153/220/209 events, with no missing interval owners. Pre-start gaps and the separately failed rapid-list capture remain disclosed |

Application acceptance is separate from component and repository checks. A passing
runtime gate in trial 04 did not prove parent ownership; that trial was stopped
without accept when the missing relations were inspected. Historical facts remain
unchanged. Trial 11 now has accepted v1, withdrawal and rejection-reason builds.
This is a coordinating-AI simulation of the user's dialogue, not independent
human usability acceptance. See the exact source/event reviews in
`dialogue-11-independent-v2/summary.json` and
`dialogue-11-independent-v3/summary.json`. The final-build process that dropped
2,701 events under rapid list loading remains incomplete evidence; acceptance of
the declared cases and stopped intervals does not erase that failure.
