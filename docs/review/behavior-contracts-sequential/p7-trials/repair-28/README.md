# P7 consolidated repair and capture review

**P7 remains in progress.** The repaired Node application's seven ordinary UI
checks pass. Its second recording loses 421 producer events and correctly remains
`interrupted`. The failed candidate has not been accepted. No new chat was created.

## Findings and disposition

| Finding | Repair or diagnosis | Evidence and remaining gate |
| --- | --- | --- |
| Extracted announcement frontend omitted `jsonRequest` | Reconnected the existing helper; added actual publish/save DOM submissions to the original sixth command | Old source fails both submissions; repaired source passes all 24 frontend checks and all seven ordinary UI checks |
| Login bootstrap could clear already typed input | Existing input-epoch repair retained | Four controlled delayed-response cases fail before the repair; the original 16 and four new cases pass afterward |
| Ordinary capture drops a burst despite a settled stop prefix | 9,376 enqueued events in about 3.7 s; 421 discarded at the unchanged 8,192-item waiting limit; later drain completes | Raw second record has 9,029 events and a capture gap. Neither a successful stop response nor passing native cases makes it complete |
| Every event in a batch rescans all node declarations | Build one request-local owner/exclusion index per batch | Individual schema, provenance, field, payload and type checks remain; both actual-source boundaries, atomic publication and duplicate receipts remain |
| Successful mapping checks could conceal an ordinary GUI/capture failure | Root acceptance preflight requires ordinary command success, seven UI cases and two complete recordings separately | Retains the earlier real failure as a negative acceptance case; current failed epoch is not accepted |

The installed provider remains commit
`66efb5e24ae4b702bfa8f0515c90a3f2c2e637c4`. The maintained source now contains the
request-local index change; that is a different provider candidate. No installed
files, capture definitions, queue sizes, native command arrays or raw recordings
were rewritten to apply it.

## Regression and performance scope

The focused batch executes 70 tests across protocol reuse, atomic admission,
actual HTTP/Python/Node delivery, history, recording evidence, capture bridge,
documents and plan checks. Source changes with preserved timestamps/length,
invalid event suffixes, field declarations, observer exclusions and duplicate
identities retain their rejection checks.

The first new test expected the word `capture`; the existing validator correctly
raised `unapproved type or value length`. The test now checks that actual type
rejection. This was an expectation-message error, not an accepted invalid event.
The first complete repository run stopped at `Runtime copy is stale: protocol.py`.
`tools/sync_runtime.py` updated the shipped examples through the existing managed
workflow. The original failed run is retained alongside its subsequent run.

An alternating same-process comparison of the same 128 previously captured
envelopes measured median validation time of 34.10 ms before and 21.37 ms after
the index change (37.3% lower). Output values are equal. This measures validation
only. Separate profiled full-admission samples were 122.1 and 125.1 ms per 64
events and did **not** establish an overall throughput improvement. Neither
measurement proves that the original burst now records without loss.

## Independent desktop review

Six desktop groups pass on the existing failed-capture candidate: initial loading,
all mapped layers in 2D/3D, Timeline, transfer arrows, drag/custom views/annotations,
and English/Chinese labels with source highlighting. An additional Timeline brush
selects exactly 4,932 original event identities. These checks neither replay the
business workload nor repair the missing events. The viewer visibly retains the
recording gap; no browser errors were reported by the interval check.

The native-controls check preserves application rows and sees four live startup
events before and after viewer interactions. Recording and source originals remain
unchanged. Personal layout/annotation changes made by those UI tests are deliberate
reviewer actions, not source-only refactoring evidence.

## Evidence

- [Native outcomes and archive indices](native-results.json): two distinct failed
  ordinary epochs, source identities and independent desktop scope.
- [Original failure, repair and targeted checks](failure-and-repair-evidence.json)
  and [archive](failure-and-repair-evidence.zip).
- [Independent desktop checks](independent-desktop-evidence.json) and
  [archive](independent-desktop-evidence.zip).
- [Failed candidate source and models](failed-candidate-source.json) and
  [archive](failed-candidate-source.zip).
- [Producer flow diagnosis](FLOW_DIAGNOSIS.md),
  [sample counters](flow-health-timeline.json), and
  [partial-recording audit](independent-partial-recording-audit.json).
- [Visible dialogue index](visible-dialogue.json) and
  [public conversation archive](visible-dialogue.zip): 494 messages through the
  failed-capture handoff.
- [Initial check failures](initial-check-failures.md),
  [negative acceptance gates](native-negative-gates.json), and
  [alternating validation measurement](index-comparison.json).

Archives contain original selected files with per-member SHA-256 values. Native
databases, installed dependencies and collector credentials are not exported.
The visible conversation export contains public exchanges and usage metadata,
not private reasoning. Coordination and repair costs prevent a controlled token
efficiency claim.

## Remaining batch

1. The maintained-source repository/package gate, including database checks, passed
   after runtime synchronization and managed ownership review. Both preceding
   failed gate outputs remain under `checks/`.
2. Measure the remaining HTTP, source-boundary, live-view and persistence costs
   together on a detached representative workload, including its sustained burst.
   Keep limits and checks fixed; the partial index optimization alone is insufficient
   evidence to schedule another expensive native run.
3. After the whole capture repair passes that regression, install the reviewed
   provider through maintenance and finish the existing Node candidate's native,
   ordinary-recording and desktop acceptance together. Preserve the accepted
   Python provider evidence separately from any newer-provider regression.
4. Consolidate A24–A34, dialogue and exact-candidate evidence. No main-branch merge,
   release, Pages deployment or marketplace update belongs to this batch.
