# Failures, repairs and retests

## Shared gap that blocks acceptance

The actual recording exposes missing general record/policy parent ownership and false long execution chains from single decision facts. See `shared-causal-grouping-gap.md`. Data-operation parent checks pass separately. The user explicitly froze this round before acceptance. The maintained repository and installed managed files were never hand edited.

## Test-driver and environment errors

1. Installing the browser driver into the project initially failed because the sandbox temporary path was inaccessible. A retry with TEMP/TMP inside the project's existing `.tmp` succeeded. The dependency remains test-only and `.tmp` remains excluded from the project projection.
2. A sandbox-local server was inaccessible from the host browser. After command/PID verification, only that owned trial process was stopped. The authorized host launch served both 8982/8983; its final listener PID was 46532, launcher 39432. Both are now absent from the reserved ports.
3. `networkidle` timed out on the continuously polled graph. The driver was changed to wait for the actual graph readiness. Form selectors were reconciled with the current login select and button labels. The real upload/review/share/download plus 28 HTTP checks and the review race passed.
4. The first recording receipt sampled the dropdown before asynchronous options refreshed, produced an empty ID and retained an invalid-ID response. `browser-flow.json` correctly describes business assertions but its recording fields are not valid evidence. Use `browser-recording-receipt.json` and `actual-recording-recovered.json`; the real record was selected in a fresh browser and has 1,800 events. The invalid response was retained.
5. The first data-call audit assumed only return/exception exits. Canonical data operations register commit/change/error phases. The audit was corrected to those registered meanings, without changing events. The second audit passed 534 data-parent checks.
6. Early browser pan tests used stale canvas bounds and an ineffective boundary gesture; the corrected fresh bounds and interior overview drag passed. A failed maximized timeline obscured the next stage's controls; the driver now restores dock size between stages. Asynchronous source fetches require a loaded-file condition. These driver issues are retained in attempt logs/screenshots.
7. Timeline point dictionaries expose raw/time, not id. The original KeyError is retained in `viewer-checks-attempt3.json` and the attempt script. Skip/include was then tested through the actual checkbox and point-count change; recording export exactly preserved events.
8. The lexical parameter highlight test did not reach the parameter: the 400/587-node code slice did not expose that ID, and searching its hash found no node. This remains not completed, not a passed highlight or independently established shared defect. Full source and authored function-range highlighting did pass.
9. `negative_controls.py` failed before running its negative controls because recipient_id is nested under observed.context. No missing-value/source-drift/schema-mutation pass is claimed. The user froze the round before further test-driver fixes.
10. The first freeze collector used the nonexistent `/api/export` path and retained its 404. The collector was corrected to the public `/api/stategraph/export` path and completed without business execution.

No business application source was changed. The project-owned `tooling/observe.py` only routes fresh observation output to this new review directory. The original active baseline, protected assertions and historical review files remain unchanged.
