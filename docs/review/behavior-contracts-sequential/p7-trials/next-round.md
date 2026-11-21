# P7 consolidated issue review

Updated 2026-11-21. P7 remains in progress. Repair 26 is committed as
`df6bba9d`; its repository gates pass. Native trial acceptance is separate.

## Working sequence

1. Inspect remaining independent features on the current candidate and retain
   failures, raw facts and screenshots. Keep unavailable checks explicitly pending.
2. Consolidate causes and affected modules in this document before another repair
   batch. Separate framework defects, application defects and test preparation.
3. Implement the batch with focused regressions. Do not weaken existing assertions,
   delete missing observations, increase capacities or rewrite failed recordings.
4. Run one complete verification round after the batch. Reuse existing trial
   evidence for diagnosis; a new dialogue is reserved for the complete candidate,
   subject to the user's authorization. Product scenes follow final acceptance.

## Findings

| ID | Finding and evidence | Classification | Required action |
|---|---|---|---|
| R27-01 | Node recording `380df57764ce4038b1e20cd1c7ca7ad2` stops with 8178 interval events and 2000 context events. Start sequence is 2099; the live history still has every earlier event. Context starts at sequence 100, cutting away one parent entry referenced by 446 context events. All 446 missing references precede the recording interval. Stop settlement is complete: target/completed 10317, pending 0. | Recording context construction defect; actual capture loss is not established by this result. The persisted recording is incomplete and remains failed. | Preserve the bounded recent context and its witnessed invocation ancestry without raising the native queue/history capacities. Distinguish intentionally omitted older history from missing required evidence. Keep strict disclosure when a needed entry really is unavailable. Add full/focused, consecutive-recording, expired-history and reused-call-ID regressions. |
| R27-02 | Python provider-only maintenance initially changed a watched provider path without running its standard generator. All 162 business assertions passed, but snapshot/build admission correctly failed. The original manifest and newly computed source identity differed. | Reviewer preparation error. | Preserve the failure. Standard generation, scan, names and candidate review are now complete; native retest remains pending. No business source or semantics changed. |
| R27-03 | The fresh Node provider lacked parser dependencies. The scan rejected 24 entries until the existing documented locked `npm ci` setup ran. All 466 maintained files remained unchanged. | Installation preparation gap, not a scanner bypass. | Retain installation receipts and include dependency checks in the final candidate handoff. |
| R27-04 | Node's pre-browser complete verification had 15 of the protected 18 case/mode combinations. Only browser on/off/fault were absent; stale-build browser evidence was correctly excluded. | Pending real evidence, not permission to reduce coverage. | Preserve the nonzero result. Real browser operations have since run; the second recording still fails R27-01, so full acceptance remains pending. |
| R27-05 | Native account switching could display the previous account's rows or apply a late response to the new account. The application now scopes responses to session/request generations; 16 controlled frontend tests and the subsequent real business page checks pass. | Application defect repaired in the existing trial; capture acceptance remains separate. | Retain before/after tests, source/mapping update and actual page results. Do not count simulated HTTP responses as native authorization evidence. |
| R27-06 | The caption/source review passed 12 locale/mode cases, then searched for `prepare_download`. Both that node and `guard_prepare_download` matched. The reviewer assumed a unique result and stopped before opening the source. | Reviewer disambiguation defect. The two search results are legitimate; this is not evidence of a wrong source binding. | Select by the stable node identity associated with the actual result. Retain the exact-source and full-file/highlight assertions. Complete this pending check in the final batch. |
| R27-07 | The general controls suite correctly requires actual live producer history before checking observer-event exclusion. The observer-only discovery session has none, so it stops before custom view/drag/annotation checks. | Unmet test prerequisite; those controls remain untested on this candidate. | Separate independent interaction discovery from native-exclusion acceptance in the reviewer harness, while retaining the original live-history, SQL and event-exclusion gates for final acceptance. |
| R27-08 | The root desktop helper initially omitted the application's documented SQLite URL. Its next startup reached a sandbox temporary-snapshot `PermissionError`. The configured host run starts and completes the independent checks. Neither startup attempt changed protected files. | Reviewer/environment preparation failures. | Reuse the application's documented process-local environment and supported test host. Preserve both failed startup receipts; avoid reporting them as product defects or changing database/capture scope. |

## Remaining checks in this discovery round

- Desktop discovery is complete for readiness, seven 2D/3D layer presets,
  expansion, Timeline and moving arrows. Twelve bilingual name cases pass;
  source navigation and live-dependent controls remain pending as above.
- Node's four declared/bound state model IDs and state/initial-state inventories
  agree. The second record has actual frames for all four models. This is frame
  presence, not complete transition or business coverage. Python's current-provider
  runtime evidence remains pending; its repair-25 result keeps that older identity.
- Complete the Python maintenance retest and Node source-only refactor only after
  their prerequisites are satisfied. Neither is complete on the new candidate.
- Consolidate A24–A34 and the visible dialogue review. Homepage/demo changes and
  their final browser checks remain pending accepted source/recording artifacts.

The original Node run is under the local trial's
`review/runtime/unified-1795263116`; its first recording is
`5e4c8036b5a4428aaba2266820113d94` (2066 events). The second recording and its failed
stop receipt remain unchanged. Selected original recordings, stop receipts,
preservation audits, desktop results and screenshots are now exported with
member hashes in [discovery round 27](discovery-round-27/README.md).

## Proposed repair batch

1. Fix R27-01 in the shared capture-context implementation. Keep the current
   bounded recent-value context; add only witnessed invocation boundary metadata
   required by those facts and the recording interval. Resolve original explicit
   parent references and scoped call identities, including completed ancestors.
   Keep starts/ends paired where the source witnessed them. Missing or expired
   evidence still produces a gap; no fabricated parent, return or end time.
2. Cover full/focused capture, consecutive recordings, calls crossing the start
   boundary, closed ancestors cut by the recent tail, reused call IDs across
   producers/streams and genuinely expired history. Unselected value builders
   must remain unevaluated. Do not increase the application's queue/history
   limits or remove the original strict recording assertions.
3. Correct reviewer setup/selection for R27-06–08 together. Preserve the first
   failures and all final native-exclusion/source assertions. Review the existing
   application repair R27-05 against the same final provider.
4. Run targeted regressions, then one complete repository/package gate. Upgrade
   both trial projects through the documented maintenance workflow. Complete
   their outstanding native/UI/refactor checks using the existing authorized
   conversations and retained requirements. Further fresh conversations are not
   a per-defect requirement.
5. Finish A24–A34 and product scenes after those results pass. P7 stays in progress
   until the whole scope is complete; no release claim follows from this inventory.
