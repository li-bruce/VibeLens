# Repair 26 — capture backlog and repeated display copies

Status: repository regression and clean-export validation passed. The Node semantic
iteration is not accepted. Its failed record and the repair-25 provider are frozen.
Python's completed acceptance belongs to repair 25, not this candidate.

## Retained failure

Node build `82c63ac0` passed its native page checks and first recording, then failed
the ordinary browser recording `60272dedcbca4a97a96d17d147379584`. Before cleanup,
the producer reported 9703 submitted, 3234 completed, 6469 pending and 21 transport
retries. A failed single delivery also advances `completed`; this counter alone
does not prove successful delivery. The original run has no per-request network
audit, so its exact last acknowledged envelope is unknown.

Isolated copies reproduce slow collector responses and the queue failure with
the original workload, assertions, capacities and deadlines. Stack/method/network
diagnostics add overhead: these are causal investigations, not controlled
benchmarks or acceptance of the original project. Two copies also expose a
separate account-switch UI defect. No failed interval is rewritten as successful.

## Changes under test

- Recording catalog/version lookups now read the pinned build/model identity.
  They no longer copy the full graph or construct runtime instances.
- Display documents and bulk event lists use detached copies of already
  validated JSON. All fields remain present; native Python object copies and
  admission validators retain their existing contracts.
- Windows source reads verify the actual opened file handle. The earlier
  path-check/open sequence admitted a directory replacement between its checks.
  A regression reproduces that race with a temporary directory junction.
  Containment and byte reading now refer to the same open file.
- Both project and source handles use normalized NT paths. A first DOS-path
  implementation passed host tests but failed inside the Windows sandbox with
  error 5. The NT representation avoids drive-letter translation and still checks
  the resolved target. Failure to resolve a handle does not permit an unchecked
  path read. Source bytes are reread, including same-size/same-timestamp edits.

The API semantics are documented by
[Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew).
The access-denied symptom also matches a reported
[Windows AppContainer case](https://github.com/microsoft/STL/issues/6286);
our sandbox and host checks establish the result for this environment.

## Failed checks and repairs

The new catalog test first failed because a lookup copied the full graph. Its
retest passed with the identity-only provider. The first event-copy regression
run exposed two test defects: a new test addressed `fields` instead of the actual
`outputs`, and an existing concurrency fixture intercepted the former deepcopy
call. The fixture now intercepts the actual JSON-copy boundary, retaining its
same admission deadline, coherent snapshot and detached-value assertions.

The first source check rejected formatting of the new Windows module. It was
formatted without changing behavior. All failed receipts remain alongside their
later retests. Shared full regression, fresh package installation and renewed
native/browser acceptance are separate pending gates.

## Complete diagnostic workload after the copy repair

`diagnostic-after2` passes all seven native page checks and its first recording
with 2066 events. During the second recording, the native queue reaches 9291
completed out of 10239 submitted, with no transport errors or retries. The next
independent health request fails with Windows `10048`; cleanup cannot finish
the interval normally. This run is still a failure, not an accepted recording.

Read-only socket inspection subsequently finds 13400 TIME_WAIT sockets at local
port 17891, separate from the trial's four server ports. The configured dynamic
port range has 16384 ports. This supports local connection exhaustion as the
immediate failure; it does not establish which application created that traffic.
Proxy settings and unrelated processes were left unchanged. The first socket
aggregation accidentally flattened rows and is excluded; the corrected aggregate
is retained. Host and sandbox both report localhost proxy bypass enabled.

Method instrumentation records event-batch p50/p95 at 117/386 ms, versus 766/1718 ms
in the earlier timed copy. These runs have different execution histories and
ambient load; the numbers identify reduced work, not a performance guarantee.
Original capacities, socket deadlines and assertions are unchanged.

The independent UI diagnosis reproduces stale-account rows, a late success
overwriting the next account, a late 401 clearing its session, and old refreshes
overwriting newer results. The Skill's iteration guidance now includes these
account-scoped cases when applicable. Application repair is tracked separately
from observer capture; simulated interface responses cannot prove backend
authorization or native-recording correctness.

## Example delivery check

The first complete repository run reaches the clarification integration test and
fails the shipped delivery example's architecture guard: synchronized observer
files no longer match its old managed-file seal. This is a missed maintenance
review step, and the existing guard correctly rejects it. No test is weakened.
After confirming every configured application source is byte-identical to HEAD,
both examples are sealed through the canonical command, inspected, verified,
accepted and checked. The complete repository suite is then restarted. Frozen
release fixtures will only be updated after that full pass.

[Diagnostic archive index](diagnostic-index.json) lists each selected file and its
SHA-256. The archives retain the original failure and timed copies; dependency
trees and the earlier 1.2 GB backup are excluded. Its original local bytes remain
preserved. Renewed installed-project acceptance is still required.

## Repository retest

The unchanged full `tools/verify.py --database` gate passes after the example
maintenance review. The 83 targeted regressions and 10 Windows source tests also
pass. Both accepted examples have new frozen release records; previous records
remain available. A fresh offline installation contains 466 maintained files,
each byte-identical to the source candidate. Clean-export validation passes for
both examples. The final source check passes in the project's `.venv`; earlier
attempts used interpreters without the pinned Ruff/Black packages and retain
their nonzero receipts. Native trial acceptance is separate; this pass does not replace
the failed Node recording or the earlier Python provider's acceptance.
