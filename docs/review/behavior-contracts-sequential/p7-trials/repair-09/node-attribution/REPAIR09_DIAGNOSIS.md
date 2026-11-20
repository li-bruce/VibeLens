# Repair09 diagnostic: seq34 receipt still missed both deadlines

One first-recording-only run, unified-1795153948. Provider: admission-candidate-skills/vibelens; build fba54b746a910206fa87701dc0cc2d4245ee0d724a68261acbdf92af2124df34. Canonical plan/apply/check passed with zero managed-file changes. All eight JavaScript adapters are byte-identical to the previous provider; application/on/off/fault and read-only CLI tools selected the new provider. Existing database and strict API checks passed. App/observer source and the immutable baseline remained unchanged.

The actual stop response is HTTP200/**interrupted**,1104 events, one explicit producer-transport gap. Producer settlement is flushed true,1145/1145,pending0. Native health is completed1133/1133,pending0,errors1,dropped0,data_errors0,capture_control_errors0. This is not a successful recording. No second run, second recording, final accept or business iteration was performed.

The only two failed request attempts are the same880-byte api_login/enter event at source sequence34. Their request-body SHA256 is identical:275ff7171cae0e741252171bee947cd18ddbf356725f34de50c96af298913283. The original1000ms deadline and two-attempt policy were unchanged. Both client attempts timed out; no later successful client receipt exists for that logical event. The server nevertheless retained that event exactly once, and native source sequences34-1125 are contiguous (1092native events plus12browser events). Client acknowledgement failure and eventual event retention are distinct facts.

Both attempts have unique TCP tuple/path/request-index joins. The broader audit has478 unique joins and98 ambiguous polling-port reuse keys left unmatched, without guessing. All target method/request end rows are present.

All values below are milliseconds. sendHeaders is Undici's pre-write hook, not a wire-arrival timestamp. Pre-binding includes original parsing, validation, session borrowing and lock waiting; it is not a pure mutex-wait measurement.

| Attempt | Client timeout | Before send hook | Hook to dispatch | Dispatch to binding | Binding duration | Server dispatch total |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 1006.5 | 174.0 | 9.7 | 422.5 | 1445.6 | 1958.9 |
| 2 | 1003.5 | 3.0 | 314.2 | 1489.0 | 65.8 | 1557.4 |

Attempt1 was slow inside binding (1445.6ms), after422.5ms before that call. Its HTTP dispatch eventually completed with200 after1958.9ms. Attempt2 spent1489.0ms before binding; binding itself then took65.8ms, and dispatch completed after1557.4ms. Both server completions occurred after the client's two deadline expirations. No original response or error was altered by the timer.

**The DataWatch validation memo is active in this actual run:**23 completed ticks contain only1 protocol.validate_project call. Total completed protocol.validate_project calls are7:4 startup/MainThread,2 first/api/view,1 DB watcher. The watcher validation call was at1795153975796-1795153976449ms, well before the two seq34 windows around1795154021xxx-1795154023xxxms. Therefore these failures cannot be attributed to continued full project validation on every tick.

The failed request windows still overlap a4757ms DataWatch.tick, recording-worker views of1348/1480ms, and other binding/batch calls. The first window overlaps the recording worker's729ms binding; the second overlaps the original request's1446ms binding plus other batch calls. These are temporal overlaps, not measurements of a unique lock owner. Tick's collection/projection/serialization/reload subphases and binding's byte-read/digest/queue subphases were not separately timed. The remaining tick cost must stay unresolved rather than being relabeled as validate_project.

Before stop, health was sampled for15.77seconds. Enqueued stayed1125 while pending fell1097->0. This is a finite backlog draining, not ongoing task-page business production. The page was Team files. The exact stack, raw637-byte stop response and hash5c2fdd1a0cbeacfe6d565bf3d432f1bef52d8eadec07eede96d3d38b13581b81 remain in this run.

All owned services were alive before parent cleanup. The coordinating chat subsequently confirmed full09 regression began only after this diagnostic ended; see the derived load-context correction. Other host load is unisolated. The run uses selected-method timing only, with no faulthandler, sys.settrace, whole-function profiler, HTTP-argument changes, lock replacement or SDK deadline change. Timer overhead was not independently measured.

This result does not erase the previous1048-event completed diagnostic recording or older normal failures. Data/fixture counts differ between retained runs, so duration differences are not a controlled performance comparison. Full09 root regression, full browser modes/second recording and final acceptance remain separate pending work.
