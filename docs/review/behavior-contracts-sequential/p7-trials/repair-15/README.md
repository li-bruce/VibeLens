# Native recording and state-model display review

Status: P7 remains in progress. The original Python drive recording on repair 14
passed independent native checks. Display repair 15 passed the complete maintained
regression, source checks, fresh installation comparison and clean-export checks.
Fresh browser review follows; this is not final trial acceptance. The full run
reported 1166 tests in 104 unittest suites with one existing skip, alongside the
maintained JavaScript and pinned TLC checks. See `results.json` for gate receipts.

## Retained native result

Recording `a5e61bbc90bf4d17a65ecb7c0aaf35bc` contains 2310 events and 24 frames.
All 12 native transitions across file, grant, download-job and announcement models
match their independent SQL rows and exact recorded frames. Same-version reads
retain persisted context, denied input does not rewrite it, invocation lifetimes
close, actual HTTP rejections retain return observations, and the recording has
no gaps. One transport retry was retained. Stop settled its fixed prefix at
2388/2388; four subsequently submitted items were outside that prefix.

The original recording, native comparisons, actual responses and screenshots are
in `python-native-recording.zip`; `python-native-summary.json` indexes the checks.
No stopped recording was supplemented or relabeled as a new run.

## Independent desktop checks

`python-ui-before-repair.zip` retains all initial checks, failures and retests:

- Seven actual layer presets have nonempty contents and matching 2D/3D identities;
  expanding a node preserves the camera.
- Real Timeline lifetimes include positive business intervals. Execution bands
  collapse independently, causal connectors remain present, zoom/pan and selected
  playback intervals work, and depth/single-layer controls preserve the same
  graph and Timeline cursor.
- Paused-step arrows visibly move in both renderers with the same identities.
- Saved custom views, language switching, source-name toggling, pan, multi-node
  dragging and annotations passed the completed controls run. Native table hashes
  were unchanged; observer control requests did not enter business observations.

The first Timeline runner attempted to clear an already empty selection. The
first controls runner referenced `graphDebug` before initialization. Both harness
errors were corrected without changing product code or assertions. Two later
controls runs timed out waiting for reload/language readiness. The next diagnostic
run passed; the intermittent readiness condition still needs a focused check.
Do not summarize every original controls attempt as passing.

## Shared repair

The state preset still showed 43 separate nodes after Collapse: conceptual states
folded, but their events, guards, effects, transitions and separately bound native
states stayed outside the model. The shared inventory now derives display groups
from declared model membership and registered model IDs. Both renderers consume
that inventory. Nested state ownership remains intact; conflicting owners remain
explicit relations. Source ancestry, semantic edges, IDs and runtime lifetimes
are unchanged.

The new regression first failed on the ungrouped event. It now covers native and
conceptual occurrences, equal local state names in separate models, ambiguous
owners, existing ancestry and absence of fabricated lifetimes. An offline check
of the unchanged native recording retains all IDs/relations: four collapsed model
entries expand to all 55 state-layer nodes, with 2D/3D parity. This offline
projection check is separate from the pending fresh browser check.

The actual names artifact also copied English state values into Chinese entries.
The Skill now explicitly distinguishes inventory/fingerprint checks from review
of translation meaning; the trial maintains both sets of aliases through its
normal naming commands. No runtime translator or automatic business rewrite is
introduced.

The original naming review is retained in `python-name-review.zip`: 12 states and
10 events across four models, with 110 actual browser checks of English/Chinese
and source-name views. IDs, original recordings and application behavior are
unchanged. The first language-navigation race remains in that archive; the
completed screenshot runner waited for the new document and initialized options.

The first full regression correctly rejected stale viewer copies in the shipped
examples. `tools/sync_runtime.py` and the ordinary example review/check sequence
refresh those copies; the original package assertion remains unchanged.

The next full run exposed an HTTP transport defect: after rejecting a group over
256 KiB, the server drained at most 64 KiB of unread input. Closing with the rest
still in flight could abort the Windows connection before its HTTP 400 reached
the client. The transport cleanup now drains at most 2 MiB in 8 KiB chunks under
the original 250 ms deadline. Admission limits, timeouts, parsing and accepted
event counts are unchanged. Arbitrarily large or stalled senders still stop at
the byte/deadline bound. A deterministic regression first reproduced the truncated
drain; all 16 transport tests then passed, followed by three repeated real HTTP
over-limit checks. Both original full-run failures remain in their original logs.

The final candidate is `state-model-http-skills/vibelens` under the isolated trial
directory; `installation-final.json` verifies 459 maintained files byte-for-byte.
The earlier candidate remains untouched. Offline npm installation first lacked a
cached locked TypeScript archive; the retained retry used the same lockfile and
downloaded dependencies into a workspace cache with lifecycle scripts disabled.

## Remaining work

Recheck model folding and the readiness condition, resolve the Node policy-wiring
and transaction-completion diagnostics, then continue Node observe recording, both semantic
iterations and source-only refactors. Final dialogue, screenshots and local
product scenes follow the completed native checks. Main/release/Pages publishing
is outside this branch's current acceptance work.
