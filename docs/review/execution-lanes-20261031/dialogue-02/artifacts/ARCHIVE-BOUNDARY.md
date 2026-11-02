# Stopped Trial: Reproduction and Archive Boundaries

## Disposition

Stopped on the forwarded coordination instruction in `stop-instruction-004.txt`. Runtime mapping acceptance has **not** passed. No `change_sync accept` command was run, and `.stategraph/initial/accepted.json` does not exist.

Do not resume repairs, synthesize return events, switch collection mechanisms, remove data operations, weaken checks, edit the Skill/framework/installed copies, or publish this version. A future test belongs in a new independent conversation and project after the maintained framework is repaired.

## Complete failed gate

- Candidate: `8de395cf982cceee21772ee18c5a04f32f8826eadf06a484a8081a5e8afd900b`.
- Observation build: `dd6d3fdca111361c3ac972f18000640558c632e57df35d38fcc9a0c300ff3b54`.
- Complete result: `verify-001.json`, also retained in `.stategraph/initial/verification.json`.
- Original command/result wrapper: `.stategraph/initial/checks/observations.json`.
- Original payload: `runtime-observations.json`.
- The archive integrity check confirms that the original wrapper hash equals the completed gate's `observations_hash`, and its JSON stdout equals the saved original payload.
- Mapping: failed with 11 unclosed-invocation reports for successful data transactions and transformations.
- State constraints: passed in the configured finite scenarios.
- Business: 12/12 required assertions executed across four scripted cases and observation on/off/fault.
- Configured project tests: four real Flask-handler/independent-SQLite scenarios passed.
- Enabled probe/data health, shared-policy evidence, implementation coverage, public export and protected projection comparisons passed separately. These do not override the failed mapping result.

The cases use synthetic accounts/files. They are scripted application tests, not human usability testing.

## Current source and interrupted later verification

The current source is later than the complete failed gate: it includes a stricter empty-CSRF check and a versioned ownership/import-boundary declaration added before the stop instruction.

- Last inspected current candidate: `088022db32017c9ac788641b838a68b8ae1bdc1dc25895e66d9b0ddc375dc846`.
- `verify-002.json` is empty because the ongoing verification was interrupted when the stop instruction arrived.
- It has no final verdict and is not an additional passed or completed failed gate.
- The archive's `source/` is the exact source at stop. Do not attribute gate 001's result to that later source.
- Gate baselines, source indexes, review decisions, command outputs and original bytes remain preserved. No baseline was reset.

## Shared-framework reproduction

`framework-issue/reproduce.py` imports the requested canonical Skill directly. It runs a real SQLite commit and an actual scalar transformation, retains their four native probe events, and invokes the unchanged canonical invocation-closure checker.

Observed pairs: `db_transaction: enter → commit`; `db_metadata: enter → change`. The checker ignores `commit` and `change`, then reports missing exits. The commit count is independently 1; the selected transformation result is `size=7`. This reproduction is separate from application source mapping, and its events were not ingested as application evidence.

See `framework-issue/README.md`, `reproduction-result.json`, and `reproduction.log`. Relevant canonical/copied file hashes match. The installed runtime/viewer manifest has no file conflicts; the native executor is byte-identical to its canonical source.

## Dialogue provenance

The business-user role was **simulated by the coordinating AI**. U001/U002/U003 are scenario requirements, answers and graph confirmation. The forwarded messages were actually received, but their receipt does not establish an independent human participant or human acceptance.

`PROVENANCE-CORRECTION.md` and `provenance.json` supersede earlier unqualified "actual user" / "No simulated answers" labels. Raw text and old artifacts are preserved without rewriting their historical contents. This trial is not an independent human usability study.

## Runtime and unrun checks

The only browser screenshots are from the design stage. The implemented application was not launched for browser testing. Live runtime recording/replay, focused recording, observer-control exclusion in a real browser, physical core packaging, and final delivery acceptance remain unrun.

The owned design server (PID 90368, verified by its exact project command line) was stopped. Host-side checks report connection refused on 8972 and 8973; see `stop-process-check.json`.

## Archive contents and exclusions

The final archive contains current application/native state/rule source, unchanged installed observer/viewer source, declarations, confirmed simulated-scenario requirements, complete failed gate and original observations, incomplete attempts, shared-framework reproduction, architecture checks, design screenshots and provenance corrections.

Dependencies in `.venv` are not duplicated. Requirement versions and installation/failure notes remain. The session-secret file is excluded. Available SQLite files and observer JSONL data are retained as local synthetic trial evidence. No data is uploaded or published.

`archive-20261031-stopped-01/` is an incomplete archive attempt caused by console-output encoding during indexing.
`archive-20261031-stopped-02/` is a complete snapshot made before the final host-side design-server stop.
The final `archive-20261031-stopped-03/` adds the verified stop record and this boundary report. Earlier snapshots are retained unchanged.
