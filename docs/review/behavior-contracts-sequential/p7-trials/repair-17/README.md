# Viewer module connection reuse

P7 remains in progress. This repair addresses local viewer startup; it does not
replace the outstanding business iterations, source refactors or final native runs.

## Failure and diagnosis

The fresh repair 16 Python application recorded 2,506 real events, 24 state frames,
12 commits and 12 reads. All 508 observed calls closed, and the fixed stop prefix
settled at 2,616/2,616 without gaps. Original native assertions and reports are in
`python-native-effect16.zip` with a SHA-256/member index of the same basename.

Independent browser startup then failed. The first page remained at Connecting;
a second instrumented run reached two locale transitions before failing. Chrome
reported `ERR_CONNECTION_TIMED_OUT` for `/trace-lifecycles.js`; no graph JavaScript
was initialized in the failed document. A separate successful startup was retained
as a diagnostic, not treated as a repair.

`local-connect-diagnostic.json` preserves the failed localhost request and its
connection dependencies from Chrome NetLog. The failure occurred while connecting
to `127.0.0.1:8876`, before an HTTP response. The original server closed every asset
response, forcing another TCP connection for each nested module import. This
evidence establishes connection churn and the failed connect; it does not identify
an operating-system or browser defect as the underlying cause.

## Repair and checks

`web/http_assets.py` is shared by the design and runtime HTTP handlers. Successful,
bodyless HTTP/1.1 asset GETs can reuse one connection with a five-second idle limit.
HTTP/1.0, explicit close, body-bearing GETs, JSON, controls, ingestion and errors
keep closing connections. Existing authorization and unread-body rejection checks
remain in place. Recording and settlement timeouts are unchanged.

- `transport-before.log` fails the new same-socket assertion on the old handler.
- `transport-expanded.log` passes the 120-import chain, real design server,
  client-close/body isolation and original cold connection-burst tests.
- `focused.log` retains a test-runner mistake: a nonexistent test module was
  selected. `focused-retest.log` reruns the three actual suites, including all
  original event-batch and rejected-body checks.
- `source-first.log` retains the initial successful formatter/linter output; the
  rerun supplies its structured receipt through the tool's actual `--out` option.
- `installation.json` compares all 461 maintained files with the new installation.
- `python-readiness-original.zip` retains failed/successful startup diagnostics,
  screenshots and the exact browser runners. The full raw NetLog stays local;
  the committed excerpt contains only the failed local request/connection.
- `python-viewer-retest.zip` runs the same original recording against the new
  installed observer on diagnostic port 8877: six locale reloads, seven presets
  in 2D/3D, expansion/camera checks, Timeline, moving arrows, custom views, pan,
  group drag, notes and locale identities pass. Locale reloads took 0.8–1.2 seconds.
  This is a viewer retest of existing native evidence, not a new capture.

The saved Timeline preserves real activation intervals and causal routes.
This recording contains 61 execution instances in two reusable bands, 43
positive-length business intervals and 425 causal flows, with no unassigned
observations. The control checks leave native SQL rows unchanged. This separate
diagnostic observer has no live producer events, so its empty self-observation
check is not sufficient evidence of observer exclusion. Final native UI tests
must run against the active producer/collector and require nonempty live history.
Non-overlapping executions can reuse a band; overlapping executions retain
separate bands. State residency remains distinct from a function's call duration.
The independent test also compares Graph and Timeline event/transfer identities.

The final full regression passes: 1,174 reported tests across 105 unittest
reports, with one existing platform skip. Source checks cover 246 Python and
142 JavaScript modules. Both managed examples retain valid frozen approvals,
and the clean staged Git export passes without reapproval. See `results.json`
for the commands' receipts. Both trial projects must now upgrade normally and
complete their remaining native acceptance. No installed Skill files are edited
by hand.

The first full runner stopped at five Node migration assertions because the
Windows sandbox returned `EPERM` from `realpath` on test directories. The same
16-test migration suite passed in the host environment without code or assertion
changes. `runner-environment.json` links both logs and the full host rerun.

The first host run then found an outdated cancellation-test double: its plain
namespace lacked the new shared connection method. The test now constructs the
real handler without opening a socket and substitutes only the same two failing
write points. Both original cancellation assertions remain. The expanded focused
rerun reports 36 tests, with the one existing platform skip; the final complete
run is retained separately as `full-verify-host-final.log`.
