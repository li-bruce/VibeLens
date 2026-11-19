# P0 — Frozen baseline

Status: complete. No production semantics changed in this phase.

The unchanged mandatory `tools/verify.py` baseline finished with exit 0, including
70 unittest suites / 774 test executions, JavaScript checks, real HTTP scenarios,
installation and observer-free business exports. The source gate passed for 188
maintained Python and 136 JavaScript files. Six new ledger tests and three forest
tests passed separately and are now added to the main runner. Python modes passed
6/6. Counts include repeated integration executions and are not unique feature
coverage. See [results.json](results.json) for commands/scopes and log hashes.

## Reproduction

The development ledger pins 28 Git blobs at the planning commit, including the
original release runner, representative tests, schemas, sample declaration and
approved plan. Read a frozen file with `git show a8f569d7:<path>`. The checker
validates these references; future code changes do not overwrite the baseline.

Run `python tools/check_behavior_plan.py` and
`python tests/test_behavior_plan.py` for requirement/case coverage and stage order.
These check the engineering ledger only. Existing product checks remain required.

## Fixture ownership

| Fixture / check | Preserved responsibility |
|---|---|
| `test_concept_models.py`, `test_concept_workflow.py` | Source-free models, immutable confirmation, exact native bindings |
| `test_model_networks.py` | Independent model identities even with the same local state and instance names; real capture |
| `test_policy_network.py` | Shared declarations, separate arguments and invocations, independent rules and effects |
| `test_concept_models.py` activity cases | Integrated native activity/resource/join declarations and actual completion |
| `test_api_observation_projection.py`, `test_telemetry.py` | Actual API ownership, response facts and incomplete coverage |
| `test_stategraph_module.py`, Python modes and multilingual tests | Application-owned state; drive/observe cannot disable observation checks |
| `test_view_continuity.mjs`, `test_trace_lifecycles.mjs` | Persistent personal views and actual invocation lifetimes |
| `test_behavior_baseline.py` and its synthetic forest fixture | Independent profile route, two state owners, shared rule and deliberately omitted sharing edge |

Production ownership remains unchanged: discovery owns intended meaning; native
declarations and application code own execution; external observation owns recorded
facts and projections; personal views own layout. New behavior services must refer
to those definitions. Analysis and rendering must not become business authorities.

## Findings retained before development

1. The sandbox run stops at the existing distribution test's Windows junction
   setup. The failing command is `cmd /c mklink /J`; no test assertion was weakened.
   The same unchanged test passes outside the sandbox. The previously reported
   concept-workflow junction case also passes outside the sandbox (23/23).
2. The existing network review reports disconnected components, including valid
   independent capabilities. It cannot determine from topology alone whether the
   user intended a missing connection. The new frozen fixture retains both cases.
   Source-backed construction obligations in P1/P2 must address that distinction.
3. The first fixture-building attempt was rejected for a missing operation
   applicability record. The fixture was completed with explicit state/rule
   applicability. The production validator was left unchanged.
4. The local interpreter prints a Miniforge location warning but runs the tests.
   Exact interpreter and installed-copy fingerprints are in `environment.json`.

Raw restart logs are isolated under `.validation/behavior-sequential/p0/`.
Earlier `.validation/guided-*` results belong to the abandoned implementation and
are excluded. Condensed text logs are retained beside `results.json`; large JSON
outputs remain in the hashed raw logs. Optional database services and full desktop
browser acceptance are later-stage checks, not claimed by this baseline run.
