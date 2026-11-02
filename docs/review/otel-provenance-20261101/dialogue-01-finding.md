# Independent dialogue 01: actor meaning

Status: confirmed through the actual login route and independent SQLite reads.

The fresh client received HTTP 401; a subsequent protected request redirected to
login. SQLite contained no account with that submitted name before or after the
request, and no business rows changed. Both captured sign-in entry and error
events nevertheless claimed that name as their user actor. Native authentication
passed its rejection case; observation semantics failed. See
[the preserved reproduction](dialogue-01-actor-reproduction/result.json) and its
raw HTTP, store, event and source evidence. No application or SDK patch was made
for this reproduction. The earlier trial acceptance receipt is retained as
historical evidence, not as acceptance of this finding.

The business contract rejects an unknown account or wrong password. The generated
`Domain.authenticate` enters its observed sign-in span first, passing
`provenance(username)`. That helper labels the submitted username as an actor of
kind `user`, before checking whether the account exists or credentials match.

This conflates a submitted account name with a native authenticated principal.
Business authentication and observation accuracy must be reported separately.
The generic protocol describes an actor supplied by native authenticated state;
a login input should remain an input/claimed-account reference. Known absence of
an authenticated actor must be distinguishable from missing observation.

Framework remediation, preserving the existing state model and native execution:

- Permit typed provenance to be supplied by the existing selected event builder,
  so the completion can describe an identity or object that became known later.
- Represent an explicitly observed absent principal as `actor: null`; omission
  remains unknown/uncollected. Do not infer an actor from an account field.
- Extend the existing protected implementation-mapping contract with context
  fields compared to independent native facts, using the same mapping report.
- Add source guidance and negative cases for credentials rejected before identity
  exists, generated object IDs and observer-only metadata helper isolation.
- Keep dialogue 01 evidence; use a fresh conversation for the corrected workflow.
