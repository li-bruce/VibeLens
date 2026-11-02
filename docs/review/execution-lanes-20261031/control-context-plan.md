# Graph controls remain usable after event history grows

Trial 08's ordinary application and recording checks passed, then conversation
control activation failed at the fixed 8 MiB inspection limit. The CLI retrieves
`/api/view` to obtain the graph model and build identity, but that response also
contains event history and retained runtime frames. Normal observation growth
therefore disables model controls even when the model is small.

Keep the existing response budget. Add a model-only control context through the
existing `BOWeb` route dispatch and existing integration callback. The standard
`GraphSession` provides this context without reading history, instances or frames.
Custom integrations may keep their existing callback; only model/build fields
cross the new endpoint. Activation, inspection, planning and application use it.
Stopped-recording filtering still reads the exact requested recording and retains
its existing budget and evidence checks. No fallback empties history or fabricates
an accepted run.

Tests cover actual HTTP commands with an unrelated runtime payload above the
budget, unchanged model/build identities, bounded reads, observer-route exclusion,
and the standard session path without runtime assembly. Existing scope, prefix,
staleness, original-event and browser checks remain unchanged. Freeze the repaired
managed examples, run the complete repository gate, then resume the frozen trial
in a new conversation. Preserve prior unaffected Web evidence and repeat affected
controls plus ordinary feature iterations.
