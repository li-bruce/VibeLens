# Native framework upgrade acceptance: b78f03a

Date: 2026-10-29 (Asia/Shanghai). Scope: a separate framework-only iteration after accepted file-sharing V2; no business feature or expectation changed.

**Native upgrade applied without a shim; overall upgrade acceptance has not passed.** The formal project gate and unaffected viewer checks passed. The strict keyboard source-menu requirement fails and must be retested after an upstream fix/new frozen version. A native rerender control or visible-menu success is not accepted as the same keyboard path passing. Automated synthetic-data evidence is not human or production acceptance.

## Identities and native sequence

| Item | Value |
|---|---|
| Frozen canonical commit | `b78f03a89e1726f951ea76d4e0781efd2e869fe6` |
| Previous V2 commit | `e69ce0921ac06fb455ec0aedc403e24d74babebc` |
| Accepted upgrade candidate | `ce7b927acb218641920e0a3e211f4ce1b86a27b94628d04a9b3d16d4febbd6bd` |
| Current build | `d8c853730fab2f69a76f2065201964f20292aa3b28de0edf604ac7911a35d023` |
| Previous V2 build | `843e214363b362d939aba82229a7abf66f6ed128d52b978b4867f03ccb22cf67` |
| Immutable change | `.stategraph/framework-upgrade-b78f03a/` |

The canonical HEAD and clean worktree were checked before application and again at completion. The actual sequence was `begin → bo_upgrade plan/apply → source/hash review → native architecture seal → scan/inspect/review → tooling/check.py --accept`, which executes architecture, scan, inspect, verify, accept and check. Final structural current checks are retained separately; the full tests were not repeated outside that formal gate.

The native plan changed exactly `static/graph/analysis.js` and `static/graph/recording.js`, with no conflicts or retired files. All 196 installed managed files match the frozen source. The first architecture check correctly refused old sealed hashes; after exact canonical provenance review, the native seal command recorded the authorized new vendor hashes. No framework validator, projector, sender, executor, admission check, or test was edited. The [post-upgrade plan](post-upgrade-plan.json) has zero changes/conflicts.

Evidence: [begin](begin.json), [plan](plan.json), [apply](apply.json), [pre-seal rejection](architecture-before-seal.json), [seal](seal.json), [parity](parity.json), [formal command log](gate.stdout.txt).

## V2 preservation and byte comparison

- [V2 source archive](v2-source.zip): 248 exact source/contract/managed files.
- [V2 evidence archive](v2-evidence.zip): 237 original reports, recordings, failures, baseline/check receipts and existing archives.
- [Before manifest](before.json) records each original hash and both archive hashes. [Preservation audit](preservation-check.json) verifies every archived entry against that manifest and confirms all seven original raw recording files remain byte-identical in place.
- The original V2 acceptance report, summary and exported 1,731-event recording remain unchanged. Shared latest pointers and normal gate output files advance to this iteration; their exact V2 versions remain in the verified evidence archive.
- [Byte comparison](byte-comparison.json) verifies all 50 protected business/test/contract files plus the entire project declaration and unchanged original evidence-audit script. The [before machine](before-machine.json), [after machine](after-machine.json), [before policy](before-policy.json), and [after policy](after-policy.json) are byte-identical pairs.

Across the complete original source inventory, only five files differ: the two upgraded viewer files, the native runtime-version manifest, the reviewed ownership hash seal, and the derived build manifest. Application code, the native state machine, policy definitions, original tests, acceptance values, mapping cases and probe wiring are unchanged.

The [upgraded source bundle](upgraded-source.zip) contains 249 current files, SHA256 `ad4d6340ed9fe4a06d6f50dfc55a8f59e7916b1709bde571a4a45e35503e28ad`. It is a source bundle, not a newly claimed core-runtime reproduction. The accepted V2 core reproduction and source package remain historical evidence.

## Full regression results

| Category | Result | Evidence |
|---|---|---|
| Implementation mapping | Passed: 15 features, 396 witnesses, 474 projection checks; policy/data evidence and public export checks pass | [gate-verify.json](gate-verify.json) |
| State constraints | Passed: unchanged declaration; actual native paths and storage journals agree with public frames | Gate verification and [evidence audit](evidence-checks.json) |
| Business rules | Passed: all 84 case/mode runs and all 282 required assertions; 2,957 enabled-mode events | Gate verification; immutable change's observation receipt |
| Project checks | Passed: original 35 pytest cases, 78.66 seconds; architecture; canonical accept/current check | Formal command log and [gate-check.json](gate-check.json) |
| Independent evidence audit | Passed unchanged: all ten original isolated controls, both actual transition journals, both live public exports and retained baselines | [evidence-checks.json](evidence-checks.json), [audit stdout](evidence-audit.stdout.txt) |

The exact command was `.venv/Scripts/python.exe -B -X utf8 tooling/check.py --accept`. That command already runs the 35 tests and all 84 scenario/mode executions, so they were not rerun separately. The original audit was executed once after current browser evidence became available. The original on/off/fault and queue-limited checks, rejection assertions and byte checks were preserved.

## Focused browser acceptance

Build identity changed because native version/seal metadata is build-bound. The old stopped recording was therefore excluded from the current list/retrieval path and was not reused as current evidence or rewritten. A new necessary short chain used real native login/upload/share/revoke/download handlers, including owner, nonowner and anonymous policy branches and both revoke state outcomes.

New stopped recording: `538215624de546279299d1c0a1cdf5b3`, **429 events and 11 state frames**. Actual drain: **53.775 seconds**. Producer/observer counts converge; errors, drops and recording gaps are zero. See [capture report](browser-native/capture-report.json), [drain samples](browser-native/drain-progress.json), and [raw exported recording](browser-native/recording.json). The recorded file remains byte-identical across viewer tests.

The [unaffected browser checks](browser-native/report.json) verify the following subset; they do not override the strict keyboard failure:

- All 21 recorded Boolean composite evaluations match explicit actual dependencies with the same check/basis. Missing child execution is never assigned an invented value or event.
- A normal `share_allowed` event animates exactly its three used Boolean guard inputs. An anonymous short-circuit event animates only `signed_in`; neither `is_owner` nor `known_recipient` receives a fabricated transfer.
- The actual authorization preset displays all 13 native policy nodes and seven declared Boolean guard relations.
- Exact raw-event selection, animation in native 2D and 3D, next/play/pause, return to live, rendered reload and source-file viewing through the visible native actions menu pass. Page and unexpected console errors are zero.
- Observer/view/source/replay operations generate zero business events. Both original personal preference entry values were restored through the native revision-checked API, with only the preference revision advancing.

Screenshots: [2D guard animation](browser-native/boolean-transfer-2d.png), [skipped conditions](browser-native/skipped-guards-2d.png), [native 3D](browser-native/boolean-transfer-3d.png), [source navigation](browser-native/source-navigation.png). These are finite checks of this project's AND/OR rule network, not a universal claim about all rule/replay semantics or visualization usability.

## Source-panel observation and failed attempts

The first browser harness incorrectly expected separate skipped-result events. The native evaluator does not execute those children; their absence and the parent's explicit dependencies are the relevant evidence. That failed attempt remains, and the corrected harness inspects actual absence/dependency identities without adding events.

A later keyboard-menu source attempt remained at loading. Visible native actions-menu source viewing passes in both live/replay modes. A fresh four-case [source matrix](source-matrix.json) preserves the actual response and UI state:

| Mode and menu | HTTP response | View / response build | Source ready |
|---|---|---|---|
| Live, Shift+F10 | 200 | Both `d8c85373…` | No; panel became hidden |
| Live, visible actions | 200 | Both `d8c85373…` | Yes |
| Replay, Shift+F10 | 200 | Both `d8c85373…` | Yes in this fresh probe; an earlier attempt failed |
| Replay, visible actions | 200 | Both `d8c85373…` | Yes |

The replay recording is the new ID above, with full manifest/response build `d8c853730fab2f69a76f2065201964f20292aa3b28de0edf604ac7911a35d023`. Every response's source SHA256 is `81ceb8a8d19d3badf06ae95c30bc95886c34015ac10b7572f746ca3d033b131e`, matching the unchanged application file. The old-recording response-label hypothesis was withdrawn after the canonical old-build admission check was confirmed; it does not explain this same-build case. No frontend revision check was weakened, no old recording was relabeled, and no protected file was patched.

A further [controlled focus probe and source finding](source-focus-finding.md) reproduces the panel opening and then hiding when menu closure restores focus to a newly selected semantic node. A native semantic rerender after selection changes the outcome, but is only a diagnostic control. The passive DOM trace and installed source identify the stale render-time selection callback and repeated selection/panel dismissal path. The [strict acceptance result](keyboard-source-acceptance.json) is **failed, exit code 1**, with no rerender or alternate menu. Its unchanged-path [test script](keyboard_source_acceptance.py) must be rerun after the next upstream freeze. These implicated files were unchanged by this upgrade.

Failed viewer reports and subsequent retests are retained in `browser-native/viewer-attempt-*.json`; source response traces/screenshots remain alongside them. The final requested source capability is verified through its visible native menu, with the keyboard observation explicitly separate.

## Performance and maintenance resources

The historical V2 drain of **363.125 seconds** remains in [its original analysis](../revocation-drain-analysis.md). The new 429-event chain is smaller and ran under different load, so its 53.775-second drain is not evidence of a performance fix or equivalent benchmark. The native sender and per-item binding/path validation are unchanged. **Real-time observation performance has not passed.**

The earlier Windows restricted-process relative-path diagnostic and corrected absolute-root measurements remain in the V2 evidence archive and original review files. They are separate environmental/performance evidence, not application authorization failures. This upgrade does not modify path validation or infer a sole cause for the delay.

Framework maintenance wall time and host-reported token counters are recorded separately in [resources.json](resources.json), bounded by this upgrade request and its final accounting snapshot. They include framework regression/diagnostic work, not the earlier business-development iteration. Cached input and reasoning counters are reported explicitly; the snapshot is not a billing statement and excludes any not-yet-reported final response usage.

## Reproduce and stop

Start `.venv/Scripts/python.exe -B -X utf8 run.py`; app: <http://127.0.0.1:8840>, graph: <http://127.0.0.1:8841/graph>. The formal project gate is the command above. To retest the stopped recording without replaying business operations, run `review/framework-upgrade-b78f03a/viewer_acceptance.py`; the original evidence audit is `review/evidence_checks.py`. Run the short capture only for a genuinely new required build/recording; the script refuses to replace the preserved capture.

The [original Chinese request and follow-up](dialogue.zh-CN.md) are preserved. No outgoing chat message, publication, repository push or product-page change was performed. The current report and all unaffected b78 checks are complete; overall upgrade acceptance remains incomplete because of the keyboard failure. Stop and wait for a new frozen canonical version, then rerun the same strict keyboard test without a rerender bypass or weakened assertion.
