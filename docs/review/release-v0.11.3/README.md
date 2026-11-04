# v0.11.3 timeline inspection patch review

Status: the [local candidate gate](candidate-gate.json) and all eight candidate CI jobs passed. They cover the full host gate, package, native examples, clean export, fresh viewer checks and all three browser harness cases. The independent project passed its finite functional and isolated-view checks; its earlier shared-default preservation failure remains unresolved. Publication and tagged installation are separate checks.

The v0.11.2 tag remains immutable. Its candidate CI passed eight jobs; later main and tag runs exposed two separate problems:

- The main browser test reloaded before the reopened timeline preference was acknowledged. The [controlled proof and test repair](../graph-quality-20261104/publication/main-ad50-timeline/README.md) retain the original failure and verify exact saved visibility, height, scope and revision before reload.
- The tag's registered lifecycle test found a paused connector that stopped moving. The [retained diagnosis](../graph-quality-20261104/publication/lifecycle-registered-motion-diagnostic-01/diagnosis.json) reproduced the actual viewer defect. The repair keeps the selected timeline connector moving from its own relationships, including when the graph view has no transfer animation.

The [v0.11.2 shared source-scope repair](../release-v0.11.2/README.md) carries forward unchanged. Source roots, classified pruning, physical bindings, API coverage, source documentation and native state-engine checks remain required. The six protected state/contract files retain their original hash checks.

[Fresh browser checks](../graph-quality-20261104/publication/timeline-inspection-0113/summary.json) passed three registered lifecycle runs plus default, mid-span and two concurrent-execution variants. The registered cases keep the original event selected beyond 1.3 seconds with zero graph transfers and visibly moving timeline connectors. The summary records the exact tested source hashes; the aggregate compares them with staged files.

## Candidate gate

[Full host verification](../graph-quality-20261104/full-verification-11-timeline-inspection-host.json) passed with database verification enabled. [Product source quality](../graph-quality-20261104/source-quality-0113.json), [final harness source quality](../graph-quality-20261104/source-quality-0113-harness-final-02.json) and [package-copy checks](../graph-quality-20261104/package-copies-0113.json) passed.

Both the [delivery](../graph-quality-20261104/examples-delivery-timeline-inspection-0113-final-acceptance-summary.json) and [team-archive](../graph-quality-20261104/examples-team-archive-timeline-inspection-0113-final-acceptance-summary.json) examples completed their native acceptance. Their [682 frozen inputs](../graph-quality-20261104/example-timeline-inspection-0113-staged-parity.json) match the staged copies. The [isolated Git export](../graph-quality-20261104/clean-staged-export-timeline-inspection-0113-report.json) passed both current native checks without regenerating or reapproving them.

The same-family preference test audit replaced ineffective asynchronous predicates with actual server acknowledgments. Complete [names and viewer-control cases](../graph-quality-20261104/publication/preference-ack-0113/README.md) and the [code-browser case](../graph-quality-20261104/publication/code-browser-ack/summary.json) passed. The code case also checks the exact recorded project structure while keeping current AST symbols excluded from historical replay. Intermediate semantic, readiness and environment failures remain retained.

[check_candidate.py](check_candidate.py) verified exact staged package files, current receipts, six protected cores and unchanged clean-export example trees. It also checked final harness source quality and all three complete browser cases. Fresh viewer and harness evidence identifies the exact staged source hashes; equality with an older viewer tag was not reused.

The frozen package contains 305 Skill files:

- Skill tree: `2df145bcd7839014c9382029723f43bc6e0dd3c6`
- ZIP SHA-256: `cbf8c8ef647033cf74fbe372724084a5f49e8a67b14c8e7c881a966cd85df0ac`
- [Package manifest](manifest.json)

The aggregate retains the original main/tag failures and each required receipt's digest. The [candidate CI](../graph-quality-20261104/publication/ci-candidate-81102c19-final.json) passed all eight original jobs on its first attempt at commit `81102c19`. Publication and tagged installation remain separate checks.

## Independent project review

The GitHub candidate was installed with all 305 files verified. The existing file-sharing project then used the managed upgrade process. Its finite checks passed: 126 business assertions, 13 negative cases, ten source-scope cases and nine browser checks. A new business recording contains 158 events. The separate paused-event measurement kept the event unchanged for about 2.09 seconds, with moving causal connectors beyond the former cutoff. An observer-only full recording contains zero business events, zero gaps and no pending delivery after settlement.

The [independent review](../graph-quality-20261104/trial-audit/observer-v0113-independent-02.md) keeps the first default-layout preservation failure separate from those passing results. Existing two-dimensional positions were retained, but camera, expansion, selection and one existing three-dimensional horizontal position changed. The writer is unknown. Earlier snapshots also show default-file changes before the v0.11.3 runtime was applied. The later isolated conversation-view measurement left the default file unchanged. The complete trial is therefore not labeled entirely successful.

The original URL query was removed by the trial's privacy filter. Its exact bytes were not independently collected. The review distinguishes that evidence gap from actual zero-event counts, the saved private namespace and server acknowledgments; a placeholder is not treated as proof of identity.

## Shared-default follow-up

The design preview and application observer use the same default view file for the same project, regardless of port. An explicit conversation URL selects its own file. Source inspection found no default write in normal startup, GET or managed upgrade; the maintained write entries are preference POST handlers, with file locking and revision checks. An already-open client can automatically save after a graph or layout update. The retained preview logs have no HTTP access records, so they cannot identify the earlier writer.

Follow-up work: record preference-write provenance outside the business event stream, and review the lifecycle of superseded preview services. Keep session identifiers and private view contents out of public evidence. This follow-up does not change the business/state executor or reinterpret the retained preservation failure.
