# Shared causal ownership and execution grouping gap

This is a canonical framework/viewer gap, separate from the retained browser-driver mistakes. No application workaround, managed-source patch or event rewrite was applied.

## Actual project evidence

- `actual-recording-recovered.json` is the new real application recording `5ad97257db954dd0b2c85cadb0f9059d`: 1,800 events, stopped, no reported gaps. It contains the browser workflow and real threaded HTTP matrix. It is not a fixture replay.
- `failure-timeline-timeline.json` and `shared-causal-grouping-gap.json` expose 114 execution chains: 103 roots are `http_request`, 10 are `policy:logged_in`, and one is `authorize_file`. The last 11 roots are single `phase=decision` facts with no native parent, not actual invocation intervals.
- The longest false interval spans approximately 745 ms to 9,856 ms in recording time, about 9,111 ms. The exact raw events and all 11 intervals remain in the JSON report. Temporal proximity cannot supply their missing parent identity.
- Policy reporting explicitly uses the file ID for entity/attempt while the enclosing application spans use application scope. General `record` and policy facts do not consistently carry the enclosing native invocation identity. Their semantic entity must not be confused with call ownership.
- The viewer renders nine bands and 63 rows. Row uniqueness, gestures and separate lanes for observed overlapping HTTP calls were tested. Those checks do not establish correct business-execution grouping while these false chains remain.

## Separate successful data-parent evidence

The final live snapshot has 1,852 events, including 534 data-operation events; all 534 have raw parent IDs. The stopped recording starts after the initial 52 live events and therefore contains 522 data events, all with parents. Do not conflate these two scopes. `runtime-parent-audit.json` verifies the final live calls, actual upload/transaction/nested-query ownership and transaction commit/error exits. This success does not repair general decision/policy causality.

## Required next step

The maintenance conversation must repair canonical record/policy causal propagation and Timeline interval/execution grouping, add regressions, and provide a normal upgrade. A newly authorized conversation must then upgrade normally and repeat actual application/browser acceptance. Never infer missing parents from timestamps, weaken protected assertions, modify business route style, or rewrite historical events. No accept was performed here.
