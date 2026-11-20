# P7 repair 12 — bounded transport recovery

Status: focused, source, managed-example, full regression and fresh-installation gates passed. Native acceptance remains pending.

## Preserved failure

Python drive completed its business operations and passed strict snapshot checks,
but its ordinary recording `9f0a0176b54545d28677b582b6e8b39e` was interrupted.
It retained 949 events and 12 frames. At stop, the producer reported target 1832,
completed 1048, pending 800 and two errors. The previous aggregate health omitted
the producer error type, so the precise cause of those two errors is unknown.

`prior-python-recording.zip` preserves the original recording, native SQL receipts,
closure checks, browser screenshot, actual launch/stop receipts, test script and
strict observation evidence. `prior-python-source.zip` and its hash inventory
preserve the project sources independently of the maintained Skill.

## Diagnosis and change

Detached replay uses original envelopes and a copied project; it does not execute
business code and is not dialogue acceptance. The first diagnostic used the wrong
snapshot key (`event_id` instead of `evidence_id`) and consequently had events only
(`baseline-active.json`, zero snapshots). That limited result is retained. The corrected diagnostic
includes all 1068 events and 34 frames (`baseline-frames.json`). With ongoing view
reads, it accumulated 317 pending envelopes before stop and settled in 2.28 seconds.
This establishes load sensitivity, not the cause of every native failure.

An independent HTTP fault test reproduces a concrete amplification problem:
after a batch was committed and its connection closed before the response, the
Python SDK immediately sent more than thirty individual requests. Each request
repeated strict admission and source checks. `retry-request-count-first.log`
preserves that failure. Node already retried requests with the same IDs.

Python now retries an ambiguous transport once using the exact original request.
Explicit HTTP rejection is not retried by this helper. Batch rejection still
falls back to individual validation. Socket deadlines, queue limits, snapshot
ordering, source-byte checks and acceptance rules are unchanged. Both SDKs expose
the retry count. The capture bridge preserves each producer's bounded error type
and counters without publishing exception messages or captured values.

The snapshot-response test confirms that retrying a committed frame preserves
its evidence ID and revision without creating a second frame. Existing malformed
batch, legacy fallback, source drift, authorization and queue tests remain active.

## Verification

- `focused-final.log`: 30 tests passed, including real Python and Node HTTP traffic.
- `health-first.log`: missing producer diagnostics reproduced before the repair.
- `binding-profile.txt`, `admission-profile.txt`, `display-profile.txt`: detached
  profiling; instrumented timings are diagnostic measurements, not a throughput SLA.
- Full regression, managed-example verification, clean export and fresh installation
  are recorded separately when complete.

The first Node dependency-install command stopped before npm ran because its
relative output path pointed outside the evidence directory. The corrected run
used the absolute output path, the same lockfile and disabled lifecycle scripts;
its exit status and output are in `installed-node-dependencies.*`.

P7 remains open. Native recording, every graph layer and Timeline, business
iteration, source-only refactoring and the final dialogue review are still required.

Complete regression: 1160 reported tests across 103 unittest reports, plus JavaScript and pinned TLC checks. Clean-export results are retained separately.
