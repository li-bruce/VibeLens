# Remote event backlog

The Node application's actual recordings remained interrupted after repair 06.
One transport request carried one event, so every queued fact repeated the
complete current-source binding check. A separate read-only measurement of the
real trial model took 1.20 seconds for 30 checks. Profiled trial times also
include instrumentation and concurrent workstation load; they are diagnostic
evidence, not an isolated performance benchmark.

The existing local `BOSessionSink` already validates bounded event groups before
publishing them, with current-source checks at both boundaries. This repair
exposes that reducer through an optional HTTP transport wrapper. Python and
JavaScript group only already queued events, preserve each original ID and
receipt, and keep snapshots in their original order. Limits remain 64 events
and 24 KiB per request. The producer's existing deadlines and queue limits stay
in place. A flush prefix excludes subsequent work from its last atomic group.

Old collectors fall back to original single-event requests. Rejected batches
and ambiguous receipts retry originals; the existing identity checks deduplicate
accepted facts and retain individual errors. Native business execution, state
authority, field selection and the recording completeness gate are unchanged.

## Failure and retest evidence

- `remote-first.log` records an incorrect test-harness assumption about the
  server factory return value. The fixture was corrected.
- `remote-reproduction.log` includes an incorrect JavaScript constructor call;
  `remote-reproduction-corrected.log` retains the actual missing endpoint and
  absent batching failures for both SDKs.
- `remote-retest.log` preserves a Windows connection reset when an unauthorized
  request was rejected before its large body was consumed. The authorization
  case uses an empty body to check the same mandatory token boundary reliably.
- `remote-complete.log` runs seven real HTTP tests covering atomic rejection,
  duplicate receipts, both producer backlogs, snapshot ordering, legacy
  fallback, ambiguous replies, strict shapes/source freshness and flush-prefix
  completion while later traffic is blocked.
- `focused.log` and `capture.log` retain the related existing regressions.
- `diagnostic-installation.json` identifies the component-tested package sent
  to the native trial. This is not a final acceptance receipt.

The complete host regression and managed example reviews passed. The sandbox
attempt stopped at Windows realpath permissions; its unchanged assertions passed
in the host rerun. The clean-export result is tracked in `results.json`.

The native candidate captured one complete 816-event recording with no gaps.
Its second recording was interrupted at stop with 148 queued items. The original
recordings and transport audit are retained in `native-candidate-capture.zip`,
with hashes and interpretation in `native-candidate-capture.json`. This is a
component repair, not a completed native acceptance. P7 retains recording
diagnostics, all desktop views, business iterations, source-only refactors and
evidence-backed product scenes.
