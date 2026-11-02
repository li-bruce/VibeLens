# OpenTelemetry and provenance review

Branch: `feat/otel-provenance`. Base: `d6a7b81498b6de7e200fcbb1ed4c98f7bd7b79cb`.
Status: shared implementation and independent Python dialogue/iteration acceptance completed for the tested scope. A sustained-refresh capture limit is retained below.
No merge, release or push is part of this change.

## Decision

OpenTelemetry supplies trace/span identity, asynchronous context and W3C
propagation behind the existing observation interfaces. Registered upstream
instrumentation can supply technical API/function/data spans. The live
VibeLens event stream, state-machine development and execution, source mapping,
recording, external observer and separate acceptance categories retain their roles.
See [the research and architectural decision](architecture-decision.md).

PROV/OCEL inform a small set of optional event facts: authenticated actor,
identified workflow, qualified object references and explicit causal links.
These are metadata on the existing graph, not a new graph layer or inference engine.
HTTP request wrappers belong to API/execution; user actions name the business layer.

## Review evidence

Start with [the concise Chinese review](review.zh-CN.md), the complete
[continuation dialogue](dialogue-04/dialogue.md), and the final
[recorded-view result](dialogue-04-browser-v2-replay-final-05/result.json).

| Area | Evidence and current result |
| --- | --- |
| Protected state engines | [Final core and installed runtime check](boundary-and-installed-runtime-final-11.json): six protected Python modules and the native JS validator/executor match the round baseline; ten installed runtime files and three repaired viewer files match canonical sources. The first check used an overly broad JS boundary and is retained separately. |
| Source quality | [Lint and formatting](source-quality-final-11.json): 125 Python and 91 JavaScript modules passed. |
| SDK integration | [30 Python SDK tests](observer-identity-sdk-retest-10.log) cover identity, asyncio, ended-parent children, cross-producer W3C propagation, linked jobs/fan-in, native SQLite values, null/verified actor, physical exceptions and producer isolation. The enhanced HTTP case covers command 303/403/500, exact native entry parameters and distinct application/observer routes. [Node](version-context-node-final-05.log) captured 28 events from 11 real SDK spans. |
| Upstream instrumentors | [Python SDK suite](python-sdk-http500-02.log) passes 22 tests, including real Flask 403 and unexpected native exception/500, plus urllib transport suppression. The observer's own HTTP sends create no application SDK span. |
| Graph and Timeline | [Latest actual OTel browser result](browser-otel-final-host-12/result.json): live wait, growing parent interval, mid-operation recording, replay/seek/zoom, complete source access and matching 2D/3D cursor. [Exception tooltip regression](view-exception-final-05.log) verifies physical exceptions remain visible without optional business error output. |
| Original checks | [Full host repository gate 08](repository-verification-host-08.status.json) passed at 16:43:20 +08:00, including the added instance-identity/API classification regressions. Earlier gates and failures are retained. |
| Real database drivers | [Host live regression](database-live-02.status.json) passed for Python and Node against isolated PostgreSQL, MongoDB, Redis and Neo4j containers; [native protocol result](database-native-live.json) contains 44 Node events. This is a driver regression, not a claim that every driver/OTel combination has been exercised. |
| Independent dialogue 01 | [Public conversation](dialogue-01/dialogue.md); [actor finding](dialogue-01-finding.md); [native reproduction](dialogue-01-actor-reproduction/result.json). Native rejection passed while observed actor meaning failed. Retained without an application patch. |
| Shared repair | Completion builders can provide facts known only after execution. The protected mapping plan compares each recorded context component against independent native facts for its case/node/phase. Missing differs from null. Original checks remain required. |
| Independent dialogue 02 | [Public conversation](dialogue-02/dialogue.md), [source review](dialogue-02-source-review.md) and [stop evidence](dialogue-02-evidence/REPRODUCTION-AND-STOP.md). Actual 500/rollback reproduced missing response/exception facts. Upstream Flask integration fixed the response boundary; shared exception capture was repaired before trial 03. No accepted receipt is claimed for trial 02. |
| Independent dialogue 03 | [Public conversation](dialogue-03/dialogue.md), `01a194c0-3fb4-7910-98fb-672dc11e70b6`. Its confirmed variant activates review/sharing only with committed notifications. The initial API-oriented four gates and verify/accept/check passed, preserving the baseline. [Frozen initial source](dialogue-03-v1-source.zip) and [hashes](dialogue-03-v1-source.json) retain 302 files. [Independent real browser flow](independent-browser-02/flow-result.json) passed upload, review/share waits and identical-byte download. [HTTP coverage review](dialogue-03-form-response-finding.md) then found missing actual 303 status on HTML commands, so complete observation acceptance is pending. Tool approval interruptions and the test locator failure are retained. |
| Isolated continuation 04 | [Public dialogue](dialogue-04/dialogue.md), `01a195c0-6ad5-72d1-9f55-44d6d379d649`, starts from the frozen accepted source; [origin](dialogue-04-origin.json). [Final project acceptance](dialogue-04-evidence/instance-frame-acceptance-summary.json) passes all four categories, 16 scenarios/48 on-off-fault runs, 122 independent native HTTP comparisons and 15 tests. |
| Ordinary business iteration | A plain revocation request triggered recall and one necessary question about independent administrator authority. The updated graph was confirmed. Four categories, 45 runs and 12 tests passed after strict model/mapping checks caught two declaration errors. [Saved configuration and identity comparison](dialogue-04-preferences-after-coding.json) retains all 234 old node IDs and three preference entries; ten nodes were added. The [accepted source](dialogue-04-v2-pre-exclusion-fix-source.zip) is frozen. |
| Listener exclusion review | [Actual 404 reproduction](dialogue-04-listener-finding.md) exposed a path-name exclusion on the wrong service. [Managed repair](dialogue-04-evidence/listener-acceptance-summary.json) captures nine real application 404s and adds zero application events for actual observer/static reads. |
| State-instance and API review | [Instance finding](dialogue-04-state-instance-finding.md), [native-frame project regression](dialogue-04-evidence/instance-frame-upgrade.md), [Python regression](state-instance-python-final-11.log) and [cross-language layer checks](continuity-final-11.log). Native identities survive live/recorded projections. Explicit API runtime nodes stay in API. |
| Final finite-flow capture | [Unchanged captured facts](dialogue-04-browser-v2-final-03/recording.json) and [actual UI review](dialogue-04-browser-v2-replay-final-05/result.json): 6,608 events, zero gaps, 18 exact native HTTP comparisons, four native state instances, seven expected state changes, zero false final transitions, 1,734 lifecycle intervals and 699 causal flows. 2D/3D share raw cursor 6609. |
| All layers | [Source/runtime audit](dialogue-04-layer-audit-final-02.json) covers all nine layers. State evidence is 11 exact native snapshot frames, not a second state-node probe. Project/data structures and unmapped code remain static projections. The on-demand code slice reports its explicit boundaries/omissions. |
| Capture operating limit | [Continuing-refresh finding](dialogue-04-capture-load-finding.md) retains the interrupted run with 1,141 pending envelopes at stop. Final finite-flow acceptance ends the user sessions and waits for actual queue settlement. No timeout, capture scope or completeness check was weakened. Sustained-throughput/stop-latency guarantees remain unmeasured. |
| Trace identity and version boundary | [Original counterexamples](version-context-reproduction-05.log) failed for a span ID reused in another trace and a valid queued cause from an earlier build. The repaired SDK uses full trace/span identity and preserves the old cause as a labeled external link, without importing old graph identity. Strict and malformed/foreign cases remain rejected. |
| Iteration handoff size | [Continuity regression](recall-continuity-06.log) passes 19 tests. A 2,000-row mapping contract remains intact while recall exposes 12 preview rows, total/omitted counts and the full contract path. The full verification plan is unchanged. |
| Repeated native contexts | [Real two-reviewer failure](dialogue-03-context-reproduction/canonical-result.json) exposed a selector limitation. [Retest of the same 93 raw events](dialogue-03-context-reproduction/joined-retest.json) matches both native callers by full trace/span identity and rejects altered/missing facts. [10 context tests](context-join-final-07.log) preserve legacy rows and require both sides of collection joins. This focused result is separate from pending full dialogue acceptance. |
| Review-oracle correction | [Reauthentication review](dialogue-03-reauthentication/README.md) initially compared request-entry identity with a later function-entry event, overlooking the intervening session clear. This was an external review false positive, not another capture defect. The unconfirmed keep-session expectation was withdrawn. [Exact-boundary retest](dialogue-03-reauthentication-corrected-boundary/result.json) passes against a stable accepted candidate, preserving both original raw runs. |

The workspace already contained unfinished recording/timeline work before this
branch. [The baseline](baseline.json) records it. Its changes are retained and are
not presented as new OTel implementation.

The final source is frozen in [a 309-file archive](dialogue-04-v2-final-source.zip)
with [per-file hashes](dialogue-04-v2-final-source.json). Build:
`2a84d16935506ba30e1071d3a4bbd74fc25c3ac12270cdf023ef79535b7c630b`.
Conversation answers are explicitly labeled scripted-user evidence, not independent
human usability results. [Browser review](dialogue-04-browser-review.md) distinguishes
product findings from locator, asynchronous-wait and adapter/type errors in the
test harness. Those errors and their original outputs remain available.

## Reproduce the shared checks

```powershell
.venv/Scripts/python.exe -m pip install -r skills/vibelens/requirements-telemetry-test.txt
.venv/Scripts/python.exe -B -X utf8 tests/test_telemetry.py
.venv/Scripts/python.exe -B -X utf8 tests/test_context_mapping.py
node tools/test_telemetry_node.mjs
node tools/test_telemetry_view.mjs
.venv/Scripts/python.exe -B -X utf8 tools/verify.py --database
```

The full gate retains mapping, native state execution, business checks,
observation on/off/fault, removal/export and project checks. SDK presence alone
does not establish complete observation. Browser tests require an actual browser
and separate screenshots/results. The first sandbox browser/junction attempts
failed under host restrictions; authorized host retests are kept alongside them.

## Integration

Read [the Skill integration contract](../../../skills/vibelens/references/telemetry.md).
Python and Node adapters are implemented and exercised. React/Vue retain the
common JSON protocol; browser-specific OTel async instrumentation is not claimed
as validated by the server-side trial. AppMap, Collector and Jaeger are researched
alternatives or downstream tools, not installed default recorders. The standalone
export is `bo-provenance/v1`, not OTLP, OWL or an OCEL serialization.

The application remains responsible for authorization and native business state.
Actor claims never come from tracing headers. A child invocation may outlive its
parent, but a later point event does not obtain ownership from an expired call.
Unknown/external parents stay explicit. Sampling and dropped events remain gaps.
