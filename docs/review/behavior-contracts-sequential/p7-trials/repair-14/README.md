# P7 repair 14 — interactive capture throughput

Status: focused, source, managed-example, full regression, fresh installation and
detached external-process load gates passed. Native acceptance remains pending. P7 is open.

## Preserved native failure

Python drive recording `b5a562d365424e3ba1264898d4370ff5` stopped with 1033 events
and 12 frames. Only six of the 12 native transitions had matching recorded
frames. The stop prefix was 2188 envelopes; 1088 had completed and 1116 remained
pending. Six retries, no reported transport errors or drops, and three unfinished
invocations were observed. This is incomplete capture, not successful acceptance.

`prior-python-recording.zip` preserves the original recording, executed script,
independent SQL/HTTP comparisons, screenshot and strict observations.
`prior-python-source.zip` and `prior-python-source.json` preserve the matching
source and contracts after checking every bound source hash. The summary retains
the original build/candidate identity and stopped-process receipt.

## Findings and changes

1. Event groups and single envelopes shared a 24 KiB wire limit. Real envelopes
   therefore split into small groups and repeated strict source checks. Groups
   now allow 256 KiB and at most 64 original events. Each event and snapshot still
   has a 24 KiB limit, including events inside a group. Atomic preflight, source
   checks on both sides, snapshot barriers, original identities, flush prefixes
   and HTTP deadlines remain unchanged in Python and JavaScript.
2. `/api/design` polled the complete discovery validator during ordinary runtime
   viewing. In `http-profile-external-http.json`, nine requests consumed 6.52 CPU
   seconds; individual requests lasted up to 0.79 seconds. This stalled ingress
   beyond the probe's ordinary deadline. `BODesign.document` now reuses successful
   document-only validation for exactly equal bytes. It rereads current bytes and
   checks physical containment on every request. Invalid changes are rejected;
   focus, language, runtime sources and implementation checks remain independent.

The new polling regression first failed with 12 assessments for 12 unchanged
reads. It now verifies one assessment across concurrent reads, detached returned
documents, same-size/same-timestamp invalid edits, deletion, and fresh focus and
language. The group regression retains oversized individual/group rejection,
exact original identity and complete queue settlement for both SDKs.

## Diagnostic limits and retests

The original three strict `on` runs supply 3260 events and 106 snapshots with
distinct instance identities. Detached diagnosis executes no application business
operation. Moving the SQLite copy changes its endpoint identity: results record
both builds, replacing only that field in derived input. It is not native evidence.

The repair-13 same-process producer slowed with the collector and underestimated
input pressure. The new sender runs in a separate process. All full-load runs use
the real viewer, normal database watcher, HTTP capture controls and original
deadlines. No scope, assertion or capture budget is reduced.

| Diagnostic | Result at the ordinary stop boundary |
| --- | --- |
| `budget-before` / `budget-after` | Same-process comparison; the latter drains, but is insufficient evidence of remote capacity |
| `external-after` | Larger group alone leaves 1121 messages pending |
| `external-fair` | Shorter Python scheduling interval does not solve the backlog; not adopted |
| `external-clone` | JSON-copy prototype does not solve the backlog; not adopted |
| `external-source-process` | Source-reader subprocess prototype does not solve the backlog; not adopted |
| `external-core` | No viewer/watcher: complete diagnostic capture; used only to isolate the contention |
| `external-http` | Request wall/CPU measurements locate repeated design validation |
| `external-design-cache` | Complete 3260 events / 106 frames, zero pending, retries, errors or drops |
| `canonical-design-cache` | Maintained implementation without prototype substitutions: same complete counts and zero pending/retries/errors/drops |

In the last run, the external sender enqueued the input in 14.57 seconds. There
were 616 pending envelopes immediately before stop; all 3366 settled within the
normal stop operation. This is a local diagnostic result, not a universal rate
guarantee or a replacement for an ordinary native business recording.

`profiler-first.log` preserves a Python 3.13 profiling conflict. The guarded
concurrent cProfile reports mix threads and are not per-method CPU attribution.
Serial profiles and request `thread_time` measurements avoid that ambiguity.
`design-polling-retest.log` retains a missing test import path; the correctly
configured retest passes eight tests. The first batch retest preserves three
Windows junction permission failures and an overbroad lost-ACK test assertion.
That assertion now checks that IDs in the lost group are never replayed singly;
legitimate unrelated singleton messages immediately before a snapshot are allowed.
Exact retained IDs, retry counts and deduplication checks remain intact.

Native Python/Node recordings, independent Web/Timeline checks, both business
iterations, source-only refactors and final dialogue/product materials are still
required before P7 can close.

Complete regression: 1165 reported tests across 104 unittest reports, plus JavaScript and pinned TLC checks. Clean-export results are retained separately.

Clean staged export: both examples passed using their frozen approvals, with no regeneration or reapproval.

Raw profiler bytes are retained in `raw-profiler-output.zip`; readable text copies normalize only trailing blank lines.
