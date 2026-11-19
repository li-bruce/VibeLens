# P4 iteration closure

Branch `feat/behavior-contracts-sequential`, following P3 `8afe4568`.
No independent conversation trial was started. Phase status follows executed
results in `results.json`, not this description.

Implementation: [module ownership and boundaries](../../../development/behavior-contracts/p4-iteration-evidence.md).
Tests cover semantic dependency changes, unaffected models, display-only reuse,
native source/tool invalidation, per-record request basis, missing captures and
original gate preservation. Actual SQLite reads supply value and boundary evidence.

| Retained log | Finding and repair |
|---|---|
| `evidence-before.log` | Missing evidence service, followed by its implementation |
| `evidence-first.log` | Shared-rule fixture had an invalid unused input; retained strict validation and corrected the fixture |
| `evidence-retest-scoped.log` | Confirmed only actual dependent consumers invalidate |
| `workflow-first.log` | Test called the existing coordinator with the wrong signature; corrected the test |
| `workflow-retest.log` | Actual coordinator and durable recall integration passed |
| `regression-final.log` | Windows sandbox denied a directory-junction test; product checks unchanged |
| `regression-host.log` | Same 236 tests passed with host filesystem access |
| `machine-label-before.log` | Native state display labels incorrectly expired evidence; normalized only documented display envelopes, retaining exact state values and transition semantics |
| `machine-label-retest.log` | State labels preserve evidence; changing the actual state domain still invalidates it |

Scoped evidence reuse cannot approve a new candidate. Required gaps still fail the
original verifier and acceptance. Analysis receipts here test dependency logic;
actual TLC execution and its trusted artifact reader are deferred to P6. Final
independent user conversations and end-to-end visual acceptance remain in P7.
