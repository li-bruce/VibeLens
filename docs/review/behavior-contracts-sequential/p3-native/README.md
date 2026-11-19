# P3 native values, action boundaries and cross-model witnesses

Branch: `feat/behavior-contracts-sequential`, following P2 `c7845530`.
The phase status is recorded in the development ledger; final results are recorded
in `results.json` only after the complete regression and clean-export checks.
No independent conversation trial was started during this phase.

## Implemented scope

The pinned project bundle carries strict `bo-behavior-bindings/v1` declarations
for every selected variable, action and interaction. Independent source indexes
resolve documented functions and parameters. Actual native reads are compared
with selected captured fields using model, instance, invocation, attempt and
build identities, with a sample identity when repeated reads require it.

Actual completion, exception and cancellation/rollback declarations remain
distinct. A commit followed by an exception preserves both facts. Cross-model
reads, messages, resources, joins and transaction participants require their
declared correlation and causal evidence. The observer never executes the native
state machine or performs an application effect.

Python fixtures execute SQLite transactions and a detached queue worker. Node
fixtures execute asynchronous file-backed effects with separate observation
wiring. Negative cases retain wrong values, missing commits, unrelated invocation
ownership, missing handoffs and wrong builds. Existing mode-parity, HTTP error,
React/Vue entrypoint, inventory, native engine and business checks remain intact.

## Failure, repair and retest

| Evidence | Finding | Repair and subsequent check |
|---|---|---|
| `binding-before.log` | No native binding service existed | Implemented the strict source/capture/case boundary |
| `binding-first.log`, `completion-binding.log` | Initial tests expected a semantic diagnostic before stricter schema/case checks | Kept strict checks; corrected test expectations in the retest logs |
| `runtime-first.log` | Commit fixture compared the nested call identity with its parent action identity | Declared the actual parent key; `runtime-retest.log` |
| `runtime-lineage.log` | Fixture used an object in the existing scalar scope field | Preserved protocol validation; model identity now uses existing provenance, `runtime-lineage-retest.log` |
| `regression.json` | Windows sandbox denied Node realpath access to the temporary workspace | Same tests with host access, `host-retest.json`; no product check was relaxed |
| `ownership-first.log` | Additional final cases cover duplicated boundaries and witnesses from unrelated calls | All 43 focused tests passed |
| `delivery-verify-before-seal.log`, `delivery-architecture-before-seal.json` | Regenerated runtime no longer matched the old managed-file manifest | Reviewed canonical regeneration, sealed its hashes, then reran verification, acceptance and check |
| `full-verify.log` | The final archive validation found the same stale managed-file hashes | `archive-seal.json` and `archive-retest.log` retain the repair and all remaining release checks, including an independently executed observer-free package |
| `archive-review-helper-first.log` | The local retest helper omitted the already reviewed managed upgrade shim from its expected change list | Corrected the helper's list after inspecting the actual diff; original source, architecture and acceptance checks remain unchanged |

The managed-manifest repair does not approve business results. The subsequent
`delivery-acceptance.json` and `team-archive-acceptance.json` record the actual
three-command sequence. Source files in their configured application scope were
also compared byte-for-byte with the preceding commit before review.
The archive's final post-seal candidate is in `archive-retest.json`. The first
release run remains recorded as failed. Its source/runtime checks passed; the
targeted retest repeats the unchanged remaining archive steps after the metadata
repair. No application or framework executable source changed in that repair.

## Evidence boundaries

Mapping and domain validity are separate results: an accurately captured invalid
application value remains visible. Finite analysis bounds never clamp application
values. Concrete-value correspondence does not prove property-preserving
abstraction. Interaction witnesses do not establish distributed atomicity or
guaranteed message delivery. Those claims require their own explicit semantics.

These are implementation, CLI and real runtime fixture checks. Fresh conversations,
complete desktop usage and public product claims retain their later phase gates.
