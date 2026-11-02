# Failure, Fix, and Retest Log

## DESIGN-001: unsupported decision topic values

- Stage: authored discovery metadata validation, before business implementation.
- Actual command: `requirements_dialogue.py validate --file discovery.json`.
- Observed failure: `invalid_decision` for `D_REVIEWER`, `D_ACCESS`, and `D_REJECTION`.
- Cause: assistant-authored topic strings were not members of the canonical topic enum.
- Repair: use canonical topics while preserving the questions, stable IDs, and unresolved status.
- Retest: canonical topic values passed validation with no errors. After U002, only `D_GRAPH_CONFIRM` remains open; see `discovery-validation-003.json`.
- Classification: trial authoring error; no framework modification or compatibility workaround.

## ENV-001: listener inventory unavailable

- Read-only `Get-NetTCPConnection` failed because the CIM resource was unavailable.
- A Python socket bind check subsequently confirmed ports 8972 and 8973 were available.
- No unrelated process was stopped or modified.

## ENV-002: Python startup warning

- The existing Python launcher emits `Failed to find real location of C:\Users\Lvi_P\miniforge3\python.exe`.
- The CLI still executes; retain command exit codes and JSON results separately from this warning.

## ENV-003: relative root resolves to a duplicate path component

- Actual policy CLI invocation with `--root .` failed with `FileNotFoundError`; the final directory name was duplicated.
- A bare Python command, without importing VibeLens, reproduced that `Path('.').resolve()` differs from `os.getcwd()` by the duplicated component.
- Classification: execution environment behavior; no VibeLens framework defect established.
- The documented absolute project-root invocation passes. No shared validator or example behavior was patched.
- Reproduction: `environment-relative-root-retest.json`.

## ENV-004: local design service unreachable from the first launch

- A session-backed launch printed a URL, but HTTP and the first IAB navigation timed out.
- A default-sandbox background launch also did not provide a reachable listener.
- The session-backed process was stopped. A host-approved hidden local process was launched with an absolute root and Python bytecode writes disabled.
- Retest: `/graph`, `/api/view`, and `/api/design` returned HTTP 200. The updated graph, Chinese interface, and design-only status were visible in IAB.
- Evidence: `design-server-host-process.json`, server logs, `design-web-checks.json`, and `design-round-02.png`.
- No network protection or shared source was modified.

## TOOL-001: atomic replacement patch rejected

- A patch that both deleted and re-added the same path in one operation was rejected before applying changes.
- The existing draft was frozen under `design-round-01/`, then the replacement was applied in separate filesystem operations.
- Retest: discovery and draft policy validation passed after the update.

## EVIDENCE-001: activation response envelope

- The review helper initially read `graph_url` from the response top level; the actual canonical response stores it under `result`.
- Fixed only the project review helper to read the documented returned envelope. The canonical CLI was unchanged.
- Retest: `design-web-checks.json` contains the actual scoped graph URL.

## Evidence provenance clarification

- A001 through A003 were authored questions in the initial discovery draft. They had not been separately delivered as chat questions before U002 arrived from the source conversation.
- The current discovery no longer marks those questions as awaiting answers. U002 resolves their business rules, and the original draft remains frozen as authored evidence.
- U002 is retained as the actual delegated user follow-up; it is not a simulated reply or implementation acceptance.
- Correction at stop: U002's forwarded text was actually received, but its business-user role was simulated by the coordinator AI. The preceding "not a simulated reply" statement is superseded by `PROVENANCE-CORRECTION.md`. It is not human acceptance or independent usability evidence.

## APP-001: undefined connection variable during sharing

- An application refactor left `FileService.share` calling `read_users(db)` with no local `db` variable.
- The real HTTP test returned 500 with `NameError`, failing the expected successful share.
- Repaired only the application reference to the actual `connection` variable. All four independent business scenarios then passed; see `business-retest-001.log`.

## GATE-001: discovery and contract authoring corrections before completed verification

- Canonical discovery decision links belong under `links`, and each link is an array. Initial authoring used top-level fields and PowerShell unrolled single-element arrays.
- Initial declaration preparation also needed the native `enum` state type and a nonempty legal graph before `begin`.
- These were project authoring errors, repaired before the completed gate. The baseline established by the first successful `begin` was preserved.
- The independent project virtual environment needed local Flask, SQLAlchemy, SQLGlot and JSON Schema dependencies. Initial sandbox `ensurepip` failed; project-local host installation succeeded without editing shared installations.

## OBS-001: canceled diagnostic after a source edit

- The first full observation diagnostic was interrupted after the model-generator source changed while it was running.
- That incomplete attempt is not acceptance evidence. A subsequent stable observed workflow captured 628 events with zero producer/data errors or loss; `probe-diagnostic-001.log` retains the actual result.

## FRAMEWORK-001: normal data completion rejected by strict invocation closure

- The complete gate passed its finite state/business/project checks, but mapping failed with 11 `invocation_without_exit` reports.
- Canonical data transactions emitted `enter → commit`, and transformations emitted `enter → change`. The shared closure audit ignored those terminal phases.
- A separate minimal reproduction using the canonical Skill confirmed the mismatch with a real SQLite commit and actual transform. Relevant copied files match canonical hashes.
- No example-local workaround, artificial return, alternate collector, removed data operation or weakened check was applied.
- The later verification was interrupted at the stop instruction. No accept command was run. See `ARCHIVE-BOUNDARY.md` for exact versions and evidence boundaries.
