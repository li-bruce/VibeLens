# Repair 25 — recording settlement under live viewer load

The Python source-refactor trial failed its ordinary recording after repair 24.
Native HTTP behavior and all 24 admitted state frames were correct, but Stop
returned `interrupted`: the fixed producer target was 3814 envelopes and the last
reported completed count was 3624. This was a capture failure, not an accepted run.

The collector had received 64 envelopes beyond that completed count. The final
two invocation exits later appeared in the live log, outside the closed record.
Consequently, neither missing instrumentation nor “all pending events were never
sent” describes the evidence. The original recording and its local 83-file freeze
remain unchanged. [Diagnosis evidence](diagnosis.json) records their identity.

## Findings and changes

- An ambiguous group receipt already retried once. A second failure immediately
  issued separate requests for every original event, multiplying strict source
  checks. Python and JavaScript now recover in ordered halves down to individual
  envelopes. Identities, receipt checks, snapshot barriers, capacities and socket
  deadlines remain intact. Permanent failures still appear in producer health.
- Semantic captions were validated and the whole model copied again on each
  poll. Validated names now use an eight-entry cache keyed by exact file bytes;
  readers receive detached values. Same-size, same-time edits and deletions are
  still detected. The session applies names to its already detached model.
- Project and API views independently traversed the same source tree. They now
  share one fresh source inspection within a request, with separate projection
  caches. Subsequent requests still inspect actual files. This does not enable
  the optional persisted AST cache or remove source admission checks.
- While Stop drained its fixed prefix, display polls and periodic recording
  copies/writes competed with admission. Display readers now yield during that
  bounded drain, and the final checkpoint replaces redundant periodic saves.
  Event listeners, admission and internal runtime reads continue. Readers are
  released on either success or failure, and an unsuccessful drain remains an
  interrupted recording with a visible gap.

The new tests first reproduced duplicate source scanning, repeated caption
validation and singleton fan-out after two lost receipts. They also exercise
source edits, detached names, real HTTP recovery in both languages, and admission
while display work waits. Existing invalid-batch, stale-source, snapshot-order,
legacy-collector and failed-receipt checks remain enabled.

## Evidence boundary

Timed diagnostic copies v7, v8 and v9 still failed. The v10 copy passed every
original recording check: 3698 events, 24 frames, fixed target/completed 3744.
Its 12 later pending envelopes were outside the fixed target. All copies retain
their original assertions and deadlines; none repairs the original failed record.
Timing wrappers add overhead, and the earlier trial services were stopped before
v10. These runs identify behavior and are not a controlled performance benchmark
or installed-project acceptance.

The complete repository regression now passes, including both languages, native
HTTP and database behavior, installation and independently executable business
core packages. Shared regression, fresh installation and renewed native/UI trial
receipts are tracked separately. P7 remains in progress until installed native
trials, Node iterations and product-scene work finish.

## Regression found during the repair

The first complete repository run failed the unchanged Node OpenTelemetry check
in `tools/test_telemetry_node.mjs`. Calling the new asynchronous group helper for
a single local envelope introduced an extra scheduling turn. The fix keeps the
original direct delivery path for single envelopes and snapshot barriers; ordered
group recovery applies only to batches. The original assertion then passed, as
did 32 related compatibility checks. `full.log` preserves the first failed run;
`final/` contains the subsequent whole-repository checks.

The next complete run reached the concept-control HTTP test and exposed an
outdated fixture: it replaced the two former source services, while the session
now asks for one shared `structure_context`. The fixture now replaces that
source-inspection boundary directly. Its session, HTTP transport, selection,
concept identity and no-runtime-history assertions are unchanged. All 18 concept
capture and API snapshot tests passed afterwards. `final/full.log` retains this
failure; `final/full-retest.log` is the subsequent complete run.

The first installation receipt is retained as an intermediate candidate. The
final candidate lives in `capture-settlement-skills/vibelens`; its receipt in
`final/installation-final.json` compares 464 maintained files byte-for-byte.
Native project acceptance follows separately after that installed provider is
bound through the managed upgrade workflow.

One dependency-install command failed before execution because its relative log
path did not exist. The corrected command used an absolute log path and exited
zero; see `final/dependency-install.log` and `final/dependency-install.exit`.
The shell's initial zero status did not establish that installation had run.

## Completed shared gates

[Regression receipts](regression.json) index the failed runs and final pass:
116 unittest reports, 1309 reported test executions (including repeated suites),
and the existing Windows symlink-creation skip. Source checks cover 248 Python
and 143 JavaScript modules. Both frozen examples passed
[clean Git export checks](final/clean-export.json) without regeneration or renewed
approval inside the export. Installed-project and desktop acceptance remain open.
