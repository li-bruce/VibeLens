# Chronological development evidence

Status statements below refer to their recorded phase. See [current results](README.md) and [final local acceptance](final-acceptance.md).

# Execution bands and observation continuity

Work in progress on `feat/recording-timeline`, starting from `d6a7b81`.
The [task list](plan.md) records the order of work. A fresh dialogue starts after
the repaired framework and repository regressions pass.

## Changes

- Each execution band contains one row per graph layer. Sequential invocations
  reuse a completed band; overlapping independent invocations occupy another band.
  Each band folds to its business row. Depth and single-layer selection retain
  layer axes even when the selected interval has no new events on that layer.
- Lifetimes, horizontal/cross-layer links, and cross-band dependency curves use
  original captured identities and the graph's replay cursor. Sharing a function
  ID alone does not establish contention.
- Ordinary graph edges use icon centres in 2D and 3D. Expanded regions retain
  circumference ports. Straight, curved, orthogonal and bus paths share these
  coordinates with routing, picking and animation.
- `change_sync recall` restores project-local requirements, contracts, observation
  ownership, source changes and checks. `begin` produces the same summary.
  `.stategraph/observation-plan.json` derives per-layer source/field/lifecycle/case
  requirements from the existing implementation inventory.
- Python and JavaScript static scans recognize configured literal-node `span`
  APIs as well as `record`. Real cases still establish the executed boundary.
- Mapping verification audits explicit invocation closure independently of business
  results. New integrations enable protected `require_observation_closure` and
  `require_probe_health`. Python source diagnostics catch a known cleared-exception
  capture in deferred span results.
- Node captions use actual text measurements and the node's width. At small
  overview zoom, one readable line and its hit region may extend below the world
  box, just as icons retain their minimum screen size. Full names, identities,
  source links and saved coordinates remain unchanged; values use remaining space.

## Failures and repairs

| Evidence | Finding | Resolution |
| --- | --- | --- |
| `tests/test_observation_continuity.py` | A real producer loses five completion events when deferred callbacks reference Python exception targets after their handlers exit. The functions still return the expected status numbers. | Source diagnostics, capture health and missing-exit checks reject the mapping. Default-bound values preserve all five real completions. This unit test does not claim to issue HTTP requests. |
| [concurrent-01](concurrent-01/result.json), [concurrent-02](concurrent-02/result.json) | The new browser fixture's state events omitted the explicit revision required by snapshots. Strict transport rejected those snapshots. | Correct the fixture's real state event/snapshot wiring; retain health checks. |
| [concurrent-03](concurrent-03/result.json) | Route assertions ran while the graph was covered by the maximized timeline. | Restore the graph and expand the actual node before measuring rendered paths. |
| [concurrent-04](concurrent-04/result.json) | Ordinary concurrent acceptance passed. | Two SQLite workers, 29 actual events, two four-layer bands, closed lifetimes and an actual transaction release/acquire link. |
| [context-negative-01](context-negative-01.log), [concurrent-midspan-01](concurrent-midspan-01/result.json) | Two already-running invocations of the same node were conflated at the recording boundary. | Preserve context by original event identity, resolve clipped invocation ownership separately, and retain one band per concurrent root. |
| [concurrent-midspan-02](concurrent-midspan-02/result.json) | The pre-recording wait dependency was not assigned to its already-open invocation. | Bind only witnessed context facts inside the same actual invocation/explicit parent. |
| [concurrent-midspan-03](concurrent-midspan-03/result.json) | Single-layer selection removed every row when that layer had no new events after recording began. | Keep each execution's selected layer axis; show an empty interval rather than removing the execution. |
| [concurrent-midspan-04](concurrent-midspan-04/result.json) | Mid-operation acceptance passed. | Two separate context entries, original wait dependencies, closed lifetimes, layer controls and centre anchors pass without extra business events. |
| [Dialogue 01](dialogue-01/dialogue.md), [original screenshot](dialogue-01/artifacts/design-round3.png) | The discovery-only trial exposed overlapping long captions at 41% zoom. It stopped before business implementation. | Repair the maintained renderer, add measured wrapping and a browser regression replaying the exact copied discovery and camera. [Retest](captions-02/result.json) preserves coordinates and source bytes. |
| [Source quality 03](source-quality-03.log) | A manual formatter call omitted the repository configuration. Lint passed, but the pinned format check rejected three files. | Apply the pinned configuration, retain the failed log, and open a separate formatting-only example checkpoint. [Source quality 04](source-quality-04.json) passes. |
| [Layer persistence](browser-regressions-03/layers/runner.log) | The browser test refreshed before the fixture server acknowledged its saved custom order; the retained server snapshot still had revision 0. | Require the actual server-owned custom order and positive revision before reload. All original assertions remain; [retest](ruler-retest-02/result.json) passes. No product persistence patch. |
| [3D layer mask](browser-regressions-03/3d/runner.log) | The test read the previous plane projection between a visibility change and the next completed render. Its failure screenshot already showed the selected layer mask. | Wait for both the requested visibility input and its worker-produced plane projection, then retain the original plane, port and interaction assertions. [Retest](layered-retest-01/result.json) passes. No product layer-layout patch. |
| [Trial 02 gate](dialogue-02/artifacts/verify-001.json) | Business, state and project checks passed; mapping failed with 11 missing-exit reports. Actual data transactions ended with `commit`, and transformations with `change`. The shared closure checker recognized only return/error. The trial stopped without accepting or starting application browser acceptance. | Register the native adapter lifecycle in data projections and resolve the same bindings for verification and display. The unchanged captured facts now contain [591 closed calls](dialogue-02/closure-after.json). Six [negative controls](dialogue-02/closure-negative-controls.json) still reject removed exits, wrong identities and wrong statuses. This replay is component evidence, not application acceptance. |
| [Trial 03 overview](captions-lowzoom-negative/result.json) | At about 26% zoom the minimum-size icons left no height inside their shrinking world boxes; the earlier clipping repair removed all captions. Trial 03 stopped at its confirmed design stage, with no application data or accepted run. | Reserve one readable caption line and extend its hit region without moving nodes. The [native zoom-and-click retest](captions-lowzoom-final/result.json) checks non-overlap, source/explained names, unchanged coordinates and actual selection below the original node box. |

Completed historical facts remain boundary markers, with no invented duration.
One such fact may feed several concurrent executions. Unit regressions cover that
case and ensure context bytes remain unchanged.

## Validation

- [First full repository run](repository-verification-01.json):
  `tools/verify.py --database` passed before the additional context-boundary repair.
- [Caption-phase repository run](repository-verification-03.json):
  the same complete command passed after context repair, measured captions and
  synchronized/frozen example updates. This is separate from the independent app.
- [Data-lifecycle repository run](repository-verification-04.json): the complete
  command passed after the shared defect found in trial 02 was repaired. The latest
  source-quality gate checks 118 Python and 90 JavaScript modules.
- [Initial Web regressions](browser-regressions-01.json): six existing suites passed.
- [Concurrent recording](concurrent-04/result.json) and
  [mid-operation recording](concurrent-midspan-04/result.json): actual Python/SQLite
  operations and native browser interaction.
- [Routing](routing-browser-01.log): actual WASM, Worker and WebGL checks.
- [Source quality](source-quality-01.json): 117 Python and 89 JavaScript modules;
  formatting, source checks and imports passed at that phase.
- [20,000-event benchmark](performance-01/result.json): nine rows; first paint
  135.2 ms, seek p95 22.1 ms and paint p95 13 ms on this Windows host. This is a
  synthetic Canvas presentation benchmark, separate from business execution.

After the context and caption repairs, all five real concurrent/lifecycle variants
passed (`concurrent-final2-*`, `lifecycle-final2-*`), as did the naming/concurrency
checks in `graph-names-captions` and `concurrent-captions`. The latest source gate
checks 117 Python and 90 JavaScript modules. The [latest synthetic benchmark](performance-03/result.json)
keeps 20,000 events on nine rows: first paint 162 ms, seek p95 36.1 ms, paint p95
13.7 ms on this Windows host, with other checks running concurrently.

The [final browser matrix](browser-final-matrix.json) retains the original 15-suite
run and the two targeted synchronization retests. All suites have a passing result;
this is not presented as a single all-green run.

Independent application implementation and iteration acceptance in the
[fresh dialogue](dialogue-plan.md) remain in progress.
Failed evidence is retained; no old check or accepted business expectation was
removed to make these results pass.

## Data-lifecycle repair

`observation/lifecycle.py` owns the pure Python boundary resolver and data-adapter
vocabulary. Database projections put that declaration in the normal graph JSON.
The strict checker now receives the current model. Explicit physical function
spans still require their actual return/exception; a mid-call commit does not
replace it. Registered value/state periods remain separate from invocation closure.

The viewer respects registered updates instead of applying legacy commit/change
heuristics over them. Graph activation invalidates its cache when model nodes
change, even if the events are unchanged. Older data recordings remain readable
using their declared adapter action and captured status.

[Native SQLite tests](data-lifecycle-runtime-04.log) cover reads, actual commit,
rollback, transformed values and exceptions, with Python/JavaScript parity,
graph/Timeline completion and a recording beginning inside a transaction.
The first two failed test-setup attempts are retained separately.
[Data Web replay](data-lifecycle-browser/database-browser-results.json) and
[mid-operation concurrency](concurrent-data-lifetimes/result.json) pass.

Trial 03 used a new conversation and directory, reused the stopped business source
candidate and confirmed requirements, and installed the corrected observer. It
stopped at the overview-caption regression before application integration. After
that repair, a new conversation will resume the same prepared, zero-data project
to test file-based handoff and ordinary feature iterations. This is explicit
adoption/handoff evidence, not another from-scratch implementation. Earlier source
bundles and failed runs remain intact.

## Native call ownership repair

Trial 04 resumed the prepared app in another explicitly activated conversation.
Its four-category gate passed, and the real browser exercised upload, assigned
review, sharing and recipient download. Browser integration defects (object title,
preference identity and missing managed-file hashes) were repaired in that app.
Acceptance then stopped at a shared adapter defect: all 94 live database events
lacked `parent_call_id`. Closed intervals alone had not exposed the wrong execution
ownership. The [frozen handoff](dialogue-04/artifacts/RESUME.md), original recording,
source snapshot, screenshots and test receipts remain unchanged.

Python ContextVar and Node AsyncLocalStorage now propagate the current same-probe
invocation into actual driver callbacks. A native transaction becomes the parent
of its body calls. Explicit identities take precedence; finished and foreign-probe
contexts are rejected. No parent is reconstructed from timestamps or written into
historical facts.

[Native SQLite regressions](native-parent-runtime-02.log) cover actual queries,
callbacks, transaction bodies and concurrent request isolation. The [Node test](native-parent-node-02.log)
uses real native file callbacks to test the shared callback contract, exact result
identity and exception identity; it is not database-server acceptance. It feeds
those original captured events into the Timeline index and verifies one band for
one request and two bands for two overlapping requests. The failed SQLite baseline
is retained in `native-parent-negative-01.log`.

The [complete repository run after this repair](repository-verification-05.json)
passes `tools/verify.py --database`. [Source checks](source-quality-07.json) pass
for 118 Python and 90 JavaScript modules, and all five source-check regressions
pass. Both managed examples are [verified and frozen](native-parent-context-20261031-verification.json).
Fresh native browser checks pass for [ordinary concurrency](native-parent-concurrent-browser/result.json)
and [mid-operation recording](native-parent-midspan-browser/result.json), including
independent band collapse and four centre-anchored routing styles in 2D/3D.

Trial 05 is now a new conversation resuming the same frozen app after those
shared gates. Its fresh four-category gate passes, including the original 12
business assertions. Detailed runtime ownership and application Web acceptance
remain in progress; this gate is not their substitute.

Trial 05 subsequently completed the actual browser upload/review/share/download
flow. Its 99 downloaded bytes match the fixture, and all 136 data events in the
final live stream retain parent IDs. It stopped before accept at an independent
source check: eight native Flask `add_url_rule` registrations projected zero API
endpoints; 154 temporary installer entries also appeared in project structure.
The [latest frozen handoff](dialogue-05/artifacts/RESUME.md) lists incomplete Web
checks explicitly. [Public dialogue](dialogue-05/dialogue.md), original source,
490 live events, a 484-event recording and screenshots are retained.

The [failing native regression](programmatic-api-negative-01.log) reproduces the
route omission against a real Flask application's registered table. A separate
Python AST module now emits literal programmatic registrations with lexical
handler bindings; the existing index projects them alongside decorators. Known
imported/bound handlers link to their physical symbols. Computed paths, shadowed
receivers and unresolved handlers remain unknown; omitted methods stay unspecified
because handler attributes can override framework defaults. This is declared
source structure, not proof that every route ran.

The [27-test source regression](programmatic-api-retest-02.log) passes, including
incremental updates and unknown controls. A [read-only rescan of the frozen real app](programmatic-api-project-retest.json)
now produces eight endpoints with eight resolved handlers and no temporary nodes.
No app code, stored event or frozen source was changed by that independent scan.

The complete [post-API repository check](repository-verification-06.json),
[119-Python/90-JavaScript source gate](source-quality-08.json), and
[actual code/project/API browser regression](programmatic-api-code-browser/browser-result.json)
pass. Both examples retain their protected [programmatic API checkpoint](programmatic-api-20261031-verification.json).
Trial 06 now resumes the frozen project in another new conversation after these
gates, retaining its original baseline and business assertions.

## General point-observation ownership

Trial 06 stopped before acceptance at a second ownership gap. Its 28 real HTTP
checks and browser upload/review/share/download passed; all 534 data events had
parents. However, ordinary rule/value points lacked their outer invocation,
including policy facts with explicit file identities. The viewer grouped some
of those points into fallback streams spanning unrelated requests. These were
execution-group spans, not observed function lifetimes. The
[public dialogue](dialogue-06/dialogue.md) and [frozen handoff](dialogue-06/artifacts/RESUME.md)
retain the failure and list incomplete Web checks. The four-category gate alone
had not tested this ownership requirement.

The user correctly questioned why a defined fact could lack ownership. Its node,
field types and real value were defined; its enclosing runtime invocation was
missing. This is a shared capture/check defect. The current
[repair plan](point-ownership-plan.md) adds a strict optional parent-entry field
to the common event envelope, preserves explicit file identities and propagates
actual same-probe context through Python/Node callbacks. The existing protected
strict-closure gate also rejects internal points that omit ownership entirely.
Source-bound external point notifications can declare their root role on the
existing node; no second graph or acceptance switch is introduced.

The 18 continuity regressions include correct values and closed calls with only
ownership removed, wrong/stale/closed parents, invalid field types and declared
external roots. All 25 native data regressions still pass. The
[Node callback test](../../../tools/test_data_context.mjs) uses actual native
file operations and checks the captured facts in the Timeline/Graph index.
It is callback-contract evidence, not database-server acceptance.

The [actual concurrent browser retest](point-parent-browser-04/result.json) and
[mid-operation recording](point-parent-midspan-browser-01/result.json) pass:
two real SQLite workers occupy two four-layer bands, file-scoped rule points have
actual parents, strict full-run ownership passes, and all four route styles retain
2D/3D centre ports. Attempt 03 is a retained test-harness failure: it filtered raw
stored events by a presentation-only `kind` field and supplied zero facts to the
checker. The retest reads their actual `bo-event/v1` protocol without altering
the application or original assertions.

[Read-only replay](old-recording-ownership-replay.json) of the old 1,800-event
recording verifies its original hash. The current index retains four invocation
bands and one diagnostic band with 758 unassigned points and no fabricated
unassigned intervals. This documents the failed capture; it does not repair or
accept the old run. [Source checks](source-quality-10.json) pass for 120 Python
and 90 JavaScript modules. Both installed examples are
[verified and frozen](observation-ownership-20261031-verification.json).

The complete [ownership repository run](repository-verification-07.json) passes,
including database contracts, both installed examples and independent core exports.
The [registered-lifecycle browser check](point-parent-registered-lifecycle-browser/result.json)
also passes for real SQLite work, live inspection, a recording starting inside the
call, actual lifecycle meanings and the shared Graph/Timeline cursor.
[Synthetic presentation performance](performance-04/result.json) retains 20,000
events in nine layer rows: initial component load 149 ms, seek p95 19.3 ms and paint
p95 11.8 ms on this machine. This excludes full graph reconstruction.

[Trial 07](dialogue-trial-07.json) is a fresh conversation resuming the same app
after these shared gates. Its normal upgrade reported 22 changed managed files,
zero conflicts and the original baseline hash preserved. Its full capture audit
passes for 3,265 new events and 1,641 point observations with actual HTTP roots.
It froze before accept after the single-rule recording exposed a partial parent
boundary. The [public dialogue](dialogue-07/dialogue.md) and
[latest frozen handoff](dialogue-07/artifacts/RESUME.md) preserve the human's later
answer allowing truthful missing-ownership disclosure for local recordings.
The 527 protected files remain unchanged. Full Web acceptance and ordinary
business iterations are not yet complete.

The [focused-boundary enhancement](focused-boundary-plan.md) retains actual caller
headers without evaluating unselected input/result builders. The selected value
nodes are separate from static boundary hints, and actual runtime ancestors keep
their original IDs and times. A bounded open-call cache survives ordinary history
expiry; its batch staging is isolated and its headers are included in exports.
Only actual missing referenced IDs become recording gaps. The
[repair ledger](focused-boundaries-test-history.md) distinguishes product changes
from driver setup failures. Eight native/protocol regressions and an
[actual concurrent Web recording](focused-boundaries-browser-04/result.json) pass.
Both examples are [verified and frozen](focused-boundaries-20261101-verification.json)
after this change. The [complete repository run](repository-verification-08.json)
and [121-Python/90-JavaScript source gate](source-quality-12.json) pass. The
[ordinary full recording retest](focused-boundaries-full-browser/result.json)
still has 33 real events, two four-layer bands and correct 2D/3D routing. Trial 08
now resumes the app in another explicitly activated conversation to finish Web
acceptance and ordinary business iterations.

The coordinator's [independent v1 snapshot audit](dialogue-08-independent-v1/audit.json)
checks 5,629 saved events from trial 08's current build: all 1,295 entered calls
close, all 777 data calls retain parents, and no internal point or supplied parent
reference is unassigned. The declared model has no missing edge endpoints.
Actual observations occur in business, rule, function/value and data-operation
layers; this audit makes no runtime claim for static code, schema or project
structure. Native API comparison and actual loaded project/code views are separate
trial evidence. Full application acceptance and ordinary feature iterations
remain pending at this snapshot.

The same saved view separately retains [11 state frames for six instances](dialogue-08-independent-v1/state-evidence.json).
All four declared state values have exact state-node counterparts. These actual
snapshots carry original evidence/build/entity identities; their separate storage
must not be mistaken for absent state observation in the point/span event counts.

Trial 08 then completed the remaining recorded Web checks but stopped before
acceptance at a separate shared control failure: its ordinary 9,078,736-byte live
view exceeded the control CLI's 8 MiB read budget. The [public dialogue](dialogue-08/dialogue.md)
and [frozen coverage](dialogue-08/artifacts/coverage.md) retain current results,
driver failures and the two blocked 3D self-routes in orthogonal/bus mode. The
coordinating trial agent directed this freeze; no human usability or accepted
application claim is made. Its original baseline and protected files are intact.

The [control-context repair](control-context-plan.md) separates graph/build data
from runtime bodies while retaining fixed read limits and exact graph/recording
validation. The [test ledger](control-context-test-history.md) retains the real
HTTP reproduction, session check, unchanged browser suites and source checks.
Both examples are [verified and frozen](control-context-20261101-verification.json),
and [complete repository run 09](repository-verification-09.json) passes. A fresh
[trial 09](dialogue-trial-09.json) continues the same app with an actual prefixed
view/replay request, then awaits ordinary business changes after v1 acceptance.

Trial 09 then caught an integration omission in that repair: the standard HTTP
server still had an independent GET whitelist and returned 404 for the new
context route. It stopped before accept. The [route ledger](control-route-test-history.md)
retains the original failure and the new actual-standard-server reproduction.
Shared GET dispatch now delegates to `BOWeb.get`; ten capture/session/HTTP tests
pass. Both examples are [verified and frozen](control-route-20261101-verification.json),
and [complete repository run 10](repository-verification-10.json) passes. Fresh
[trial 10](dialogue-trial-10.json) continues the affected controls and ordinary
business iterations. The [trial 09 dialogue](dialogue-09/dialogue.md) and
[handoff](dialogue-09/artifacts/RESUME.md) retain its unaccepted failure.

Trial 10 applied a basic real view but stopped at its expanded permission view:
the planner ignored neighbor types and required a state hidden by the requested
filters. The [typed-focus ledger](control-types-test-history.md) preserves this
failure and an insufficient intermediate path-filter implementation. The final
repair keeps the original business path and explicit one-hop cross-type bridges,
filters ordinary neighbors, and retains the visible-node check. Targeted tests,
actual Python/JavaScript type parity and existing browser suites pass. Trial 11
tests frozen canonical source in parallel with managed/full gate 11; final
acceptance still requires every gate.
