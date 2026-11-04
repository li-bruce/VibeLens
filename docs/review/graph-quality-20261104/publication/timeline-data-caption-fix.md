# Legacy data lifecycle presentation repair

The supported-Ubuntu CI browser reached the historical Timeline test and failed
with graph cursor `2` versus Timeline cursor `12`. Actual Chrome on Windows
reproduced the same failure: [first run](timeline-cursor-before-01/result.json).

The first suspected cause was a test helper reading four browser round trips
during playback. Sampling those fields atomically is appropriate, but the
[atomic-snapshot rerun](timeline-cursor-retest-01/result.json) still failed.
The error occurred after changing to Data operations, rather than during the
earlier playback check.

The retained page errors identify the product defect. Legacy data recordings
have resolver-supplied terminal states `committed` and `transformed`, with
labels `Committed` and `Transformed`. The Graph caption dictionary lacked both
phases and passed `undefined` into the translator. Graph projection threw;
Timeline and replay controls consequently retained the preceding cursor. The
[direct reproduction](timeline-data-caption-reproduction-01.json) isolates both
nodes against the unchanged actual saved recording.

The repair uses the resolver's existing label when a generic caption is absent.
Both closed data phases use the neutral `historical` display class, matching a
closed return. The native phase, captured status, timestamps, duration, event
IDs and registered lifecycle labels remain unchanged. There is no new business
success classification.

Verification covers the shared resolver's full phase vocabulary: running,
waiting, returned, exception, boundary, unknown, registered ended, and the two
legacy data phases. The [unit result](../timeline-legacy-caption-unit-final-01.json)
checks Graph captions/classes, native durations, Timeline periods and unchanged
event bytes. [Exact API observation](../timeline-legacy-caption-api-final-01.json)
and [viewer semantics](../timeline-legacy-caption-view-final-01.json) still pass.

The final [actual Chrome run](timeline-data-caption-final-03/result.json) passes
all earlier checks with zero page errors: 2D/3D cursor and transfer agreement,
playback/pause, data animation, transform duration, filtering, persistence,
Chinese/mobile presentation and native touch seeking. It also asserts both
legacy nodes' exact phases, neutral display classes and positive native
durations. Business writes remain zero and original recording bytes match.

The atomic test helper remains, with every cursor/transfer assertion retained.
Browser artifact upload now includes hidden files only within its existing
explicit synthetic-evidence paths under `.validation`; it does not upload the
whole working directory. CI reruns and final managed-example acceptance have
separate receipts.
