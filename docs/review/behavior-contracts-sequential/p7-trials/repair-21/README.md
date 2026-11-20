# Repair 21: source clocks and Timeline durations

P7 remains in progress. This repair follows the Node trial's actual browser
failure after repair 20; native business verification is a separate result.

## Failure and cause

The new recording opened successfully, so the API identity repair held. Timeline
then displayed all 1257 projected lifecycles without measured durations. Its
time-axis check treated the merged collector stream as one producer clock.

The unchanged recording contains 6044 facts from two producers. Both source
clocks advance normally; 24 delivery inversions occur when browser and server
batches interleave. There are no invalid timestamps. The original recording SHA256
is `d56a22aa789a26dccde3b6cb6d45ac95c6087f84cdb4f788cd0da6c0a46b1f9c`.
The original failed desktop run, screenshots, exact test scripts and diagnosis
are retained in `first-native-timeline-failure.zip` with a member manifest.
`clock-before.log` preserves the failing regression before implementation.

## Change

- A dedicated `trace-clock.js` validates each build/run/producer clock. Collector
  stream, business object and attempt identity do not manufacture separate clocks.
- Replay preserves original event ordinals and IDs. Timeline uses reported source
  timestamps and a separate sorted index for time-window queries.
- Time-range loops retain exact selected IDs in delivery order. The independent
  `time-range-before.log` counterexample shows why two ordinal endpoints alone
  select the wrong events after interleaved delivery. Explicit skips still apply;
  manual endpoint edits restore the ordinary contiguous delivery-range behavior.
- Real source-clock reversal, invalid timestamps, and disorder with missing
  producer identity keep the existing event-order fallback.
- Timeline explains late delivery in its clock note. Multiple-producer clocks
  remain disclosed. This change neither synchronizes clocks nor invents causal links.
- The native UI test now reports missing numeric durations clearly and explicitly
  requires a time axis; the original positive business-duration requirement remains.

VibeLens `observed_at` is emitted at the producer. Collector sequence records
delivery order. These are distinct observations, consistent with the separation
of event and observation time in the [OpenTelemetry logs data model](https://opentelemetry.io/docs/specs/otel/logs/data-model/).

## Evidence boundaries

`native-clock-retest.json` indexes the original recording without modifying its
bytes or ordering. Its base model has 1165 indexed lifecycle slices, including
44 positive business intervals. That count differs from the full UI's projected
inventory; this is an indexing regression, not completed browser acceptance.

Two qualified Node concept aliases still contain raw IDs (`policy-operation:login`
and `policy-operation:logout`). They require a normal metadata correction before
the next recording; they are not a reason to change renderer language precedence.

The Node trial also restored personal preferences after its first audit. Preserve
the original revision 50 to 54 diff and subsequent restoration to 55 as separate
evidence. Post-restoration equality does not prove automatic preference retention.

Native recording files and databases remain in the isolated trial directory.
Do not publish its raw archive, which contains local collector configuration.
Fresh installation, native recapture, complete desktop checks and remaining
semantic/refactoring iterations are still required for P7 acceptance.

## Completed repair gates

Full regression passed with 1296 reported tests across 116 unittest reports and 1 existing skip(s); totals include repeated suites. Final source checks, installed clock/selection counterexamples, unchanged native-record indexing, desktop Timeline controls, both managed examples and clean staged export passed. The 464 owned installation files match the final source. The 20,000-event component load passed on this host; it excludes whole-graph reconstruction. First-pass and final-pass receipts remain separate. See `results.json`. P7 native acceptance is still pending.
