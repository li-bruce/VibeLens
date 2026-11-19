# P1 contracts, review records and recoverable migration

Candidate branch: `feat/behavior-contracts-sequential`.
P1 passed the frozen-candidate regression and clean Git export. The exact source
fingerprints and logs are recorded in [results.json](results.json). The full runner
executed 917 unittest cases across 78 suites, plus its Node, integration, package,
installation and HTTP checks. These counts are executions, not unique features.

## Implementation

- Strict interaction, assumption, progress-property, recovery-initialization and
  refinement definitions use canonical state/policy identities.
- Finite-design admission reports invalid/unresolved/unsupported/eligible. No TLC
  process is launched; no property pass is claimed.
- Discovery V3 records construction targets outside the executable registry,
  independent modeling obligations, exact presentations and atomic promotion.
- Project V2 pins discovery/behavior/profile bytes. Python resolves full
  definitions; Node validates the transport/version boundary. Readers reject
  mixed revisions and incomplete migrations.
- The existing concept and upgrade commands expose these operations. Managed
  migration preserves source, models, IDs, confirmations and personal views.
  Explicit reference refresh validates new definitions without approving intent.

See [wire/API reference](../../../development/behavior-contracts/p1-contracts.md).

## Retained failures and repairs

| Evidence | Cause | Repair and retest |
|---|---|---|
| `boundaries-before.log` | A copied activity test fixture omitted the canonical completion guard | Corrected the fixture; retained a negative test proving removal is rejected. `boundaries-after.log`, `boundaries-final.log` |
| `admission-before.log` | The callback-free test fixture retained a crosslink to a removed guard | Updated the fixture's matching crosslink and all modeled transitions. Existing strict validator unchanged. `admission-after.log` |
| `construction-before.log` | Test used a noncanonical business-root ID and matched diagnostic codes against human messages | Corrected fixture ID and structured diagnostic assertions. `construction-after.log` |
| `migration-before.log` | Migration loader imported the wrong existing dialogue function name | Reused the actual `assess` entrypoint |
| `migration-after.log` | Windows sandbox blocked Node realpath on temporary fixture directories | Same tests under normal host permissions passed in `migration-host-retest.log`; path containment checks retained |
| `full-verify.log` | Additional source edits during a long check made managed example copies stale | Preserved the failure; synchronized through the existing managed updater and froze subsequent candidates |
| `target-routing-before.log` | Existing question scheduler attempted to resolve a pending construction target as a completed concept | Added target-aware scope selection and CLI confirmation checks. `target-routing-after.log` |
| `migration-race-before.log` | A concurrent project edit during plan construction could combine old model content with new input bytes | Snapshot the original basis and recheck all inputs before returning a plan. `migration-race-after.log` |
| `full-verify-locked.log` | The example ownership ledger still pinned its previous managed framework files | Reviewed canonical copies, recorded regeneration with the existing architecture guard, and retained all ownership checks |
| `delivery-verify.log`, `team-archive-verify.log` | Direct example commands omitted the shared JavaScript parser environment configured by the normal runner | Used the existing process-local adapter path; both `*-verify-configured.log` runs passed, followed by actual accept/check |

`full-verify-retest.log` was interrupted after the target-routing reproduction.
`full-verify-final.log` was interrupted after the migration-race reproduction.
Neither interrupted run is a pass. `full-verify-release.log` is the final candidate
run; its process exit and final marker must both pass before P1 closes. New frozen
example rounds were copied from actual accepted verification; previous frozen
rounds remain intact. The clean-export gate subsequently checks checkout bytes.

The migration tests also interrupt after the first canonical write and before the
journal exists, verify exact-byte rollback, reject external edits during recovery,
reject stale/altered plans, preserve legacy V1 without fabricated identity, check
explicit V2 reference refresh, and read the same migrated data in Python and Node.

## Evidence boundary

These are definition, migration and existing-product regression tests. Full A-case
acceptance spans later phases; it is not inferred from the unit-test count.
P2–P7 and fresh dialogue acceptance remain outside this P1 receipt.
