# File-sharing product demonstration

## Scope

Replace the gallery story on the product homepage and interactive demonstration with a small file-sharing application. Keep the product's visual identity, bilingual copy, scroll progression, real 2D/3D viewer, and separation between coding conversations and hands-on observation.

## Work sequence

1. Run an independent VibeLens development conversation in `VibeLensTrials/file-sharing-demo-20261028`. Confirm a compact business graph before implementation.
2. Build and exercise login, owned-file upload, sharing with a named user, authorized download, and a small revocation iteration. Preserve dialogue and actual execution evidence.
3. Inspect a real failure if one occurs. If a deliberate isolated mutation is used, record it as a mutation, never as an organically discovered defect.
4. Export sanitized graph definitions, recordings, application frames, source context, and screenshots. Link them to the corresponding tested build.
5. Update homepage examples, diagrams, screenshots, conversation controls, and the interactive story together. Keep the overview readable at a glance.
6. Verify English/Chinese, desktop/mobile, recording playback, custom views, 2D/3D camera interaction, source navigation, and scroll transitions. Preserve failures and retests.

## Evidence and provenance

- Independent conversation: `01a1830f-3fb2-73c1-b8aa-becffa72e8e3`.
- Original user brief: a simple file-sharing application with users, roles, authorization, sharing, and a compact business graph.
- Follow-up answers in the trial are scripted user simulation. The trial is not a human usability study.
- Maintained source and documentation use English; original conversation evidence remains in Chinese.
- Do not replace historical gallery evidence. Remove obsolete gallery references from the current product presentation only.

## Status

- Three isolated conversations are running the scoped trials; the matched assisted and unassisted first versions have passed their respective checks.
- Product branch: `feat/file-sharing-demo`.
- Product presentation and complete acceptance are in progress; the replacement is unpublished.

## Expanded user request

- Develop the complete shared rule network on the independent `feat/shared-policy-graph` branch in `VibeLensTrials/vibelens-policy-graph`.
- Observe how the original Skill guides the rule model, record deficiencies, improve it, and retest using the file-sharing case.
- Reference the larger task-chain policy example from conversation `01a182ad-7d40-7e52-acb1-8b9b07d17022`.
- Compare an assisted build with an isolated unassisted build, including initial tokens, later diagnosis and repairs. Control conversation: `01a18318-4fde-7633-a768-f0aff1cf25b5`.
- Answer trial design questions autonomously as a natural simulated user; preserve the actual wording and provenance.
- Explain the concept-to-code hierarchy and cross-layer references/mappings briefly on the homepage.
- Initial trials have different observability/export tasks; their raw costs are descriptive, not a clean efficiency experiment. A matched task-only retest is required before claiming a comparative benefit.

## Implementation checkpoint

- New matched assisted conversation: `01a18332-cb51-7471-83f8-990d88886b9d`, directory `VibeLensTrials/file-sharing-policy-trial-20261028`. Its first draft already contains 10 shared policy expressions and four operation roots (upload/share/view/download). View and download share `read_allowed`.
- Natural scripted answers sent to all three conversations. All use the same owner/recipient/unrelated-user scope, metadata-only viewing, and a later revocation iteration.
- The first pilot and unassisted control reached host-level `waitingOnApproval` during browser acceptance. The main chat asked the user to handle the control's execution approval; this is separate from autonomously answering design questions.
- Policy worktree has 23 passing feature tests, including actual BOProbe/JSON events, core-only execution, source moves, added conditions, fresh fact revisions, strict projection, old-proof rejection and standalone CLI freshness.
- Existing individual tests passed: code graph 22, source quality 5, dialogue 22, whitebox 8, stategraph module 11, assessment fixes 20. Canonical viewer semantic checks pass. Package check passes after `tools/sync_runtime.py`.
- Full release retest is running in the policy worktree: log `.validation/policy-release-final.log`, exec session `39065`. Earlier failures are retained under `docs/review/shared-policy/`. Both installed examples completed legitimate source-change reviews and inspect/verify/accept/check; their new frozen records preserve the old history.
- Skill Creator quick validation passes after adding PyYAML only to the local development environment.
- Token telemetry is available in local named session JSONL files. `.validation/session_metrics.py` extracts only settings/counters, never assistant reasoning or base instructions. Include the third trial and phase boundaries before final reporting.

## Resumed run: 2026-10-29

- All three trial conversations were interrupted by the host restart, then explicitly resumed. Headless Playwright replaced the stopped desktop continuation; the control has no remaining approval flag.
- The unassisted V1 passed 12 HTTP / 11 browser checks. Its V2 revocation iteration passed 20 HTTP / 22 browser checks, including a real unchanged recipient document with no intervening list request and a denied download. No business bug was observed in that accepted iteration.
- Assisted V1: build `fa390db0b5de`, candidate `739a82501fe7`; 12 application tests, 39 business assertions, 8 evidence checks, and 552-event recording/replay passed. Framework changes/retests are a cost confound and are recorded separately. The identical natural revocation requirement was sent; V2 is in progress.
- The old-Skill pilot completed real 2D/3D capture and found a layout-identity integration problem and a test-setup contamination problem. It is completing final V1 exports; these are not file-permission defects.
- Visible trial dialogue is exported under `trials/{with-skill,without-skill,pilot}/dialogue.md` and `.json`. These are in-progress snapshots, not final exports. `tools/export_trial_dialogue.py` excludes reasoning, system/developer instructions and arbitrary tool outputs; three tests verify that boundary.
- Token boundary snapshots are in ignored `.validation/file-sharing-v1-counters.json` (control V1) and `file-sharing-assisted-v1-final-counters.json` (assisted V1). Refresh per phase and report cached/noncached input and output separately.
- The new product copy and proposed flow use file sharing, reusable access checks, revocation and source drill-down. App previews now read actual screenshots at the current event; old synthetic gallery preview CSS is removed. `tools/test_file_story.mjs` passes event ordering/backward seek and conversation separation checks.
- Remaining substantial work: finish paired V2 and a clearly identified isolated diagnosis test; export runnable example and real before/after presentation artifacts; replace old case tests/capture scripts and obsolete active gallery routes; run complete bilingual browser/camera/motion/layout checks; finalize comparative evidence without claiming a fair token-efficiency result from confounded pilots; commit verified branches and then publish the updated site.

## Later checkpoint: native protocol repair

- Shared-policy feature commits `5f3cf4a` and `088514b` were pushed to `origin/feat/shared-policy-graph`; they are merged into this product branch at `df4a4f4`. Main and Pages remain unchanged.
- Assisted V2 completed: build `9de5ee5b1e2e`, candidate `47923892feaa`; 16 tests, 84 business assertions, 10 evidence checks and 12 browser screenshots passed. Control V2 already passed 20 HTTP / 22 browser checks. Neither accepted V2 exposed a natural permission defect.
- A fresh frozen-version conversation was created: `01a18512-6617-7791-aa29-f2aeb9312859`, title `文件共享复测 · 冻结版 VibeLens`, directory `VibeLensTrials/file-sharing-stable-trial-20261029`. It has the same natural answers, is preparing a design graph and must wait for graph confirmation and the next frozen source commit before coding. No runtime installation should begin yet.
- Isolated diagnosis copies exist at `VibeLensTrials/diagnosis-{with,without}-skill-20261029`. Their untouched baseline application tests passed (16 / 20). **No defect has been seeded yet.** An unmodified canonical `change_sync begin` on the assisted copy exposed a real framework gap; its `review/diagnosis-begin.json` preserves that failure. Do not treat this as the planned business diagnosis.
- The framework gap was previously hidden by the trial's `integrations/bo_schema_compat.py`: project.schema.json had an inline old model enum, and policy/data projection order oscillated. Canonical fixes are now uncommitted in the policy worktree: project schema references the canonical model resource; protocol validation registers it offline and enforces exact policy maps/orphans; policy projection preserves existing element order. The old committed source fails both new regressions (`.validation/native-protocol-before-tests.log`). All 26 updated policy tests pass, including unpatched copied-runtime validation and real data/policy composition. The actual assisted V2 project also validates with the canonical protocol without importing its shim.
- Both installed examples began a normal `policy-native-protocol-20261029` change **before** runtime copies were synchronized. Ownership seals are complete/in progress (exec session `77063`). Reviewed inspect/verify/accept/check is running through `.validation/review_native_protocol.py` (log `.validation/native-protocol-reviewed-examples.log`). Finish it, freeze the new receipts preserving history, and run the complete repository gate plus clean Git export before committing/pushing this repair. Keep canonical source stable while trials resume.
- After the repair: remove the trial-only schema/order shim through normal project upgrade/reverification; preserve this work as framework cost, then prepare the isolated diagnosis mutation. Planned common fault: revocation uses the actor identity instead of the selected recipient in its delete target. Seed only isolated copies, record the seed outside worker projects, reproduce failure, then send the same symptom without the cause to both workers. Do not alter original applications or tests.
- Product export tooling now reconstructs a recorded view from actual recording context/final/events/frames (live events may be empty after a same-build restart). It checks source hashes and produces compact code-slice references; all 56 native neighborhoods matched their hashes in a dry V1 check. Files under ignored `docs/site/viewer/_draft-v1*` are **pipeline fixtures from the legitimate V1**, not a defect story or final material. Do not publish them as a failing application.
- `story` contract now separates `business_anchors` (native path closure, preserving intermediate relations) from `actions` (`id`, actual `node`, actual `phase`, bilingual `label`), and includes `control_anchors`, `focus`, `inspection_event`, `source_focus`, `captions`, and `telemetry`. The exporter selects explicit application screenshot stages; graph screenshots do not enter the app window. `case-code.mjs` reconstructs detached native neighborhoods without duplicating all source nodes.
- Current Pages artifacts `case-data/v1.json` and `v2.json` are still the old gallery. The default build is intentionally not ready until real teaching material replaces them. `control-plans.json` currently comes from the dry V1 pipeline. All-layer UI and camera checks, gallery-test migration and full final browser verification remain pending. Preserve the old gallery artifacts in a dated/fixed archive before replacing active files.

## Presentation work still needed

### Current execution checkpoint

- Native protocol repair is committed and pushed at `e69ce09` on `feat/shared-policy-graph`, merged into this product branch at `3b46cf0`. Its 27 policy tests, complete repository runner, maintained-source check and clean staged-source export passed. Historical failures and repaired frozen examples are preserved in the shared-policy review.
- The independent assisted trial removed its schema/projector shim and CLI wrapper and passed the original 16 tests, 84 business assertions, 10 evidence checks and real recording/replay. The original pilot is now performing its own normal no-shim upgrade against this freeze.
- The fresh frozen-version trial received the scripted graph confirmation and `e69ce09`; it may now build its initial scope. Revocation remains a later iteration.
- Two disposable diagnosis copies first passed their original tests. The native assisted copy also passed canonical check and began `.stategraph/diagnosis-03` before mutation. The controlled common error changes the revocation target from selected recipient to acting owner; exact hashes and seed are outside the worker projects in `diagnosis/controlled-mutation.json`. The original delivered apps and test expectations were not modified.
- The unassisted diagnosis completed: only its erroneous SQL argument changed; all original 20 HTTP and 22 browser checks passed plus the added stale-page/other-recipient/owner/regrant evidence. Assisted diagnosis is still preserving its actual failed run and native replay before repair. Its graph exposed zero affected rows and a retained shared state; an independent SQL listener and source inspection identified the actual bound identity. Do not describe a recorded request parameter as proof of a driver's bound value.
- The previous gallery case and synthetic practice source are archived under `legacy-gallery/`. Product source is still work in progress and unpublished. `test_case_artifacts.mjs` is being migrated to actual record/source/neighborhood/capture evidence; final case exports are pending.

The product branch is intentionally unpublished while its replacement artifacts are prepared. Its current work in progress is not ready to serve: the old exported gallery artifacts must be replaced before the new contract-driven viewer is usable.

1. Finalize bilingual file-sharing chapter/dialogue copy and a compact intent diagram.
2. Export real application builds/recordings/code/source and per-event screenshots. New presentation contract: `artifact.story` supplies stable business/state/decision IDs, `focus.core/inputs/effects`, `inspection_event`, `source_focus` and bilingual `captions`; `artifact.application_frames` maps actual event IDs to screenshots.
3. `case-application.mjs` and the rewritten companion now use actual screenshots rather than a second simulated gallery UI. Finish matching CSS and browser tests.
4. Update `build_control_preview.py`, capture scripts and artifact/browser tests to read the new contract. Keep strict evidence checks, actual 2D/3D interactions and the black-flash transition regression.
5. Replace homepage screenshots; retire active gallery demo references and redirect/remove unused legacy illustration modules after checking their callers. Preserve historical gallery evidence.
6. Finish independent policy tests/formatting/package checks, record failures and retests, compare the paired trials, then decide publication from verified branches. No GitHub push or Pages deployment had occurred at that checkpoint.

## Core-first checkpoint: 2026-10-29

The user explicitly requested that all core work and acceptance finish before further promotional or demonstration page changes. The existing presentation is an unpublished draft. Do not resume its editing/deployment until the independent final framework upgrade below completes.

- Canonical policy/viewer fixes are committed and pushed as `b78f03a` on `feat/shared-policy-graph`. A complete frozen-source `tools/verify.py` run passed, along with 27 policy tests, strict example reviews, source/package/Skill checks and a clean Git export. Exact fingerprints and original failures are in `docs/review/shared-policy/checks/policy-viewer-final.json` and its adjacent receipts.
- This product branch includes that framework commit at merge `26224d8`. Presentation drafts remain uncommitted. Main and Pages are unchanged.
- Original pilot native V2 and both controlled diagnosis trials passed. Final native pilot evidence and visible transcripts have been archived. Paired token costs are descriptive and show higher assisted costs; no efficiency benefit is claimed.
- The fresh frozen `e69ce09` trial completed its revocation iteration: 35 tests, 84 scenario runs, 282 business assertions, four formal check categories and 10 negative evidence checks passed. Its real recording contains 1,731 events and 11 snapshots, with zero errors/drops/gaps. Draining took 363.125 seconds. Pending counts decreased while the producer totals remained fixed; this was bounded backlog, not demonstrated self-capture. This is not a real-time performance acceptance.
- A read-only profile identified repeated Windows path resolution in per-event source binding as a substantial cost. It did not change source validation. Keep batching/throughput optimization as a separate documented task; do not weaken freshness checks.
- Fresh trial `01a18512-6617-7791-aa29-f2aeb9312859` has now received `b78f03a` for a separate normal upgrade round. It must retain original V2 evidence, preserve business/test bytes, rerun formal checks and test actual rule animation/presets/source/2D/3D on unmodified recordings. Framework costs remain separate. Await its final result before returning to the product pages.
- Pending draft UI work after core closure: test the representative-layer opening and explicit completion receipt; repair a flaky camera gesture in the product browser test; finish controls and black-flash regressions, source formatting, artifact/source integrity, final receipts, commit and Pages verification. The homepage's stable-assets browser check passed. Earlier failures remain under `checks/`.

### Independent failure and focused repair

The independent `b78f03a` upgrade passed the original 35 tests, 84 scenario runs and 282 assertions, but its strict keyboard-source browser test failed. Returning focus after Source selected the same node again and dismissed the detail panel. Matching source/build responses and a successful visible-menu path did not make the original keyboard path pass. The overall upgrade was not accepted.

The isolated candidate `3458366f72563b35749a9f7bcf799c2b7e22da00` on `fix/semantic-focus` reads the current semantic selection in the focus callback. Its regression fails against the previous source and passes after the fix. Both shipped examples completed normal new review/verification/acceptance records. Package, source and clean Git-export checks passed. A complete repository run and an independent normal upgrade with the same original keyboard sequence are in progress. No freshness check, business rule, test expectation or recorded event was weakened or rewritten. The candidate remains separate until these checks finish.

The suspected old-recording source mismatch was rejected: existing recording-version validation already blocks that request. A real HTTP regression preserves the old-version rejection, current full-file response and zero business events from source reads.

Promotional and demonstration page editing and deployment remain on hold during this core repair and acceptance.

The complete frozen-source `tools/verify.py` run passed on the unchanged clean `3458366` worktree. `.validation/focus-final-result.json` binds its log, all 240 Skill file fingerprints and both frozen example candidates to that revision. The independent original keyboard test also passed without changing its script or adding a rerender. Its full-source/version/replay and original business regression round is still in progress; page work remains paused until its final result.

### Core acceptance complete; product draft resumed

The final independent upgrade completed on `3458366`: all four formal categories, original 35 tests, 84 scenario runs, 282 business assertions and ten negative evidence checks passed. The byte-identical strict keyboard test and extended full-file/highlight/version checks passed in live/replay. A fresh 429-event/11-snapshot recording passed Boolean dependency, short-circuit, authorization preset and 2D/3D regression with zero errors/drops/gaps and zero observer-generated business events. Its 121.584-second drain is retained as a throughput limitation, not a performance improvement. The original b78 failure remains unchanged.

The core branch is pushed at `098b46b`, including full frozen-source receipts and the independent repair evidence. This product worktree includes the fix and evidence at `c9684cd`; all 240 Skill bytes match the tested freeze. The completed failed/final upgrade folders, source/evidence archives, per-round costs and visible dialogues are retained under `trials/frozen-repeat/`. Archive settings/name checks passed for 26 nested archives and 3,448 files.

Only after this core closure did product-page work resume. The first remaining browser test used a bottom-of-canvas coordinate that could fall outside the visible iframe after translated layout. The harness now checks a visible, unobstructed canvas point and releases the same right mouse button it presses. Camera rotation/zoom/pan assertions remain unchanged. The new stable-asset run is in progress; viewer assets are not rebuilt while a browser check is reading them.

### Core reopened by controlled-view integration

The complete bilingual case browser passed, including all eight views/layers, 494 static-code nodes, saved views across builds/reload and genuine camera gestures. Source inspection now uses the existing native Locate action when a large saved region cannot fit beside the source file; it preserves view membership and layout. Artifact, runnable-core, dialogue-export, source/lint and formatting checks passed. The final conversation-control browser then failed: after the business view, `policy:read_allowed` was requested but hidden, while the controller reported `applied`.

This is a native integration defect, not an omitted source rule. A simplified display boundary had removed the rule's parent, and the controller reused that projected ancestry when computing hidden nodes. A separate `fix/control-ancestry` worktree now restores canonical ancestry while retaining captured fields, opens required ancestors, and refuses success when a requested node remains hidden. The same final unit fails against the previous Git module and passes with the repair, including a rejected acknowledgement negative. The unchanged bilingual browser harness passes against an isolated copy with only the two candidate native assets replaced. Both shipped examples completed new normal reviews; full frozen-source and independent native-project acceptance are next. Pages remain paused during this reopened core repair.

The clean candidate is `3052e03c32e9bbfcdc19961cad36085415795433` at `VibeLensTrials/vibelens-control-fix`. Source formatting/lint, Skill validation, package checks and a clean staged Git export passed. `tools/verify.py` is running against that unchanged freeze (`.validation/control-final-full.log`, exec session 76265). The same independent trial is testing a normal native upgrade and actual scoped `bo_control.py` requests in turn `01a1864e-affc-7843-ac8b-450252965dac`; preserve all business/test bytes and request-node visibility assertions.

The isolated candidate also passed the compositor regression: 40 transitions across English/Chinese and 2D/3D, with zero black frames. Its exact two candidate assets are recorded in the fixture proof. The final product/browser chain had stopped at the original control failure; screenshots, artifact checks and homepage release checks resume only after this core round completes. Local draft stays at port 8894; isolated candidate fixture is port 8896. No main/tag/Pages publication has occurred.

### Final control acceptance and five-step presentation

The frozen `3052e03` complete repository gate and independent native upgrade passed. Original 35 tests, 84 scenario runs, 282 assertions and ten negative controls remain unchanged. Main/detail controls expose every requested node (13/13 and 14/14); ancestry, captured values, filtered replay, 2D/3D, reload, explicit source selection and missing-prefix rejection passed. The original strict keyboard-source sequence still passes. Observer actions add zero business events. Public evidence is exported under `trials/frozen-repeat/native-3052` with exact session/profile masking and original/public hashes; private configuration stays local.

Only after this core closure did page editing resume. The user's latest requirement condenses the public story into five steps: confirm the flow, record the failure, inspect a focused path, ask AI to repair it, and verify the next run. Custom view editing moves into inspection. Display-only cleanup removes known authoring boilerplate without changing raw recordings, sources or model semantics. `references/graph-writing.md` supplies the reusable generation prompt; it retains business constraints and actual diagnostics.

Clean product integration first exposed missing linked trial files, then the old gallery controller test's dependence on replaceable marketing data. Its input is now a byte-frozen fixture with provenance; all 16 original tests remain and an added fixture hash check makes 17. The unchanged native controller browser passes. The legacy gallery business regression keeps its assertions and exports to private evidence rather than overwriting the new product story. Earlier integration failures are retained. The final five-step browser/full staged integration are in progress.

### Local acceptance complete

The complete clean-export `tools/verify.py` run passed at staged tree `0bfd2ff30f9e658ff5f55d4db2df3493f54c18ee` (908 code files), retaining frozen example approvals. Final presentation work changes only the scene driver, its host and browser harness; the release delta receipt binds those files to their final browser/source/unit checks. The canonical runtime and all application/test expectations from the full gate remain unchanged.

Final five-step case acceptance passes English/Chinese: eight confirmed business nodes, five visible source-focus nodes, 17 saved nodes across builds/reload, eight presets and eight layers, 494 loaded source nodes, actual motion, camera gestures, source, mobile and reduced motion. Homepage and scoped controls pass. Compositor checks pass 32 transitions and 2,324 frames with zero black frames. Original failures are retained; display assertions now distinguish hidden layout inventory from rendered glyphs and verify semantic parity. Save waits for the native preview; the scope action retains saved-view projection semantics. Final artifacts were rechecked sequentially after image capture.

Skill validation, source formatting/lint (110 Python and 68 JavaScript modules), exact 64 source checks, package/copy checks and archive checks pass. Git publication and deployed Pages verification are the remaining release steps.
