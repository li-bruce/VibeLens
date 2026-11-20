# Repair 23: keep design metadata work out of initial capture

P7 remains in progress. This repair does not accept either trial or publish a
release. Python remains in drive mode; Node remains in observe mode.

## Failure and diagnosis

The original Python run returned HTTP 200 from ordinary Stop, but correctly kept
recording `bef6eebce72447579ebd8f2ab562147d` interrupted. The fixed producer target
was 3296 and completed was 3278. Pending was 34, including 16 submissions beyond
the target. Dropped was zero. A transport TimeoutError was already present at
recording start. See [the preserved failure](native-failure.json).

Read-only checks were fast in isolation. In the copied native workload, a cold
`/api/design` read overlapped event admission. This optional metadata request
assessed the complete design while short transport requests were active. An
unprofiled source-binding call took 918 ms, exceeding the producer's 500 ms
single-attempt timeout. The retry recovered in that diagnostic run; this is not
a claim that every run fails or that all latency comes from one function.

The original recording, data, source and preferences were retained before
stopping its services. Diagnostic setup failures were also retained. The
[diagnostic index](diagnostics.json) identifies each copy, archive and boundary.
The copied database has a different physical identity: transport diagnostics
therefore pin the original verified graph, without claiming database discovery
acceptance. v4 used additional profiling and is not a timing comparison.
The unmodified browser harness has hardcoded descriptions of its ordinary
launcher. Inside these diagnostic copies, the wrapper and diagnostic index
describe the actual entry point and timing hooks; those raw report descriptions
are not evidence of an uninstrumented normal-entry run.

## Change

- Prepare valid optional design metadata before opening the capture listener
  and before publishing a reloaded session.
  An invalid optional draft still returns its original error on request and does
  not disable a valid loaded runtime build.
- Read current discovery bytes on each metadata poll, while reusing its validated
  digest. Full document callers still receive detached copies. Changed bytes,
  including same-size/same-time edits, undergo the unchanged strict validation.
- An explicit supported URL language no longer requests design metadata just to
  choose that same language. Conversation-language fallback remains available.

Queue capacity, socket/flush deadlines, event fields, model semantics, native
assertions and source admission checks are unchanged. The Skill reference now
explains the metadata preparation boundary and distinguishes timeout diagnosis
from queue overflow.

## Verification

The new assertions fail against the prior immutable provider and pass against
the fix: [counterexamples](counterexamples.json). Existing drift, concurrency,
focus and language checks remain. The initial formatting check failed; its log
is retained and the formatted source recheck passed.

In the fixed isolated workload, all original assertions passed, with 3114 events,
24 exact state frames and no recording gap. The fixed target of 3148 completed;
eight newer submissions did not move that target. Metadata reads took 2–12 ms in
this run. Timers add overhead, and these figures are not a throughput guarantee.
Normal installed-provider upgrade and native acceptance still follow the full
regression gate. See `diagnostic-v5.zip` for exact calls and case results.

The initial fix missed session replacement after a source edit. A separate
counterexample found zero assessments before publishing that new session and
one on its first metadata request (`reload-before.log`). Startup and replacement
now share the preparation function. The regression verifies one assessment
before publication and no repeat on that first request. The intermediate full
gate was deliberately interrupted for this correction; its log and process-tree
receipt are retained. Only the final complete rerun can qualify this repair.

## Completed repair gates

Final complete regression passed: 1304 reported tests across 116 unittest reports, including repeated suites. Source checks, both managed examples, seven metadata regressions through the fresh installed provider, and the clean staged export passed. See [results](results.json). These gates do not replace the remaining native trial acceptance.
