# Shared Adapter Gap: Missing Enclosing Data-Call Identity

Evidence: `runtime-freeze-audit.json`, `final-view.json`,
`final-e190b2e6b29345818a9d6cb23f654196.json`, and the original
`bo_stategraph/data/` records retained in the project and archive.

The final live stream contains 94 events whose node begins with `db_`; none has
a nonempty parent_call_id. Outer HTTP and business spans retain their own call
identities and parent links. Data intervals can satisfy the canonical closure
check while appearing as separate Timeline execution groups. Timestamp proximity
cannot supply the absent parent relation and was not used to fabricate one.

The application uses the installed canonical BODataRuntime and native BOProbe.
Inspect the copied `observer_runtime/bo_observer/data/runtime.py` and
`observer_runtime/bo_observer/adapters/python/bo_probe.py` read-only. Shared source,
validators, installed files, recorded events and parent IDs were not patched.

The user's requested next prerequisite is a maintained-project adapter repair
with concurrent context isolation tests. After that, a new explicitly authorized
conversation should upgrade via normal bo_upgrade, retain the active baseline,
regenerate and rerun all protected checks with fresh native events. Include
nested transaction/query/transform ownership, error exits, concurrent requests,
and zero observer events for polling and recording controls. This is a pending
verification obligation, not a proposed new business rule.
