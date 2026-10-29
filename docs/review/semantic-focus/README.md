# Keyboard focus and source panel

The independent frozen-version file-sharing upgrade exposed a source-panel dismissal in the native viewer. Selecting a new node, opening its menu with Shift+F10, and choosing Source fetched the correct source with HTTP 200 and a matching build, but restoring keyboard focus selected the node again and closed the panel. Rerendering the semantic controls first avoided the problem; that workaround was not accepted as a passing result.

`SemanticView.render` captured its original `selected` argument in a focus callback. Immediate selection feedback updated `this.selected` without rebuilding the controls, so the callback could use the old value. The callback now reads the current selection. Keyboard navigation to a different node still selects it; returning to the same node preserves the open detail/source panel.

The new regression fails on `b78f03a` and passes after the correction. It covers immediate selection, focus restoration, navigation to another node and focus restoration after a render. It is part of `tools/verify.py`. Both shipped examples use normal new change records and retain their previous expectations and approvals. Original native-browser evidence, failure, source checks and final verification receipts are indexed in this directory.

A separate transport hypothesis was rejected. Old-build recording source requests are already blocked by the recording-version boundary, and the actual failing native-browser request used a new recording with matching view/recording/response builds. No source-version or frontend freshness check was relaxed. A real HTTP regression now checks rejection of old recording source, correct current source, and zero business events from source reads.

The independent project requires a fresh frozen upgrade and the same original keyboard sequence before this issue is considered closed. Its reports remain separate from these framework/example checks.
