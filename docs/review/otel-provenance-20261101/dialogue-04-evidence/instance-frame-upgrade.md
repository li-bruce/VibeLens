# Managed instance-frame and API-layer repair

The canonical runtime and viewer were upgraded in `.stategraph/instance-frame-identity`. The shared implementation now retains run-qualified `snapshot_instance` and `native_instance_id` on machine configurations. Runtime comparisons join the same witnessed instance and retain prior configurations across instance-local frames. Explicit `layer: api` declarations are honored by both the frontend and the backend.

## Scope and preservation

The conflict-free managed upgrades changed only these canonical files:

- `observer_runtime/bo_observer/observation/session.py`
- `static/graph/runtime-frames.js`
- `static/graph/replay-steps.js`
- `observer_runtime/bo_observer/workflow/observation_requirements.py`
- `static/graph/graph-layers.js`

Application source, native executor, state and policy declarations, independent assertions, and API node declarations were preserved. Revocation removes sharing authorization only; administrators retain their independent original access. The current human confirmation is retained in `admin-rule-confirmation.json`.

`pre-instance-frame-repair/frozen-inputs.json` freezes 55 files, including business sources, current personal preferences, and all four prior accepted change directories. It also records all 244 model node identities. Old service logs and its stop request are preserved alongside it. The two managed upgrade plans, apply results, and automatic upgrade backups retain copy provenance. `instance-frame-integrity.json` records the latest integrity checkpoint and managed registry comparison.

## Added independent checks

The frame regression executes actual HTTP upload, approval, sharing, and revocation, followed by a later file approval under the same `application` attempt. It compares final configurations with SQLite, each frame with native state/journal facts, and actual JavaScript replay output with six same-instance state changes. Three native instances remain distinct. No revoked Share state becomes a File state.

The API regression checks the existing `api_get`, `api_post`, `api_command`, `api_file_info`, and `api_workspace` declarations using both installed classifiers. Each must remain in the API layer.

Focused test development logs are retained as `instance-frame-focused-test-01.log` through `-05.log`. Early checks incorrectly expected a saved-event metadata field, a journal row for initial file insertion, and raw recording events to already be viewer timeline items; the test was corrected to use the public frame contract, independent initial SQLite reads, and the canonical timeline adapter. The Node argument indexing was also corrected. These were project test-harness errors; no canonical implementation or prior checks were weakened.

## Verification and live handoff

The normal `tooling/verify.py` entrypoint runs all 16 existing scenarios in on/off/fault modes and the full project test suite, then performs canonical verify, accept, and check. Final gate results, test counts, loaded build identity, new process identity, and fresh URLs are recorded in `instance-frame-acceptance-summary.json` after completion. The independent parent chat performs real browser, timeline, 2D, and 3D acceptance.
