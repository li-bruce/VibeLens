# Keep display work separate from observation admission

Status: implemented; focused, database, source, managed-example and complete
regression and clean-export checks passed. Native recording acceptance remains
failed; this does not close P7.

## Reproduced problems

- `static-view-first.log`: deliberately hold a static declaration copy. Incoming
  native probe work cannot drain while `recording_version_context` holds the
  session lock. Fourteen existing settlement checks passed and the new case failed.
- `watch-validation-first.log`: two unchanged database watch ticks execute full
  project validation twice. Actual metadata collection must continue, but this
  repeated pure work is unnecessary.
- `component-profile.json` and `project-profile.log`: a read-only profile of the
  570-node, 1,562-edge Node project identifies repeated project validation and
  source reads as work to investigate. Profiling overhead and concurrent work
  prevent treating these timings as a throughput benchmark or proof of every
  native receipt timeout.

## Changes

`observation/session.py` copies the build's static model and conceptual context
outside the runtime event lock. SessionHost pins that immutable build while the
request runs. Mutable event cursors, state snapshots and binding checks retain
their existing synchronization and validation.

`data/projection_validation.py` owns a one-entry memo for one watcher. Only an
identical JSON value that passed all original graph/data/project checks can reuse
validation. Non-JSON coercions, failed candidates and changed definitions cannot
reuse it. Every tick still reads sources, collects actual catalogs, compares
declared and actual structures and runs the existing reload logic. Independent
checks and forced synchronization always execute the original validators.

SDK deadlines, retries, event identities, capture obligations and recording gap
checks are unchanged. A focused pass does not establish native recording success.

## Tests and retained failure

The seven new tests cover a blocked static copy in both live and recording views,
fresh database collection, same-size/same-time invalid edits, schema replacement,
independent checks and JSON type safety. The first retest exposed an unclosed
SQLite connection in the new test fixture on Windows; `focused-first-retest.log`
is retained. The fixture now explicitly closes its connection.

`focused.log` records 84 passing new and existing tests. `source.json` records
format/source checks. `database.log` records 94 passing tests across nine Python
suites, the JavaScript database/causal checks and the database-choice dialogue
fixture. This run covers the local adapters; it is not a new external-server or
Docker integration claim. Both managed examples passed verification, acceptance
and their current-source checks; the native application source is unchanged.
Their existing receipts were frozen as `behavior-contracts-p7-repair09-20261120`.
Native Python and Node recording evidence is evaluated separately.

The fresh diagnostic installation contains 455 maintained files matching the
candidate byte-for-byte. Its first hydration attempt lacked the configured
offline dependency cache and failed; `diagnostic-install.log` retains that result.
`diagnostic-install-retest.log` records the normal installer succeeding with the
verified cache. No installed source was edited. The installation receipt is a
diagnostic package identity, not a native acceptance result.

## Native retest remains failed

`native-repair09-failures.json` indexes the unchanged recordings, native database
comparisons and timing files in its ZIP archive. Python retained 79 events and
matched none of eight actual journal transitions before its failed stop boundary.
Its aggregate error count alone does not identify the transport exception or
server stage. Node drained the entire 1,145-item prefix and retained 1,104 events,
but one delivery exhausted both attempts; capture health correctly kept the
recording interrupted. These outcomes do not close native recording acceptance.

The Node timing log confirms that the database watcher performed full project
validation once, rather than every tick. Remaining receipt delay requires further
measurement of source reads and display/data work; successful memo reuse does not
establish that the overall ingestion bottleneck has been solved.

The first full regression (`full-verify-retest.log`) stopped at the existing
invalid/oversized HTTP-batch case: Windows aborted the connection before the
client received the expected 400 response. The unchanged seven-test HTTP suite
passed when run separately (`remote-http-retest.log`). No assertion, size limit
or transport timeout was relaxed. A subsequent full run is required; this one
successful focused rerun does not identify the cause of the connection abort.

`full-verify-second.log` records the complete subsequent runner: exit 0,
99 Python unittest reports containing 1,126 reported tests and one skip, plus
JavaScript checks and the pinned TLC/Java integration. No assertion or transport
deadline changed between those two runs. The first Windows abort remains an
unresolved intermittent result, rather than a claimed repaired cause.

`node-attribution/` preserves the later read-only correlation against the original
archive. Sequence 34 reached the server exactly once, but both client attempts
expired before their responses. The first binding call lasted about 1,446 ms;
the retry spent about 1,489 ms before binding. The overlapping database tick was
not executing full project validation. These measurements identify intervals,
not a unique lock owner or a proven operating-system cause.

`python-timed09-failure.json` indexes a separate authorized diagnostic using the
same installed candidate. The recording contains 1,006 events and 12 frames;
all eight native journal transitions match. It still fails: its submitted prefix
did not drain, and four read events have no frame. The timers captured three
0.5-second batch timeouts followed by successful single-event fallback. Four
snapshot requests returned HTTP 200 with `accepted=false`, which the single-item
transport currently ignores. Receipt validation and same-version read semantics
therefore require their own repair. A zero producer error counter in this run is
not evidence that every snapshot was accepted. The original failed recording,
raw timings, diagnostic source and source/native comparisons are archived intact.
