# First-party source scope integration

This change follows the user's explicit source-ownership decision. Human-authored
and AI-generated application source belongs to the analyzed project. Installed
dependencies and classified generated records do not. The earlier performance
diagnosis describes the previous policy; this is a deliberate scope definition,
not a reinterpretation of ordinary exclusions.

## Shared boundary

`bo_observer/source_scope.py` now supplies the same policy to the source inventory,
AST entrypoint, code/API index, project tree, documentation discovery and source
capture. Existing `source_scope.exclude` entries remain inspected for hidden
application methods and routes. New literal `prune` boundaries require a
`dependency` or `artifact` category and a reason. Diagnostics report encountered
prefixes without claiming how many files an unvisited subtree contains.

Full stategraph acceptance retains the original requirement to include `.` in
its source roots. Explicit nested roots may reopen a first-party subtree inside
a default or declared storage boundary. Narrower standalone code inspections
remain available. Arbitrary `data`, `modules`, `runtime` and `review` directories
are not excluded by name; the default review-output boundary is exactly
`review/runtime`.

Executable source bindings, feature parameters, policy predicates, telemetry
registrations and explicit AST inputs cannot point into classified storage or
outside their declared roots. Hash-only evidence and watched configuration
remain byte-checked. `.gitignore` is a hashed advisory input; its patterns do not
silently exclude first-party code. A changed ignore file invalidates the current
candidate and requests scope review.

## Retained failures and repairs

The first existing CodeGraph regression run found that creating the observer's
own `.stategraph` directory changed saved-versus-current `scope` diagnostics.
The strict saved-graph check remained enabled. Semantic identity now includes
policy, advisory input hashes and actual owned-source facts, while encountered
pruned-prefix diagnostics are excluded from that comparison.

A second unchanged regression, `test_limits_are_explicit_and_sources_revision_bound`,
then caught mutation of an earlier returned graph when a later view refreshed
those diagnostics. The fix copies the diagnostic scope overlay instead of
mutating the semantic cache or a previously returned graph. The maintenance
source identity follows the same diagnostic distinction.

The original 31 CodeGraph tests pass after these repairs. A separate sandbox run
of the expanded scope suite could not create a Windows junction (`mklink /J`
returned exit 1); this environment failure is distinct from the host run that
exercised actual junction rejection. The engineering fixture that narrowed its
roots to `web` while retaining a `worker.py` executable binding required a
fixture migration. The fail-closed binding check is retained.

## Focused verification

- Existing CodeGraph suite: 31 passed after diagnostic and immutability fixes.
- Source documentation: 18 passed.
- API snapshot and exact observation projection: 20 passed.
- Existing implementation coverage: 17 passed, including the original project
  root requirement restored byte-for-byte.
- Syntax, Ruff, ESLint, Black and Prettier: passed for 136 maintained Python and
  98 JavaScript modules. Receipt:
  [source-scope-source-quality-01.json](source-scope-source-quality-01.json).
- The 1,500-file engineering benchmark retained its incremental assertions:
  one changed file parsed and 1,506 unchanged source units reused. Its separate
  narrow-root fixture migration is recorded above.

These are focused framework results. Managed-example acceptance, publication
and a fresh user conversation are separate release gates owned by the main
task; this note does not assert their completion.
