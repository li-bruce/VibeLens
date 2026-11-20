# Keep each fact's actual read point

The Node iteration adds a current-permission check when a queued download begins
preparation. Its first draft broadened the read timing of three existing file
facts. The unchanged announcement operations then appeared among 86 records
requiring review. The original [validation](concept-confirmed-validation.json)
and [independent dependency diagnosis](p7-node-scope-review.json) are retained.

This was a modeling error, not a global policy-version bug. The existing
`editor-has-no-file-power` example connects announcement and file permissions.
The confirmation checker follows that declared dependency and correctly refuses
to reuse an old snapshot after its file facts' read basis changes.

The corrected draft preserves those original facts and gives the new worker
checkpoint its own fact bindings. The intermediate
[recheck](concept-qualified-validation.json) reduces the blocked set to the
changed `file-share-revoke` relationship. That remaining relationship still needs
its applicable review; the document does not claim complete design or native
acceptance. Original accepted confirmations were not rewritten.

The maintained [concept guide](../../../../../skills/vibelens/references/concept-models.md)
now explains how to distinguish a new read point from a change to a shared fact.
It also requires following the dependency path before changing a checker or
reconfirming unrelated business behavior. Predicate definitions can remain
shared while invocation timing and parameter bindings remain explicit.

Two existing regressions passed: read-basis changes invalidate confirmation, and
reducing the active scope cannot conceal affected shared consumers. No runtime
check was weakened or changed. [Results and original-file hashes](results.json)
describe this intermediate diagnosis only; P7 remains in progress.
