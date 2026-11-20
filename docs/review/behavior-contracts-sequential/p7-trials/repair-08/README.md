# Technical feature coverage and review diagnostics

The Python trial submitted `requirement_changes` as a list. The contract expects
an object mapping requirement IDs to reasons. The trial must fix its authored
review while retaining this failure. The canonical `behavior.iteration` checker
also lacked an explicit type guard: `protected_errors` raised an AttributeError
at `reasons.get` instead of returning a strict, actionable review error. The
repair rejects malformed data without broadening allowed requirements.

Status: implemented; focused and complete regression passed; native P7 acceptance
remains open.
`review-first.log` retains the domain and review-consumer failures. `focused.log`
runs 33 related checks, including actual inspect/verify rejection without an
acceptance receipt. `source.json` records the source-format check.

A second independent static finding is in
`technical-business-classification.json`: a technical readiness endpoint was
authored as a business action with no corresponding confirmed business binding.
The trial is correcting its generator while preserving that source and API.
The trial then exposed eight failures: coverage requires every feature to have a
business projection, and enrichment promotes every `business_node` to a business
role. This includes readiness, native transition helpers and database access.
`classification-first.log` reproduces the generic gap with an actual scanned
readiness function. Node names alone cannot establish business meaning.

## Repair contract

- Validate the review object and maps before their consumers. Malformed reasons
  cannot authorize changes or crash inspection with an AttributeError.
- Preserve the existing `bo-implementation/v1` inventory. An omitted category
  retains business coverage. A technical feature explicitly declares
  `category: technical`, `implementation_node` and `classification_reason`.
- Technical features retain source, parameter, field and actual-runtime-case
  checks. They cannot carry a business owner/role or absorb a node already bound
  to the business model. The existing anti-weakening checks remain active.
- Enrichment uses the declared implementation owner without manufacturing a
  business role. Every scanned entrypoint must still have a valid disposition.
- Test both strict failure paths and a real technical return value; keep the
  malformed-review and classification failures separate from business failures.

The trial must upgrade through the maintained installer after canonical tests.
Installed runtime files are not edited to make its current inventory pass.

`diagnostic-installation.json` identifies the fresh 454-file installation used
for the Python integration retest. It contains the component-tested changes and
repair 07; it is not a final acceptance receipt. Shared adapter-provider guidance
also covers independent readers and on/off/fault subprocesses, following the
Node trial's mixed-provider finding.

## Native trial boundary

The fresh Python installation passed initial inspection with all 25 features
retained, including eight technical features. Its subsequent strict verification
rejected separate project wiring: announcement rules attached to the wrong
operation, an effect mapped to a commit-only point rather than a witnessed call,
and observations using an old build manifest. The trial is repairing those
bindings; this framework regression does not certify its runtime acceptance.

Both managed repository examples completed verify, accept and check with their
application source unchanged. Full regression passed 98 unittest suites and 1,124
reported tests, with one Windows file-symlink privilege skip. Pinned TLC 1.7.4 and
Java 17 were enabled. The complete gate receipts and clean frozen export are
indexed in `results.json`. P7 remains in progress until both native trials, their
iterations and independent Web/Timeline checks pass.
