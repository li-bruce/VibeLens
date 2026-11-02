# Development findings

The initial baseline at `.stategraph/initial/baseline.json` remains immutable. Requirements, expected outcomes and required on/off/fault modes were preserved.

- The first metadata configuration incorrectly supplied `target_actions` on transactions. The canonical validator rejected it. The project declaration was corrected; no validator was changed.
- Native policy execution returns `value`, not `allowed`. The application integration was corrected before independent testing.
- Raw sqlite3 context managers do not close connections. The independent test fixture now uses `contextlib.closing`, preventing Windows file locks during disposable test cleanup.
- Test databases are created only under `review/test-data`, with a resolved containment check before disposable cleanup. The system sandbox temporary path was unsuitable for SQLite access.
- Flask's default URL canonicalization redirected `/api/files` to the HTML root. Disabling default-value redirects preserves the JSON API path. Static asset routing is explicitly `/static`.
- Initial transport diagnostics exposed a project adapter passing integer `attempt=1` to policy events. The adapter now uses the native probe's string application attempt identity.
- Initial state snapshots lacked an explicit matching `revision` on their witnessed change events. The actual native revision is now supplied at both boundaries.
- Diagnostic sink forwarding retains the canonical sink's batching and rejection behavior. It records bounded error messages and rethrows; it does not accept or rewrite rejected events.

These are application/integration fixes. No canonical runtime, validator or projector was patched. Preflight observations and normal verification remain separate; failed or missing captures are not accepted evidence.
