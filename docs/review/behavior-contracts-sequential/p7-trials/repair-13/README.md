# P7 repair 13 — source checks during interactive capture

Status: focused, source, managed-example, full regression and fresh-installation gates passed. Native acceptance remains pending.

## Original failure

The ordinary Python drive recording `b967a911c5474f2b805e759d7793679c`
stopped with 546 events and four frames. Its producer had processed 621 of the
2020 envelopes in the stop prefix; 1415 messages remained pending. Seven
transport retries were reported, with no recorded transport errors or drops.
The missing frames and unfinished lifecycles prevent recording acceptance.
The error type behind those recovered retries was not reported.

`prior-python-recording.zip` preserves the original recording, independent SQL
and HTTP receipts, strict observations, screenshot, launcher, stop receipt and
test script. `prior-python-summary.json` records the trial's findings. The
business sources and protected checks were unchanged in that trial.
`prior-python-source.zip` and its SHA-256 inventory retain the matching source
and contracts; every manifest source hash was checked before archiving.

## Investigation

The detached load replays the first original strict `on` run: 1068 events and
34 matching snapshots. It executes no application business operation. Database
address identity changes when its SQLite copy moves, so the completed diagnostic
records both build IDs and replaces that field only in its derived input. These
derived events are not accepted native evidence.

`host-complete.json` uses the actual viewer, normal database watcher, remote
capture-control client and original HTTP timeouts. The source-reader thread pool
left 923 messages pending after stop and reported timeouts. `host-complete-serial.json`
changes only that reader to sequential execution in the diagnostic process:
all 1068 events and 34 frames arrived, and the stop prefix drained without loss.
`canonical-serial.json` repeats the same load with the maintained implementation,
without replacing the reader in the diagnostic. It also drains the complete prefix.
Timings include instrumentation and local machine load; they are comparisons,
not throughput guarantees.

The shared reader now performs the exact same containment and byte checks in the
caller thread. It no longer waits for four separately scheduled Python workers
while viewer and database threads are active. File contents, attributes and parent
links remain uncached. Same-size, same-timestamp edits are still detected. HTTP
timeouts, queue capacity, capture scope, event identities and strict source/state
validation are unchanged.

The existing source, remote HTTP, batch and capture-control regression reports
38 passing tests in `focused-first.log`. The Skill's mapping guidance now explicitly
requires normal application workers and the actual viewer during recording checks.

## Diagnostic limitations and retained setup failures

- `control-only.json` and `with-watch.json` were run inside the sandbox. The latter
  lacked the database URL; its watcher timings do not establish valid catalog
  refresh. They are not compared as successful native runs.
- `host-watch-browser.log` retains an incomplete detached setup whose relative
  provider path prevented its model exporter from loading.
- `host-watch-browser-ready.log` retains the next setup error: moving the database
  after constructing the session changed its build. The completed runner follows
  normal startup order and records the relocated build explicitly.
- A handle-based Windows reader prototype was rejected: its main-process timing
  did not improve on the current reader, and sandbox handle-path queries failed
  with access denied. No such implementation was added to the framework.
- `warm-watcher-profile.txt` profiles unchanged catalog refresh separately. No
  database collection or validation was disabled to make the test pass.

The runner and source/evidence inventory are retained alongside the gates. Actual
Python drive and Node observe recordings, all-layer Web/Timeline inspection,
business iteration, source-only refactoring and final product materials remain
required before P7 can close.

Complete regression: 1160 reported tests across 103 unittest reports, plus JavaScript and pinned TLC checks. Clean-export results are retained separately.
