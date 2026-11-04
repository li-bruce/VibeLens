# Paused Timeline connector regression

The v0.11.2 tag's registered-lifecycle browser check found a real animation stop.
Its two 20 × 66 pixel screenshots showed the same visible connector. A separate
host run passed while it was still inside the first animation cycle; that pass
did not establish continued paused inspection.

The [retained diagnostic](../lifecycle-registered-motion-diagnostic-01/diagnosis.json)
takes 36 successive native screenshots at one selected event. The Timeline has
its own painted causal route and the graph has no matching transfer. Motion
changes initially, then stops after approximately 1.1 seconds. The original
pixel-motion assertion fails. No synthetic event or runtime mutation is used.

The fix keeps inspection animation active for the currently painted causal
route whose raw index exactly matches the selected event. Hidden-view,
hidden-document and reduced-motion guards remain. Other historical routes do
not start animation merely by being visible.

[Fresh acceptance](summary.json) binds the results to the two tested source-file
SHA256 values. Three actual registered-lifecycle Chrome runs each keep the same
event selected through at least 1.3 seconds of native frames with zero graph
transfers, then pass the original screenshot-motion and raw-identity assertions.
Default, recording-midspan, concurrent-band and concurrent-midspan browser checks
also pass. Trace/lifecycle/context units and source formatting pass separately.

These are local results for the v0.11.3 candidate. Remote CI, managed example
acceptance and the independent application upgrade remain separate gates.
Only synthetic screenshots and finite result/geometry/hash receipts are copied
here; complete recordings, fixture databases and service logs remain in ignored
local validation storage.
