# Reproduction evidence and explicit stop

Status on 2026-11-01: stopped at the human-requested reproduction/fix-evidence phase. No `accept` was executed, no accepted receipt exists, and no new baseline was accepted. Application delivery and full runtime acceptance are deferred to the requested new conversation against the stable shared version.

## HTTP 500

The original reproduction used the real Flask review route and a disposable SQLite database whose notification table was made unavailable. Flask returned 500, its native exception signal reported `OperationalError`, and the review transaction rolled back to `pending`. The original graph's HTTP completion and business exception outputs were empty.

- `http500-before.json`: original native status, exception signal, rollback read and raw events.
- `http500-before.stderr.log`: original native exception log.
- `before-audit/`: source snapshots saved before the integration revision.
- `before-source-check.json`: saved source hashes match the original reproduction's source hashes.

The first run retained the actual status, but did not archive its response body/headers. They have not been reconstructed. The final focused run below preserves the complete new native response, including actual headers and body.

The application then adopted upstream `opentelemetry-instrumentation-flask` 0.66b2 on the application-owned tracer provider. Route/method selectors are available at span start; the framework instrumentation obtains the actual status through its WSGI `start_response` boundary. The inner dispatch span and guessed status assignment were removed.

- `http500-final-focused.json`: native 500 response, native exception signal, unchanged pending state/revision, empty transition journal, original events, selected independent SDK span facts, and actual capture health. All five focused assertions passed, with zero capture errors and drops.
- `source-audit-after.json`: separately retained earlier focused results after upstream Flask integration.
- `final-focused.stderr.log`: actual unhandled-exception log for the final focused run.

Classification: the HTTP response boundary was an application integration issue. The exception type is currently visible through an explicitly allowlisted project `outputs.error` field. This is separate from a shared, uniform exception-trace-fact interface. The shared exception-fact gap remains for the main conversation to repair. These focused results do not establish stable shared-SDK acceptance.

## Sign-out timing

At receipt of the source-review concern, session clearing had already been moved into the application's sign-out interval. No pre-fix logout runtime failure was claimed.

`logout-final-focused.json` records a direct native Flask-session read at each actual producer `record` call. Entry still has authenticated `member1`; return has no authenticated principal after the native `session.clear`. Captured provenance matches both reads. The initiating user's ID remains in selected input `actor_id`; the remaining principal ID is read back from the native session-clearing callback and captured separately. The test no longer fills null merely from the scenario name or a later final session. All five focused assertions passed, with zero capture errors and drops.

## Observation isolation

`bo_principal` and `bo_identity` now live in the isolated `app/ports.py` observation interface. Business source calls the explicit `self.bo` port. Native policy evaluation and declaration-driven state execution retain their own authority.

The queued tracing field is explicitly named `bo_carrier`. Serialization and parsing belong to `BOHooks`; disabled observation uses the quiet port. `schema-migration-job-check.json` independently compares the full selected native job rows before and after the real SQLite column migration. They are equal. `observation-isolation-check.json` retains six passing source/isolation checks and this migration evidence.

## Integrity and remaining work

- `stop-integrity.json`: original baseline ID `8b10c0b17818ef97bc322a596f5440bf634fa105df6b6202021897e0d96faa76`, its current file digest, no accepted receipt, and no modified managed runtime/viewer/core files.
- `evidence-checkpoint/source/`: complete current source/declaration set plus the unchanged copied canonical runtime used by the final focused audit.
- `evidence-checkpoint/source-hashes.json`: checkpoint file hashes and the focused build identity. This is evidence, not an accepted build.
- Earlier original business assertions passed. The last extended test run passed concurrency, non-owner administrator denial, job migration and source-drift detection. Its semantic mutation case failed during isolated fixture setup because a parent directory was missing; it did not establish mutation sensitivity. This failure is left unresolved under the stop instruction.
- Full on/off/fault verification, recording/replay, browser acceptance, `change_sync verify/accept/check`, and final application delivery have not been completed. No missing or unrun item is a pass.

The maintained repository and copied shared SDK/validators/projectors were not patched. Further shared-interface work and fresh stable-version testing belong to the main conversation and a new independent trial, as requested.
