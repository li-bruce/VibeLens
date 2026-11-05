# Trial review and clearer implementation views

The completed independent chat is **not a complete acceptance pass**. Its configured business cases passed, while formal delivery, two state-frame associations and recording eligibility still failed. See the [assessment](TRIAL-ASSESSMENT.md), [public dialogue](dialogue/dialogue.md) and [original result](trial-evidence/RESULTS.md). No later business iteration was performed in that chat.

This change improves presentation and display classification. It does not claim to repair those three independent-trial failures.

## Changes

- Implementation detail has three display planes: **Entry points**, **Project structure** and **Code execution**. The existing semantic implementation classification, node IDs, bindings and recorded facts remain unchanged. API handler calls, captured values and database operations are execution detail; stored schemas retain their own plane.
- The default view remains business, states and rules. Old implementation selections expand into the three planes, preserving narrow facet exclusions. Timeline uses the same display classification.
- The home page explains one development loop: confirm the model, inspect actual behavior, then refine the implementation. It uses native screenshots and a seven-plane interactive explainer, with English and Chinese copy.
- The walkthrough follows a single revocation defect. Five stages separate Codex development from application operations and VibeLens investigation. The confirmation dialogue contains business, state and shared-rule views. A focused native graph keeps the actual relation between revocation and its database operation.

## Story and evidence

The story was presented in the coordinating conversation before screenshot capture. See the [five-stage script](STORY.md). The case uses the existing file-sharing execution artifacts: its deliberately seeded defect is disclosed in the linked provenance. It is separate from the completed independent trial above.

![Confirm the model](screens/confirm-zh-CN.png)

![Follow the result into source](screens/inspect-zh-CN.png)

The published screenshot inputs are the original native viewer, preserved source and original recording. No screenshot or event was painted to manufacture a result. [Capture provenance](../../site/images/capture-proof.json) records the build, event, selected node IDs and image hashes.

## Checks

| Scope | Result and evidence |
| --- | --- |
| Display identity and filter migration | [49 JavaScript regression groups](checks/unit-results.json), including all 32 old implementation facet combinations |
| Python/JavaScript observation classification | 19 observation-continuity tests; semantic classification remains distinct from display planes |
| Native walkthrough | [Browser checks](checks/case-browser.json): both languages, five stages, actual moving edges, source, saved views across builds/reload, eight presets, seven occupied planes and mobile |
| Product home | [Home checks](checks/site-browser.json): keyboard image switch, language switch, seven layers, responsive layout, replay and reduced motion |
| Cold startup | [Six fresh contexts](checks/startup-browser.json): delayed child data, one localized navigation, same-viewer story handoff |
| Concurrent real execution | [Execution bands](checks/execution-bands.json): two users, real SQLite writes, closed calls, resource dependency curves, collapse and depth controls |
| 2D/3D interaction | [Layered viewer](checks/layered-browser.json): source ownership, hidden layers, multi-layer persistence, spatial drag, undo and replay |
| Concept-model runtime | [Concept checks](checks/concept-browser.json): actual app operations, independent concepts and cross-layer bindings |
| Timeline component load | [20,000 synthetic events](checks/timeline-performance.json): initial render 240 ms, seek p95 31 ms, draw p95 19 ms in this run; excludes complete graph reconstruction |
| Source quality | [Syntax, lint and formatting](checks/source-quality.json); normal package-copy and document checks |
| Maintained examples | [Two accepted changes](checks/example-maintenance.json): mapping, state rules, project checks and 96/189 business assertions passed; protected business source and requirements retain their previous hashes |
| Complete repository regression | `python tools/verify.py --database` passed in 480 seconds; [full output](checks/full-regression.txt) includes installation, multi-language checks, actual effects, observer-free exports and both maintained examples |
| Clean installation source | [Git export check](checks/clean-export.json): both examples pass using only the committed files and frozen approvals, without regeneration or reapproval |
| CI browser follow-up | [Graph geometry](checks/graph-quality-followup.json) and [API causality](checks/api-followup.json) pass with the split display planes; [seven further browser runs](checks/browser-followup.json) cover Timeline, naming, captions, native lifecycles, mid-span recording and concurrent execution |
| Published pages | [Live browser checks](checks/published-browser.json) passed in both languages, including all five story stages, camera drag, saved views, source comparison and mobile layout |

The [delivery record](checks/delivery.json) contains the tested base, source fingerprints, exported example trees and open trial gaps. The database scope includes adapter regression and local SQLite execution; external live database services were not rerun for this presentation change. This result is separate from the failed independent trial. The [file manifest](manifest.json) records the review artifacts and their hashes.

## Failures and corrections

1. The confirmation dialogue called document-level `scrollIntoView`, which advanced the story and hid its continuation button. It now scrolls only the conversation panel. Both language flows pass.
2. The focused graph excluded `contains`, separating the action from its observed database operation. Its original, typed relation is retained; the small inspection view uses the native directed layout. Broader views retain clustering.
3. A test dragged the graph center, which can hold a node. The camera test now uses empty canvas. Rotation remains independently checked by the native walkthrough regression, including zoom and pan.
4. A fixed test port attached to an unrelated local server and received 404. A shared test-host helper now owns an ephemeral port. Test semantics were retained.
5. Old browser assertions expected the former implementation row name and its alphabetic order. Assertions now explicitly check the new planes, their order and their saved visibility. Old-filter migration has independent regressions.
6. The restricted environment blocked Windows directory-link fixtures. The unchanged eight tests passed in the normal local environment; the full run was repeated there. The original failure log is retained.
7. Copied viewer assets changed the maintained examples' managed-file hashes. The full suite correctly refused their stale approval records. Each example was restored to its prior accepted files to begin the change, then received the pending assets again, followed by architecture sealing, inspection, review, verification and acceptance. New receipts are saved alongside the old ones. Business requirements and expectations were not changed. An intermediate parser-environment failure was retained and corrected by selecting the installed JavaScript adapter.
8. The additional GitHub browser job found a geometry test still clicking the former `implementation` layer. The adjacent API browser test also expected API and operation intervals on that same row. These tests now select `symbols` for captured execution, and explicitly check business → entry → execution calls and returns. Exact method/status values, measured durations, source identities, drag bounds and restoration assertions remain in place. The [decoded CI log](failures/github-graph-quality.log) is retained; both tests and all seven remaining browser variants passed locally after correction. No runtime code changed in this follow-up.

Failed runs and screenshots remain under [failures](failures/). Historical evidence elsewhere in the repository was restored rather than overwritten by the new performance run.
