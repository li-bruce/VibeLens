# v0.11.3 timeline inspection patch review

Status: the [local candidate gate](candidate-gate.json) passed. It covers the full host gate, package, native examples, clean export, fresh viewer checks and all three browser harness cases. Remote CI, publication and tagged installation remain pending separate checks.

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

The aggregate retains the original main/tag failures and each required receipt's digest. Remote CI, publication and tagged installation remain separate checks.
