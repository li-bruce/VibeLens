# Repair 22 — source inventory reuse under native capture load

P7 remains in progress. This repair removes repeated source-index work; it does
not claim that the complete native capture has passed.

## Preserved failure

The Node observe trial upgraded normally to repair 21. Its four pre-browser
verification commands passed and seven business GUI checks passed. Recording
`7800290145cd4373910d42769eb73353` was interrupted after the native producer
dropped six events at its 4096-item queue limit. The browser producer lost none.
The queue eventually drained; that cannot restore the lost events. The strict
recording rejection is correct. No post-recording verification or acceptance ran.

See [native counters and evidence hashes](native-failure.json). Original event
files, screenshots, data and the failed trial archive remain in the isolated
trial workspace. Published receipts contain counts and hashes, not raw business
data or transport credentials.

## Measured work and changes

Three diagnostic copies started with the same database hash and ordinary cases,
queue capacity, capture scope and deadlines. Instrumentation has overhead; these
runs are diagnostic evidence, not acceptance of the user's application.

1. Excluded JavaScript files were reparsed on every source inventory read. The
   existing reuse applied only to Python. Inspection findings now retain their
   source-byte hash and parser fingerprint for both language families. Errors and
   excluded application endpoints remain visible; edits and deletions invalidate
   cached results. Source is still read on every pass.
2. The project tree repeatedly resolved full physical Windows paths for ordinary
   files. It now uses the existing reader's fresh ancestor-attribute checks and
   keeps physical containment checks for changed/reparse ancestors. This caches
   path construction, not file attributes or content.

Both changes have a before-failing regression. Final review also added an
unfamiliar Windows reparse-file counterexample: its own attributes must prevent
the plain-file fast path. The first complete regression passed before that
additional guard; its failure, correction and final-pass gates remain separate.
The scope suite passed all 29 tests on the host, including Windows junction checks.
A sandbox-only `mklink`
failure is retained separately rather than skipped. Existing admission, field,
sequence, source-boundary and recording-loss checks are unchanged.

## Diagnostic boundary

| Run | View p95 | Second capture |
| --- | ---: | --- |
| [Before](diagnostic-before.json) | 9203 ms | Interrupted |
| [Exclusion cache only](diagnostic-cache-only.json) | 1341 ms | Interrupted |
| [Both changes](diagnostic-after.json) | 1281 ms | Interrupted |

Cold parsing remains necessary. Different request timing changes the observed
backlog and drop count; the table is not a controlled universal speedup claim.
The diagnostic native workload still exceeds the existing queue under capture.
Application event volume and collector throughput need separate follow-up before
native acceptance. No capacity or deadline was raised in these comparisons, and
the original application database hash remained unchanged.

Skill guidance now distinguishes a source-index correction, a capacity failure
and complete native acceptance, and requires preserving each producer's facts.
Full regression, managed-example reviews and a fresh installation follow these
targeted checks. Python cancellation, the Node baseline/iteration, both source
refactors, the final matrix and accepted product scenes remain open P7 work.

## Application volume and transport sizing

A read-only audit of the original Node trial found no accidental duplicate probes
or observer self-capture in this chain. `src/service.mjs::listFiles` scans every
file and performs real per-file queries and authorization. The isolated bridge
projects the decision's existing steps; it does not run the predicate again.
For N total files, O owned by the caller, one successful list HTTP request emits
`8 + 14*O + 16*(N-O)` events. The ordinary GUI sequence makes six Alice lists and
eight other-member lists; each additional Alice file therefore adds about 212
events. Original samples match this source-derived formula.

The [transport sizing receipt](transport-budget-analysis.json) separates a
proposed finite 8192-item queue from the source-index fixes. Observed envelope
bytes suggest about 9.27 MiB at that capacity, excluding object overhead; the
protocol's per-envelope ceiling implies a much larger worst case. No queue
setting changed in the diagnostic comparisons above. A normal technical change
and fresh native acceptance are still required. Original small-queue failures,
deadlines, operations, capture fields and loss checks must remain intact.

## Completed repair gates

Final complete regression passed: 1300 reported tests across 116 unittest reports, including repeated suites. Source checks, both managed examples, the fresh installed scope counterexamples and clean staged export passed. See [results](results.json). Native capture and P7 remain pending.
