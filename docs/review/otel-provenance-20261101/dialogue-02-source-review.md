# Dialogue 02 source review

Status: preliminary source findings sent before initial delivery; runtime
confirmation and application repair are pending. These are not reported as
shared-runtime failures.

Update: the trial preserved an actual HTTP 500 and rollback reproduction. The
response-boundary defect was repaired through upstream Flask instrumentation.
The observer's default physical exception field was then repaired centrally.
Logout had already been adjusted during development before the review message;
no pre-fix runtime failure is claimed. Its direct native boundary audit passed.
Observation helpers and the carrier column were isolated and checked. The trial
stopped without accepting a baseline; see [its retained report](dialogue-02-evidence/REPRODUCTION-AND-STOP.md).

1. `TeamService.sign_out` selects an absent actor on completion, but the calling
   HTTP dispatcher clears the native session only after this function returns.
   The scenario oracle independently names the case, but hardcodes null from its
   eventual meaning instead of witnessing authentication at the selected boundary.
   Preserve the executing caller or move the relevant native boundary; compare
   native facts at that time rather than merely comparing final snapshots.
2. Observation-only identity formatters remain mixed into the business service
   without the `bo_`/`BO` naming. The internal queue column `carrier` also lacks
   an observer identifier. Review isolation and reader-visible ownership.
3. A custom request span surrounds dispatcher execution. An unhandled exception
   can end that span before Flask creates its real HTTP 500 response. The shared
   SDK regression now verifies actual upstream Flask 500 instrumentation, but
   the application integration needs its own real-entrypoint check.

The trial is allowed to fix its own integration and business code. Canonical
state/protocol validation remains read-only. The later ordinary business iteration
will be sent without graph/probe maintenance instructions; this source-review
feedback is part of initial acceptance, not evidence of automatic iteration recall.
