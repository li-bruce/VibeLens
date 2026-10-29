# Revocation V2: measured capture drain

Build: `843e214363b362d939aba82229a7abf66f6ed128d52b978b4867f03ccb22cf67`.
Frozen framework: `e69ce0921ac06fb455ec0aedc403e24d74babebc`.

The final browser run completed the actual business operations before sampling the capture drain. The producer then stayed fixed at 1,731 events and 11 snapshots. No operation, success event, or missing state was synthesized to finish the recording.

| Elapsed seconds | Pending envelopes | Observer events accepted | Completed sends |
|---:|---:|---:|---:|
| 10.303 | 1,641 | 102 | 101 |
| 155.838 | 901 | 839 | 841 |
| 292.848 | 286 | 1,451 | 1,456 |
| 363.123 | 0 | 1,731 | 1,742 |

Producer counters and the observer view are read sequentially, so intermediate rows are not atomic cross-process snapshots. Completed sends include both events and snapshots. With zero transport errors/drops, this count is the fixed enqueued envelope total minus the actual unfinished queue tasks. Final counts converge exactly: 1,731 accepted events plus 11 accepted state frames equals 1,742 completed envelopes.

The complete 35-sample series is [drain-progress.json](browser/20261029T034258Z-7c262b/drain-progress.json). Its queue count decreases monotonically, accepted events increase monotonically, the sender remains alive, and enqueued counts remain unchanged. The browser also rejects six successive samples without queue progress. This run shows continuing drain rather than a stopped sender, a moving target, or a continuing capture source.

The actual wait predicate is the native `BOProbe.flush(10)` result, which checks `queue.unfinished_tasks == 0`. The browser repeats that bounded wait for at most 900 seconds, then additionally requires pending=0, accepted events equal the stable producer event count, accepted frames equal the snapshot count, and zero errors/drops. It does not substitute a guessed event target for queue completion.

The last HTTP 200 flush response was:

```json
{"dropped":0,"enqueued_events":1731,"enqueued_snapshots":11,"errors":0,"flushed":true,"pending_envelopes":0,"waiting_envelopes":0,"worker_alive":true}
```

The recording subsequently stopped normally with zero gaps. Total measured drain wait was **363.125 seconds**. The public transport timeout supplied by the project adapter is 10 seconds per item; the framework's sender and per-item validation remain unchanged. These settings are distinct from the 900-second total browser wait and the 900-second native project-command budget.

The installed sender has one worker. `GraphSession.event` and `GraphSession.snapshot` each call the full binding check before accepting an item; the current manifest binds 52 source files. This is consistent with substantial serialized per-item work. Three separate read-only binding checks in the restricted diagnostic process took 1.0009, 0.8471, and 0.9196 seconds and all reported current. Those timings are environment-specific and are not interchangeable with the live server's throughput or proof of an exclusive cause. See [revocation-binding-cost.json](revocation-binding-cost.json).

The earlier 300-second browser attempt remains failed. Its retained recording later became interrupted when that superseded build was stopped, and its shutdown gap is preserved. The final run is separate evidence; it does not retroactively convert that attempt into a pass.

This is a finite successful capture-completeness check. **Real-time observation performance has not passed.** The delay remains a separate framework performance limitation. No framework validator, sender, projector, viewer, test, or admission check was weakened. The known Boolean data/guard replay matching issue also remains unchanged.
