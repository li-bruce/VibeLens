# Point-observation ownership

## Reproduction

Trial 06's immutable `actual-recording-recovered.json` and
`failure-timeline-timeline.json` show an HTTP concurrency peak of four and nine
Timeline bands (63 rows over seven selected layers). Of 114 indexed executions,
103 start at actual `http_request` entries. Eleven are fallback observation
streams: ten start at `policy:logged_in`, one at `authorize_file`. Several fallback
streams span unrelated requests on the same file. These are execution-group spans,
not witnessed function lifetimes. The earlier commentary used an imprecise
description of the interval; preserve this distinction in the final report.

Actual data calls inherit their outer context correctly. Ordinary `probe.record`
points do not. `policy.record_evaluation` deliberately supplies file entity/attempt
identities; these must not be replaced with the outer request's identity.

## Repair direction

1. Add an optional strict `parent_event_id` to the common JSON event envelope. It
   identifies the actual enclosing invocation entry, distinct from file/entity
   identity. Do not overload data dependencies or merge by timestamp/node label.
2. Python/Node `record` should inherit the current same-probe call context by
   default, retain explicit identities and allow explicit null parent suppression.
   Span completions must retain their original parent and never parent themselves.
3. Native data-adapter adoption must retain its own actual entry ID so points
   inside callbacks/transactions attach to that native call. Preserve exact native
   results, exceptions, disabled/fault behavior and observer exclusion.
4. Strict complete-run checks must validate explicit parent entry references,
   target call ID and current build. Clipped recordings may use original context
   entries. Cross-entity ownership is permitted only through the explicit entry
   reference; old scoped call-ID resolution remains unchanged.
5. Graph and Timeline resolve those same explicit references, including context
   boundaries. A point fact with no registered start is not a function invocation.
   Unowned fallback observations must not fabricate a long-running request from
   many point facts; unknown ownership remains visible as unknown.
6. Replay the unchanged failed recording to document the old gap. Do not add new
   parent IDs to historical facts. Verify the repaired context on fresh actual
   Python/Node runs, including policy points with explicit file identities and
   concurrent requests. Timeline bands must match actual invocation concurrency.
7. Preserve source-first native-entrypoint guard regressions already implemented,
   synchronize/freeze the next managed checkpoint, run complete checks, then start
   another new chat. The trial 06 application/UX evidence is stopped before accept.

Implementation details remain subject to schema and existing lifecycle tests.

## Clarification after the user's ownership question

The old recording is frozen failed evidence, not a valid category of unexplained
application facts. Its node/field declarations were present; runtime invocation
ownership was omitted by ordinary record/policy capture and not required by the
earlier gate. This is a shared implementation and verification gap.

Use the existing protected `require_observation_closure` gate to require ownership
of internal points; do not add an optional switch that could be forgotten. Native
entry events establish roots. A genuine source-bound external point notification
may declare `observation_root` on its existing node. Unowned internal points fail
mapping independently of correct business responses, values and closed calls.
Wrong references and locally closed parents also fail. The viewer keeps unknown
old evidence separate without converting it to long-lived executions. None of
these changes repairs or rewrites the old facts.
