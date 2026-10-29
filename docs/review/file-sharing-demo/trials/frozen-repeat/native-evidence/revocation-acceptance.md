# Revocation V2 acceptance record

Date: 2026-10-29 (Asia/Shanghai).

Status: the authorized revocation iteration is implemented and its finite automated checks passed. Canonical accept/check passed for the current candidate. The simulated design restatement is explicitly recorded; this is not independent human or production acceptance.

## Scope and behavior

Only a file's owner can cancel the selected recipient's relation for that file. Cancellation commits one targeted relation deletion and the corresponding native state transition in the same SQLite transaction. Every subsequent download reads current permissions, including a request made from an unchanged recipient page. The owner and all remaining recipients retain access; other files are unaffected. Removing the last recipient returns the file to private state. The existing share operation can grant access to the same recipient again.

The changed business graph was displayed before implementation. Request provenance, the explicitly simulated restatement, and technical interpretations are retained in [revocation-design-dialogue.md](revocation-design-dialogue.md) and [revocation-design-preview.md](revocation-design-preview.md).

No registration, public links, teams, approvals, preview, editing, deletion, promotion page, or additional business workflow was added. Revocation governs subsequent requests, not bytes already downloaded or transfers already in progress.

## Frozen identities and preservation

- Installed canonical revision: `e69ce0921ac06fb455ec0aedc403e24d74babebc`.
- Accepted candidate: `239b9b6314b8fd5d224b03715013e9c5bf4918d3e30aad64aa209f97b43c0d01`.
- Build: `843e214363b362d939aba82229a7abf66f6ed128d52b978b4867f03ccb22cf67`.
- Active immutable change: `.stategraph/revocation-v2/`, based on accepted candidate `de568f8032081e09018f41908949af30c344eea3526db17bae16a258f218f18f`.
- Revocation baseline SHA256: `e4c0ca6310436c999793c0c92a6570e01d9fdd29074bf948b48858c9d5d5f16c`.
- Original initial baseline SHA256 remains `8339139b0637be9abdea6611a1952bccce286954ea2ceca351ec0293456c79f7`.
- All 29 preserved pre-change source/contract files match their recorded hashes. All 26 original business checks, 20 cases, and original whitebox rule/check remain intact; 68 checks and eight cases were added. See [revocation-preserved-expectations.json](revocation-preserved-expectations.json).

The old project boundary assertion that an excluded revoke route returned 404 was updated because this user request explicitly brings that route into scope: an owner request without a selected recipient now returns 400. Registration/edit/delete exclusions and all original business expectations remain checked.

The 196 managed framework files and the separate native executor match their installed frozen hashes. No source was copied from the changing upstream worktree. Framework validators, projectors, sender, viewer, executor, and framework tests were not patched. A later framework upgrade is a separate iteration. See [revocation-canonical-parity.json](revocation-canonical-parity.json).

## Results kept separate

| Category | Result | Evidence |
|---|---|---|
| Implementation mapping | Passed: 15 features, 396 witnesses, 474 projection checks; actual policy/data evidence and public exports validated | [Native verification](revocation-verify.json), [evidence audit](evidence-checks.json) |
| State constraints | Passed: real pending/upload/private/share/shared paths, revoke/shared with another recipient, revoke/private with no remaining recipient; raw storage journals and exact native frames agree | Current observations receipt, browser recording, evidence audit |
| Business rules | Passed: 84 real case/mode runs, all 282 required assertions | `.stategraph/revocation-v2/checks/observations.json`, native verification |
| Project checks | Passed: 35 pytest cases in 85.35 seconds; architecture guard; current canonical accept/check | `.stategraph/revocation-v2/checks/test-0.json`, [architecture](revocation-architecture.json), [accept](revocation-accept.json), [check](revocation-check.json) |
| Browser/UI | Passed: real owner controls, unchanged recipient page's next download returns 403, exact bytes retained for owner/other recipient, re-sharing, last-recipient private state, another file unaffected, locale/layout regressions, recording/replay and rendered reload | [Final browser report](browser/20261029T034258Z-7c262b/report.json) and neighboring screenshots |
| Observer isolation | Passed: on/off/fault modes, slow bounded queue, business behavior without observer modules | Project tests, [core reproduction](revocation-core-reproduction.json) |

The 84 runs cover the 28 scenarios in each of on/off/fault mode. Enabled-mode offline evidence contains 2,957 real events; off/fault runs contain zero delivered events, with intentional observer faults verified independently of business success.

New cases cover owner cancellation, nonowner/anonymous rejection without effects, unknown recipient rejection, idempotent cancellation, the last recipient, re-sharing, and access to another file. Independent assertions compare actual HTTP statuses/bytes and SQLite ownership/relations/state; they do not treat observer events as business authority.

The canonical sequence completed source scan, inspect, verify, accept, and check against the same baseline and candidate. The architecture guard and managed-copy hash audit also passed. No baseline was reset and no old assertion was weakened to obtain a pass.

## Real browser recording and drain

Final recording ID: `77ae11709c33488ca6b294097e7d86da`. The report and actual recording remain together in the linked browser evidence directory.

The final report contains **1,731 real events and 11 state frames**, zero recording gaps, zero page errors, and zero unexpected console errors. The single expected resource error is the exact download URL's tested HTTP 403 and is recorded separately. File bodies, session tokens, and passwords are excluded from event captures.

Primary-file frames: `pending → private → shared → shared → shared → shared`. The revoke frame retains only Zhoulan's relation. Secondary-file frames: `pending → private → shared → private → shared`. Its revoke frame has no recipients. Four actual event IDs were selected in the native timeline and checked against active states, including both revoke outcomes. Recording/query/source controls emitted no business events; reload rendered the current graph.

Queue drain took **363.125 seconds**. Across 35 recorded samples, the enqueued count stayed fixed, pending envelopes fell to zero, and accepted counts converged exactly. Final capture errors/drops and recording gaps were zero. The [drain analysis](revocation-drain-analysis.md) retains sample counts, the actual wait predicate, last HTTP response, configuration, read-only profiling, and its limits. This is capture-completeness evidence; real-time performance is not claimed to have passed.

## Independent evidence sensitivity

Ten counterexamples passed using in-memory evidence or checked temporary copies only. The original six controls remain: missing download field, incorrect download value, missing exported instance, unsynchronized source, an actual isolated SQLite column rename, and a removed upload transition frame. Added controls detect a missing revoke capture field, a wrong captured input target, a wrong output target echo through a supplementary independent comparison, and a removed revoke transition frame. Both actual public exports validate, both files' complete raw transition paths match recorded frames, and preserved baseline/source hashes match.

An earlier audit deliberately changed the output recipient echo but asked the native checker to detect it through a value witness configured for the input target. It did not reject that undeclared output value; the failed control is preserved in [evidence-checks-unbound-echo-attempt.json](evidence-checks-unbound-echo-attempt.json). The final audit correctly tests the declared input witness and additionally checks both actual input/output targets against the scenario's independently requested recipient. This does not claim native value coverage for an undeclared field or modify the framework. Final results: [evidence-checks.json](evidence-checks.json).

## Core reproduction

Current archive: [core-revocation-v2-843e2143.zip](../dist/core-revocation-v2-843e2143.zip), 37 files, SHA256 `05d2b448a80214363a40b86ef866ca5dc959078613649e546d5a9278f479ca9f`.

Every archived file matches the current source. In a checked temporary extraction, real login/upload/share/download, unrelated-user denial, targeted revocation, retained owner/other-recipient bytes, re-sharing, and last-recipient private state passed. No `observer_runtime`, `bo_observer`, or `integrations` module was present/imported. The temporary extraction was removed. Historical initial and intermediate archives remain separate. See [reproduction report](revocation-core-reproduction.json) and [canonical package receipt](revocation-core-package.json).

## Failure history and limits

- A browser start found the local graph unavailable after a transient view-save startup conflict. Its failed report and launcher/server logs remain. The final services were started after synchronization completed.
- Attempt `20261029T032537Z-ecb3d9` completed the business checks but failed capture transport diagnostics. Later diagnostics reported six errors, zero queue drops, and a recording gap. Its failed report/recording remain. The project adapter now supplies the existing public transport timeout option as 10 seconds; no framework transport code changed.
- Attempt `20261029T033150Z-ff922f` exceeded the 300-second drain budget with zero producer errors/drops. The recording was later interrupted by shutting down the superseded build; its shutdown gap is retained. It remains failed. The final run independently proves actual drain progression/completion with a 900-second ceiling and the original zero-error/drop/gap requirements.
- The first native observation command exceeded 240 seconds; [its timeout receipt](revocation-first-observation-timeout.json) remains. Superseded verifier runs were stopped before source-bound harness changes; no mixed-source result was accepted. The final full suite used a bounded 900-second command budget and passed.
- Concurrent view writes caused a model-build/startup conflict. Project-owned services were stopped before the final synchronization; the framework was not repaired. The package tool refused to overwrite an intermediate archive, so the current archive has an explicit build suffix.
- An initial read-only timing probe used a restricted process's incorrectly resolved relative root and reported stale. It is marked discarded in `revocation-binding-cost-discarded.json`; the corrected absolute-root measurements all reported current.

The known incomplete matching of Boolean dependency `data` events to logical `guard` replay edges is **unchanged and not claimed fixed**. See [known-framework-limitations.md](known-framework-limitations.md). Unknown dynamic/library-call candidates remain unknown; these finite checks are not complete semantic proof, production readiness, or a human acceptance claim.

No other trial/source-chat history was inspected, no outgoing chat message or GitHub push was sent, no canonical working-tree files were consumed, and no promotion materials were produced. The application database was not reset.

## Run and checkpoint

From this project, run `.venv/Scripts/python.exe -B -X utf8 run.py`. Application: <http://127.0.0.1:8840>. Developer graph: <http://127.0.0.1:8841/graph>.

The usual full project gate is `tooling/check.py`; the repeatable browser/evidence checks are `review/browser_acceptance.py` and `review/evidence_checks.py`. Use the project Python environment. Current V2 work is complete at the frozen revision. A new framework revision requires a separate ordinary upgrade and regression iteration.
