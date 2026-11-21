# Initial check failures retained

## New protocol regression: error-message expectation

The first `tests/test_protocol_reuse.py` run executed five tests: four passed and
one failed. The failing case was
`test_next_batch_reads_current_capture_and_observer_declarations`.
This excerpt is transcribed from that command's tool output; it is not a rerun log:

```text
ValueError: unapproved type or value length
AssertionError: "capture" does not match "unapproved type or value length"
Ran 5 tests in 1.324s
FAILED (failures=1)
```

Changing the field from string to boolean was already rejected. Only the test's
expected message changed to the existing type validator's message. The separate
unknown-field, observer-exclusion, identity, bounds and source-change assertions
remain. The raw subsequent result is in
[the focused protocol log](checks/targeted/test_protocol_reuse.log).

## First full repository gate: stale shipped copy

The first complete gate reached package parity and stopped with:

```text
AssertionError: Runtime copy is stale: protocol.py
```

Its complete output and nonzero receipt are in
[the initial full log](checks/full/full.log) and
[receipt](checks/full/result.json). The existing `tools/sync_runtime.py` refreshed
the delivery/team-archive runtime copies and their manifests. Trial installs,
native data and recorded facts were not changed by that operation.

The second full gate passed copy parity and later stopped in the clarification
integration fixture. Its architecture guard identified three changed managed
files: `protocol.py`, `observation/event_batch.py`, and `runtime-version.json`.
The synchronization tool intentionally does not approve a regenerated runtime.
The explicit example-review workflow compares every configured business source
byte-for-byte with HEAD, checks the changed artifact scope, records the reviewed
regeneration and then runs `verify`, `accept`, and `check`. The test and architecture
assertions remain unchanged. The failed full run is retained in
[the post-sync log](checks/full-after-sync/full.log).

## Detached profiling setup

The first profile used a directory already occupied by a previous diagnostic and
refused to overwrite it. A subsequent attempt fed a persisted recording envelope
to producer protocol validation; observer-added `source_seq` and `stream_id` are
not producer fields and strict validation rejected them. The corrected profiler
reads original producer envelopes from `review/runtime/native-runs.json` instead.
No recorded envelope was edited to make it pass. These setup failures are not
native capture failures or measurements of collector throughput.

## Native negative-gate fixture

The first read-only comparison expected both failed ordinary receipts to contain
their interrupted recording in the ordinary `recordings` array. The earlier GUI
exception stored its cleanup recording separately; its ordinary array has only
one completed item. The existing gate correctly rejects that missing second
recording. The corrected fixture checks that exact rejection for the earlier
epoch, and the explicit interrupted-recording rejection for the later epoch.
The gate itself was unchanged. Both command failures remain required failures in
[the final negative-gate check](native-negative-gates.json).
