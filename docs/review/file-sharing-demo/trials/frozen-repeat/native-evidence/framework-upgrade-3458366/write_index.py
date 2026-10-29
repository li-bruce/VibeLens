"""Write a source-bounded English failure/fix/retest index from actual receipts."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
read = lambda name: json.loads((OUT / name).read_text(encoding="utf-8-sig"))
s = read("summary.json")
before = read("before.json")
details = read("keyboard-details.json")
copy = read("unchanged-test-copies.json")["keyboard_source_acceptance.py"]
preserved = read("preservation-check.json")
body = f'''# Focus-fix candidate: independent project acceptance

Date: 2026-10-29 (Asia/Shanghai). **This project's independent acceptance passed.** The original failing keyboard path now passes without a rerender or alternate-menu bypass. Native framework installation was used; no shim, business change, weakened assertion or fabricated event was introduced. These are finite automated checks, not human or production acceptance.

## Frozen source and native maintenance

| Identity | Value |
|---|---|
| Frozen source commit | `{s["canonical_revision"]}` |
| Source directory | `VibeLensTrials/vibelens-focus-fix` |
| Accepted project candidate | `{s["candidate_id"]}` |
| Current build | `{s["build_id"]}` |
| Previous b78 build | `{before["build_id"]}` |
| Immutable change | `.stategraph/framework-upgrade-3458366/` |

The source was clean and frozen at application and completion. Native plan/apply changes exactly `static/graph/semantic-view.js`; all 196 installed managed hashes match. The substantive fix reads `this.selected` in the focus handler rather than the render-time `selected` closure. [Frozen source diff](frozen-source-diff.patch) preserves the exact change.

The sequence was `begin → bo_upgrade plan/apply → source/hash review → native ownership seal → scan/review → tooling/check.py --accept → independent browser/evidence checks → final current check`. The formal command runs architecture, scan, inspect, verify, accept and check; the original business test suite was not separately repeated. See [begin](begin.json), [plan](plan.json), [apply](apply.json), [seal](seal.json), [parity](parity.json), [post-upgrade zero-change plan](post-upgrade-plan.json), and [formal command log](gate.stdout.txt).

At authorization the wider source verification was still in progress. A later passing source receipt was supplied and checked against the same clean full SHA, 240 Skill-file hashes, two example bindings and the full log SHA. The [receipt audit](upstream-receipt-check.json), [source result](upstream-verify-result.json), and [source log](upstream-verify.log) are retained. That source suite was not rerun here and did not replace this project's independent tests or real browser work.

## Preserved failure and unchanged application

The previous [b78 review](../framework-upgrade-b78f03a/index.md) remains **failed for its original keyboard requirement**. Its strict exit-code-1 result, DOM/HTTP traces, screenshots and stopped recording are preserved without rewriting them.

- [b78-source.zip](b78-source.zip) preserves {len(before["source_files"])} exact source/contract/managed files, including the original strict test.
- [b78-evidence.zip](b78-evidence.zip) preserves {len(before["evidence_files"])} original reports, failures, recording files, previous archives and baseline/check receipts.
- [Preservation audit](preservation-check.json) verifies archive hashes and every archived member. All {preserved["old_raw_recordings_byte_identical"]} earlier raw recordings remain byte-identical in place; original V2 and b78 failure artifacts are unchanged.
- [Byte comparison](byte-comparison.json) verifies all 50 protected application/test/contract files and the entire project declaration. The [before](before-machine.json)/[after](after-machine.json) machine and [before](before-policy.json)/[after](after-policy.json) policy are byte-identical.

Across the complete prior source inventory, changes are limited to the one native viewer file, native runtime-version metadata, reviewed ownership hashes and the derived build manifest. Business source, state/policy logic, original tests, acceptance values, mappings, capture wiring and the original evidence-audit script remain unchanged.

Current [source bundle](upgraded-source.zip): {s["source_bundle"]["files"]} files, SHA256 `{s["source_bundle"]["sha256"]}`. It is a source bundle; no new claim is made about a separate core export. The accepted historical core reproduction remains preserved.

## Failure → frozen fix → identical-path retest

1. **b78 failure:** newly selecting the revoke node, opening Shift+F10 and choosing Source returned HTTP 200 with matching source/build identity, but restoring focus invoked a stale selection callback and hid the panel. The original [strict failure](../framework-upgrade-b78f03a/keyboard-source-acceptance.json) and [finding](../framework-upgrade-b78f03a/source-focus-finding.md) remain intact.
2. **Frozen upstream fix:** only the native focus handler changes to use current `this.selected`. The detail panel, menu, source/version checks and application code are byte-identical to the prior installation. This project did not patch the frozen source.
3. **Same-path pass:** the [strict test](keyboard_source_acceptance.py) is a byte-identical copy of the b78 test, SHA256 `{copy["copied_sha256"]}`. Its [result](keyboard-source-acceptance.json) is passed/exit 0, versus b78 exit 1. It performs no explicit rerender after selection and uses no alternate menu. [Copy-byte proof](unchanged-test-copies.json) also covers the reused fixtures/capture/viewer scripts.

The exact path is: restore the original preference values → open a fresh graph → select/focus the previously unselected revoke node → Shift+F10 → Source → focus returns to revoke. The panel remains visible with actual source. The passive focus/selection trace and [strict screenshot](browser-native/strict-keyboard-source.png) are retained. No diagnostic rerender control is counted as acceptance.

Additional [keyboard detail checks](keyboard-details.json) execute that same keyboard path in both live and replay modes, explicitly proving the node starts unselected. Both show all {details["modes"][0]["full_file_lines"]} source lines, matching the real application file, with 39 marked function lines (250–288). Source response/view/recording build identities match; old recording source requests return native HTTP 400. The old detail-panel/version-check file hash is unchanged. This is actual current/obsolete admission plus byte-preserved frontend validation, not a fabricated response test.

Screenshots: [complete live source and highlight](browser-native/keyboard-complete-source-live.png), [complete replay source and highlight](browser-native/keyboard-complete-source-replay.png). Focus returns to the revoke node, personal preference values are restored through the native revision-checked API, and observer-control business-event delta is zero.

## Complete project regression

| Category | Result | Evidence |
|---|---|---|
| Implementation mapping | Passed: 15 features, {s["mapping_witnesses"]} witnesses, {s["projection_checks"]} projection checks, native policy/data/export evidence | [gate-verify.json](gate-verify.json) |
| State constraints | Passed: unchanged declaration, actual storage journals/native transition frames/public projections agree | Gate verification and [evidence audit](evidence-checks.json) |
| Business rules | Passed: {s["scenario_mode_runs"]} case/mode runs and all {s["assertions"]} assertions; {s["enabled_mode_events"]} enabled-mode events | Formal observation receipt and gate verification |
| Project checks | Passed: original {s["pytest"]} tests in {s["pytest_seconds"]} seconds; architecture; native accept/current check | [formal log](gate.stdout.txt), [gate-check.json](gate-check.json) |
| Evidence sensitivity | Passed: all {s["evidence_counterexamples"]} original controls, both real transition paths, immutable baselines and both live exports | [audit](evidence-checks.json), [stdout](evidence-audit.stdout.txt) |

The full command is `.venv/Scripts/python.exe -B -X utf8 tooling/check.py --accept`, executed once. The unchanged original evidence audit was run once after current browser evidence was ready. On/off/fault, queue-limited behavior, rejection cases and independent expected values were retained.

## New-build recording and visual regression

Version/seal metadata is build-bound, so the changed build required fresh native evidence; older stopped recordings were not relabeled or reused as current. A necessary real short chain generated recording `{s["recording_id"]}` with **{s["recorded_events"]} events and {s["recorded_frames"]} state frames**, zero errors/drops/gaps, and exact final queue/observer count convergence. Its [capture report](browser-native/capture-report.json), [drain series](browser-native/drain-progress.json), and [recording](browser-native/recording.json) are preserved.

The byte-identical [viewer regression](viewer_acceptance.py) passes on this new recording: all {s["browser_policy_evaluations"]} actual Boolean composite evaluations match explicit dependencies and equal check/basis; normal authorization animates three used guard inputs, while the anonymous short-circuit animates only signed_in. No skipped child value/event/transfer is invented. The authorization preset displays all 13 native policy nodes and seven Boolean guard relations. Native 2D/3D animation, raw-event replay, next/play/pause/live, source access and rendered reload pass with zero page/unexpected console errors and zero business events from observer operations. See the [browser report](browser-native/report.json), [2D](browser-native/boolean-transfer-2d.png), [3D](browser-native/boolean-transfer-3d.png), and [skipped conditions](browser-native/skipped-guards-2d.png).

## Performance, resources and boundary

Actual new short-chain drain: **{s["drain_seconds"]} seconds**. The earlier b78 short-chain 53.775 seconds and V2 1,731-event drain 363.125 seconds remain historical facts. This capture overlapped the formal project gate, and workloads/load differ; these timings are not an equivalent throughput comparison or a performance-fix claim. The sender and per-envelope binding/path validation are unchanged. **Real-time observation performance has not passed.** Earlier Windows relative-path diagnostics remain in the preserved V2 evidence and original [drain analysis](../revocation-drain-analysis.md).

This candidate's maintenance wall window and host-reported token deltas are in [resources.json](resources.json), separate from [b78 maintenance](../framework-upgrade-b78f03a/resources.json) and the business iteration. Cached input/reasoning subsets and the final accounting-snapshot limit are explicit; no billing or unique-text estimate is implied.

The [original Chinese request and source-verification follow-up](dialogue.zh-CN.md) are retained. No business feature, publication, outgoing chat message or promotional/demo page was produced. This project's independent acceptance is complete; stop here. Broader human/production readiness is not inferred from these finite checks.

Run `.venv/Scripts/python.exe -B -X utf8 run.py`. [Application](http://127.0.0.1:8840) · [Current graph](http://127.0.0.1:8841/graph).
'''
(OUT / "index.md").write_text(body, encoding="utf-8")
print("Wrote the source-bounded focus-fix failure/fix/retest index.")
