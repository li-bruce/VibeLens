# Keyboard focus and source panel

The independent frozen-version file-sharing upgrade exposed a source-panel dismissal in the native viewer. Selecting a new node, opening its menu with Shift+F10, and choosing Source fetched the correct source with HTTP 200 and a matching build, but restoring keyboard focus selected the node again and closed the panel. Rerendering the semantic controls first avoided the problem; that workaround was not accepted as a passing result.

`SemanticView.render` captured its original `selected` argument in a focus callback. Immediate selection feedback updated `this.selected` without rebuilding the controls, so the callback could use the old value. The callback now reads the current selection. Keyboard navigation to a different node still selects it; returning to the same node preserves the open detail/source panel.

The new regression fails on `b78f03a` and passes after the correction. It covers immediate selection, focus restoration, navigation to another node and focus restoration after a render. It is part of `tools/verify.py`. Both shipped examples use normal new change records and retain their previous expectations and approvals. Original native-browser evidence, failure, source checks and final verification receipts are indexed in this directory.

A separate transport hypothesis was rejected. Old-build recording source requests are already blocked by the recording-version boundary, and the actual failing native-browser request used a new recording with matching view/recording/response builds. No source-version or frontend freshness check was relaxed. A real HTTP regression now checks rejection of old recording source, correct current source, and zero business events from source reads.

The independent project requires a fresh frozen upgrade and the same original keyboard sequence before this issue is considered closed. Its reports remain separate from these framework/example checks.

## Completed acceptance

The [complete canonical run](focus-final-full.log) passed on clean revision `3458366f72563b35749a9f7bcf799c2b7e22da00`. Its [receipt](focus-final-result.json) binds the log hash, all 240 Skill file fingerprints and both frozen example candidates to that unchanged revision.

The independent project then applied the native upgrade with no shim. Its original 35 tests, 84 scenario runs, 282 business assertions and ten negative evidence checks passed. Mapping, state rules, business and project reports all passed. The [summary](native-after/summary.json), [current gate](native-after/final-check.json) and [parity check](native-after/parity.json) retain the exact candidate/build identities and unchanged protected-file surface.

The original strict keyboard script is byte-identical before and after the repair. Its [failed receipt](native-before/keyboard-source-acceptance.json) and [passing receipt](native-after/keyboard-source-acceptance.json) preserve the same selection/menu/focus sequence. Extended [source checks](native-after/keyboard-details.json) confirm the full 299-line file, correct function highlight, matching source/build identity and visible panel in live and replay modes. No explicit semantic rerender or alternative menu is used to pass that path.

The new [native recording](native-after/browser-native/capture-report.json) contains 429 events and 11 snapshots with zero errors, drops and gaps. The [browser report](native-after/browser-native/report.json) passes actual Boolean dependencies, skipped-condition negatives, authorization filtering, 2D/3D animation and zero business events from observer operations. [2D](native-after/browser-native/boolean-transfer-2d.png), [3D](native-after/browser-native/boolean-transfer-3d.png) and [full-file source](native-after/browser-native/keyboard-complete-source-live.png) screenshots are retained.

This closes the demonstrated focus defect for the tested project. The short-chain drain took 121.584 seconds under overlapping verification load; real-time throughput has not passed and no performance improvement is claimed. Earlier source-version and runtime validation requirements remain unchanged.

During evidence assembly, an unchanged example JSON retained CRLF bytes in the older worktree. The exact-byte archive check stopped until that file matched the tested LF bytes; [alignment](merge-line-ending-alignment.json) records the sole line-ending difference and retained hashes. The [first package check](merge-closure-first.log) ran while the new receipt links were not yet copied. After completing assembly, the unchanged [package check passed](merge-closure-retest.log). These are archive/checkout issues, separate from the native source-panel defect and its regression.
