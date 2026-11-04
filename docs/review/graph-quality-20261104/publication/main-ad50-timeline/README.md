# Timeline reload acknowledgment repair

The main-branch CI failure was a test synchronization defect. The recording timeline restored the last acknowledged hidden preference after the test reloaded before confirming its reopened setting had been saved. The repair changes the browser test only; the published v0.11.2 Skill and archive remain unchanged.

## Failure retained

[Main run](https://github.com/li-bruce/VibeLens/actions/runs/41807986096), failed job 126499745512, reached `tools/test_recording_timeline_browser.mjs:278`. The reload's selected recording was valid, but its timeline remained hidden. [Original result](original-ci/result.json), [screenshot](original-ci/failure.png), and [full job log](../ci-main-41807986096-timeline-failed.log) are retained.

Artifact 13310637979 had SHA256 `bbb84fcb8d59ef05920bc2e4fb144badeaba0c0948791b0a7502baa44ddc10ef`. Its full ZIP and extraction stay in `.validation/ci-main-41807986096`; this review includes only the relevant failure files.

The same commit had passed the candidate's eight jobs. That historical result remains valid evidence for that run; it does not erase the main failure. The separate tag-run connector-animation failure is tracked independently and is not covered by this repair.

## Cause and controlled proof

The test hid the timeline, reopened it through its normal button, then checked only that the persisted scope was `all`. That scope had already been saved earlier. It did not acknowledge the reopened visibility or resized height. In addition, the asynchronous predicate passed to `waitForFunction` produces a truthy Promise before its fetched value is checked by the poller. The pinned [Playwright 1.56 source](https://github.com/microsoft/playwright/blob/v1.56.0/packages/playwright-core/src/server/frames.ts#L1336-L1398) confirms that polling behavior.

[The controlled driver](acknowledgment-proof.mjs) held one preference POST in an isolated real-Chrome recording fixture:

1. The server acknowledged revision 2 with scope `all` and visibility `false`.
2. Native reopening showed the timeline while its POST was held. The original scope predicate passed against the still-hidden saved state.
3. Reloading restored that acknowledged hidden state, reproducing the CI failure.
4. After a real reopened acknowledgment at revision 4 with visibility `true`, the same reload restored visibility and height.

[All six proof checks passed](controlled-acknowledgment-proof.json), with zero business writes and unchanged recording bytes. [Old-barrier failure](controlled-old-barrier-failure.png) and [acknowledged reload](controlled-new-barrier-pass.png) show the difference. The first diagnostic attempt's asynchronous-predicate failure is also retained in [its receipt](controlled-async-predicate-first-failure.json).

## Repair and verification

`tools/test_recording_timeline_browser.mjs` now subscribes to successful preference POST responses before each native close/reopen action. It verifies exact visibility, scope, height and an increasing server revision before reloading. All previous interaction, visibility, scope, transfer, recording-integrity and mobile/touch assertions remain. A new assertion checks that the resized height survives reload.

- The unchanged original full browser test passed locally, showing why a normal run alone was insufficient to diagnose the race: [result](local-original-01/result.json).
- The repaired complete real-Chrome test passed three consecutive runs: [run 1](local-fixed-01/result.json), [run 2](local-fixed-02/result.json), [run 3](local-fixed-03/result.json), [command receipts](retests.json).
- Prettier and ESLint passed for the changed maintained test. No timeout increase, delay, skipped case or relaxed assertion was added.
- The canonical Skill still matches the published v0.11.2 tree `82b7f501697334bb83a82b5863ac7c068785b6bf` exactly.

[Machine-readable summary](repair-summary.json) records the source and evidence hashes. New remote CI results must be assessed separately after this test repair is committed.
