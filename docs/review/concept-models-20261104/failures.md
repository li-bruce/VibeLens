# Failures and repairs

## F01: preview argument shadowed by the graph envelope

- Commands: `python tests/test_iteration_dialogue.py` and `python tools/test_web_continuity.py`.
- Initial results: 7 tests, 1 failure/1 error; 11 tests, 2 errors.
- Evidence: `bo_design.py:185`, `TypeError: unhashable type: 'dict'` at `if view not in {"business", "state", "rules", "all"}`.
- Cause: the new requested view name was overwritten by the existing local graph-envelope variable.
- Repair: use `envelope` for the graph payload; preserve the explicit view selector.
- Retest: iteration dialogue passed 7/7. Web continuity exposed F02 below.

## F02: legacy business preview dropped a condition node

- Command: `python tools/test_web_continuity.py`.
- Initial result: 11 tests, 1 failure; `download` was absent from the default preview.
- Cause: applying the new business-plane selection to version 1, which mixes conditions and states into the same business network.
- Repair: retain the complete legacy default roots; version 2 independently selects the requested conceptual view.
- Retest: web continuity passed 11/11.

These failures occurred during implementation, before the complete conceptual backend was available. They are not results for a released build.

## F03: source enrichment invalidated the exact policy projection

- Found in the independent file-sharing trial when combining `policy.project`
  with `code_structure.enrich` and then calling `validate_project`.
- The gate rejected a maps relation outside the expected policy projection.
- Cause: enrichment added declaration fields to policy-owned nodes and a new
  canonical declaration changed the policy projector's choice of source anchor.
- Repair: retain policy-owned node metadata and stable anchors; add explicit
  source-binding relations without changing policy meaning.
- Retest: both composition orders, repeated projection/enrichment, and rejection
  of a forged policy relation pass. The trial then loaded its real bound model.

## F04: preview exports could overwrite their own input

- Independent review reproduced `preview --out discovery.json` and the companion
  collision from `preview --out discovery.md` in a temporary project.
- Cause: export checked containment, but not input/output separation. The same
  issue affected concept CLI outputs aimed at configuration-selected inputs.
- Repair: shared `workflow/artifact_paths.py` preflights every output, configured
  and explicit contract inputs, source paths, and workflow evidence before writes.
- Retest: direct, companion, configured-input and workflow-evidence collisions
  reject without modifying the contract. Existing unregistered source/configuration
  files are protected too; new outputs must use the declared report formats.
  Normal Markdown/JSON export passes, including repeated reports under `review/`.

## F05: old layer expectations remained in regression scripts

- Full verification first stopped in `test_source_documentation.mjs`: expected
  `execution`, received the consolidated `implementation` concern.
- A later run found an old six-row expectation in `test_telemetry_view.mjs`.
- Repairs preserve source-range, causal and event assertions while checking the
  new concern and original implementation facet separately. Concurrent execution
  bands retain one row per represented concern and each user's own events.
- Final aggregate retest is recorded in the acceptance report.

## F06: version 1 binding fields were still required by the version 2 wrapper

- Core concept bindings passed, while `requirements_dialogue.assess` additionally
  demanded legacy `model_nodes` and the entire unscoped rule draft.
- Repair: version 2 uses its checked semantic scope and `model.concepts` bindings;
  version 1 retains its original mapping checks and now compares full rule meaning.
  All active business node kinds remain subject to binding checks.
- Retest: public workflow tests cover legacy operator drift and version 2 scoped
  binding; the independent trial exercises the same public commands.

## F07: display metadata stripping removed legitimate business values

- Review found that recursive removal of `label`, `summary`, `description`,
  `source_refs`, `documentation` and `presentation` also removed identically
  named keys inside business values, rule arguments and independent assertions.
- This could hide a real semantic change behind an unchanged confirmation hash.
- Repair: remove display metadata only from known record envelopes. Preserve
  complete nested business JSON, event/context keys and resource identities.
- Retest: the concept suite passes 36 tests, including these keys in domain
  payloads and a Boolean-to-number mutation (`false` to `0`).

## F08: conceptual selection did not reach capture owners

- Integration review found that a conceptual node could be displayed while
  custom-view selection and region recording still searched native nodes only.
- A design ID different from its implementation ID therefore had no usable
  capture binding. This is a shared framework issue, not a trial-only defect.
- Repair: one shared resolver accepts only exact, validated concept-to-native
  implementation bindings. Control inspection, queued view application and region
  recording use the same inventory. Source targets require exact capture owners.
- Retest: 10 capture/control tests include actual HTTP activation, inspect, plan,
  application and queued validation with different concept/native IDs. Runtime
  projection preserves each real invocation, rather than assigning an invented
  lifetime to the conceptual parent. Browser checks also found F11 below.

## F09: unrelated future questions blocked the current increment

- The concept core respected `discovery.scope`, but the dialogue wrapper still
  required implementation links for every resolved question and scheduled every
  open question, including unrelated future features.
- Repair: use the confirmed semantic scope plus question prerequisites for the
  current implementation gate. Validate record shape, references and decision
  history across the entire document as before.
- Retest: the public workflow suite passes 21 tests. An unrelated future question
  stays pending; an active question's unresolved prerequisite still blocks it;
  invalid evidence anywhere in the document still fails validation.

## Environment interruption

The sandbox rejected temporary Windows junction creation. Full verification
stopped with real errors; the tests were not skipped. The unchanged junction
checks were repeated with approved tool permissions. See
[source verification](source-verification.md) for the isolated reproduction.


## F10: standalone model imported the observer

- Shipping-example checks failed with `ModuleNotFoundError: bo_observer` after
  source enrichment. The new source-reference validator lived in the observer
  package even though the independent native model needed that contract.
- Repair: move deterministic declaration IDs and pure reference validation into
  the standard-library-only `bo_contracts.py`. Source adapters reuse the same
  implementation. No import-path workaround is needed in application code.
- Retest: 14 source identity tests pass, including an isolated Python process
  containing only the three native stategraph files and an import guard that
  rejects any observer dependency. Forged declaration references still fail.

## F11: focused capture submitted a snapshot without evidence

- Actual browser recording of a selected sharing operation returned HTTP 200,
  captured nine facts, but ended interrupted with one producer transport error.
- Cause: region filtering correctly omitted a separate state-read event;
  `record()` returned `None`, but `snapshot()` still queued that missing identity.
  The collector correctly rejected the snapshot.
- Repair: Python and JavaScript probes omit a snapshot when its source evidence
  was not captured. Existing capture errors remain unhealthy. Non-null IDs still
  undergo strict collector validation; no synthetic evidence is created.
- Retest: three cross-language regressions pass. The same real HTTP operation
  records nine facts, closes spans, and stops with zero errors and no gaps.
  See the trial's focused-capture before/after evidence and browser report.

## F12: shipping graph builder wrote an incomplete failed scan

- Example migration uncovered a missing JavaScript adapter: the scanner reported
  errors, but the example builder could still write a partial source projection.
- Repair: both maintained example builders reject scan errors before replacing
  the graph. The normal configured adapter remains required.
- Retest: a missing-adapter invocation returns nonzero and leaves the graph hash
  unchanged. Complete builds retain every previous native node and add the exact
  physical declaration references. Migration uses the real prior accepted Git
  baseline; old approval records are not rewritten.


## F13: implementation comments renamed confirmed business actions

- Final screenshot review found `Share file` replaced by a truncated function
  docstring. Name selection prioritized source documentation over authored
  business labels; merging a shared concept/native ID also lost the concept name.
- Repair: preserve the conceptual label as a display overlay. Explicit user/AI
  names win, followed by the confirmed concept or business label. Source comments
  remain available for concrete API/function names and detail. Source-name mode,
  native IDs, parameters and lifecycle evidence remain unchanged.
- Retest: naming, source-documentation and concept-observation regressions pass;
  final browser screenshots use the running project with the corrected labels.

## F14: scope filtering falsely completed initial-state registration

- The independent trial set its local initialized flag before checking whether
  its snapshot was queued. A deliberately filtered first read could therefore
  suppress the next actual initial-state observation when capture widened.
- Repair: the example marks initialization only after `snapshot()` returns true.
  The setup guide now makes this producer responsibility explicit; unavailable
  pre-state is never inferred from a later result.
- Retest: real focused-to-full capture on the same instance, all 15 case/mode runs,
  and a fresh portable replay pass. Original failed and accepted receipts remain
  in the trial evidence rather than being overwritten.


## F15: recording metadata queries rescanned the source tree

- Aggregate verification stopped in the unchanged capture-settlement regression.
  The expanded control context had become the recording version provider, so
  listing/reading saved recordings also requested a full project source view.
- Repair: keep a lightweight pinned `recording_version_context` for recording
  identity checks, and a separate complete static context for control inspection.
  Initial recording context still contains the actual project tree.
- Retest: all 14 original settlement tests pass, including the explicit rejection
  of source rescans and runtime assembly during metadata reads. Concept capture
  and exact control inventory checks remain unchanged and pass.


## F16: concurrent acceptance jobs overlapped receipt writes

- The aggregate suite reached its final archive-example preparation while a
  separately launched example acceptance was updating the same local receipt.
  `check` correctly rejected `accepted verification differs` during that window.
- This was test orchestration, not a source change or a relaxed model contract.
  All earlier aggregate steps and the separate archive invocation had passed.
- Repair: stop concurrent writers and rerun the complete repository command with
  a single writer per example. The failed aggregate log is retained as
  `root-evidence/failure-verifier-overlapping-acceptance.log`.
- The acceptance report records the subsequent serial command's exit status.
