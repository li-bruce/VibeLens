# Conversation-control containment repair

The file-sharing product acceptance exposed a native controller defect after the shared-policy and source-focus checks had passed. Switching from the compact business view to the requested permission detail reported `applied`, but the declared `policy:read_allowed` node was absent. The prior finite acceptance did not cover this combination.

The current display intentionally removed a boundary node's parent to show its link to the business view. The controller then treated that display projection as its containment inventory. It hid the original `policy:network` parent and could not reveal the requested rule. The original declaration and rule were present throughout.

Control projection now restores canonical model ancestry while retaining generated capture fields. It opens required ancestors even for explicitly selected nested business steps, enables advanced detail for an explicitly requested source node, and leaves the current display/model unchanged. A success receipt requires every requested node to be visible; an incomplete result is rejected. Runtime facts, permission definitions, node identities and source-version checks are unchanged. The Skill and its control reference require this resulting-view check.

## Regression evidence

- [Original browser failure](browser-before/failure.json) and [screenshot](browser-before/failure.png).
- [Final regression against the previous Git module](control-projection-final-against-before.log), [same-test fingerprints](control-regression-pair.json), and [reproducible old-module fixture](control-before-fixture.zip). The failure is the missing canonical parent, not a missing import or test dependency.
- [Passing ancestry/visibility unit](control-projection-final.log), including unchanged display boundaries, nested business expansion, explicit source detail and a rejected acknowledgement for a hidden requested node. The earlier [first red run](control-projection-before.log) remains.
- [Existing conversation-control unit](control-legacy-after.log), retaining activation, scoped preferences and build checks.
- [Unchanged native browser harness](viewer-control-browser.mjs) passes English/Chinese controls, requested node identities, 2D/3D, filtered replay, clipboard, mobile and reduced motion in the isolated captured-project fixture. See its [result](browser-after/result.json), [log](control-browser-after.log), and [candidate asset hashes](candidate-core.json). This static fixture is not evidence of business execution or native server authorization; the independent project round remains separate.

Both shipped examples are completing normal new `control-ancestry-20261029` review and acceptance records. Complete frozen-source regression, clean Git export and independent native-project control acceptance remain pending. Promotional/demo editing is paused during this repair.

## Tooling failures

Windows sandbox permissions initially prevented two pinned npm dependency folders from being created; the authorized serial install passed. A review-helper string replacement named the previous snapshot `semantic-control` instead of `semantic-focus`; it stopped before acceptance. The helper was corrected and resumed the existing pending change using the unchanged prior-source exclusions. Original logs are retained. These setup issues are separate from the controller defect; no test or approval requirement was relaxed.
