# Complete-capture boundary under continuing application refresh

`dialogue-04-browser-v2-final-02` passed the native upload/review/share/revocation
actions but its recording is interrupted, not accepted as complete. The stop
request exhausted the existing two-second producer flush bound. At the final
checkpoint, 7,076 envelopes were enqueued, 5,935 received and 1,141 pending.
There were zero producer errors/drops. The saved recording explicitly contains
the queue-drain gap. Raw recording, screenshots and failure JSON are retained.

The application's own `static/app.js` reloads the whole workspace every three
seconds. Three logged-in browser pages therefore keep producing real application
reads, including per-file permission/data work as synthetic files accumulate.
These are application requests, not observer traffic, so excluding them would
misrepresent capture. Example revalidation was also running on the host.

No queue timeout, scope, completeness check or business implementation is changed
to turn this run green. The next finite-flow test closes the application pages
after the last user action, waits for the actual queued facts to arrive, and then
stops the recording. The separate SDK/browser regression already exercises stop
during active work and mid-operation recording at its tested event rate.

Sustained-throughput and stop-latency guarantees under ongoing read traffic remain
unmeasured. This is a retained operating limit, not proof of an optimized
high-throughput recorder. Queue gaps must remain visible.

Finite-flow retest `dialogue-04-browser-v2-final-03/recording.json` contains 6,608
events, an empty gap list and `producer_settlement.flushed=true`. The unchanged
recording passed canonical UI review in `dialogue-04-browser-v2-replay-final-05`.
That result does not remove the continuing-refresh operating limit above.
