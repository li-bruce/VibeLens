# P3 native binding implementation

Branch: `feat/behavior-contracts-sequential`. Current phase state and executed
evidence are in [progress.json](progress.json). This document describes the
implemented interfaces; independent dialogue acceptance remains a P7 obligation.

## Data and authority

`bo-project/v2` pins the discovery and behavior artifacts. The canonical model
contains `behavior_bindings`; there is no second editable model registry. Project
loading checks its strict schema, references and semantic definition hash.
Source-free design remains valid without native bindings; implementation
inspection requires complete bindings when a behavior contract is configured.

The native state/activity engines and application permissions are unchanged.
Binding validation does not replace concept/native semantic checks. Observation
does not execute a business action, commit a transaction or repair a native value.

## Module map

Paths are relative to `skills/vibelens/scripts/bo_observer/`.

| Module | Responsibility |
|---|---|
| `schemas/behavior-bindings.schema.json` | Exact versioned source, capture, identity and case declaration |
| `behavior/binding_sources.py` | Resolve documented functions and fields against the independent owned-source scan |
| `behavior/bindings.py` | Expand every selected variable, action and interaction into binding obligations |
| `behavior/native_values.py` | Compare independently read values by declared qualified keys; diagnose domains separately |
| `behavior/native_lineage.py` | Resolve actual owning invocations and reject invalid explicit dependencies |
| `behavior/native_interactions.py` | Check shared reads, sends/receives, resources, joins and transaction boundaries |
| `behavior/native_runtime.py` | Combine protocol, lineage, native values and action-boundary results |
| `workflow/behavior_cli.py` | Read-only focused diagnosis using the existing sync configuration |
| `project_artifacts.py` | Read one pinned project/document bundle with repeated consistency checks |
| `workflow/sync_config.py` | Include pinned artifacts in candidate snapshots |
| `workflow/change_sync.py`, `workflow/sync_verify.py` | Add binding/runtime obligations to existing inspection and verification |

Pure binding/runtime services receive dictionaries and source indexes. They do
not import an application, crawl dependencies, start a server or launch a process.
The workflow layer owns file access and the independent source inventory.

## Evidence meaning

- Declaration completeness covers all contract variables/actions/interactions,
  including models hidden in the viewer. Source facts use actual indexed callable
  declarations and documented parameter names.
- Native values join by model, instance, invocation, attempt and build, plus a
  sample identity for repeated reads. Selected null and a missing field differ.
- Parameter, completion and interaction facts must belong to an actual action
  invocation. Event arrival order and equal payloads do not establish causality.
- A commit followed by an exception retains both physical boundaries. One event
  cannot count twice as two alternative exits.
- Joint reads require explicit revision/transaction evidence. Resource release
  retains its holder/acquisition. Join membership is checked against actual
  arrivals. These checks do not establish distributed transaction atomicity.
- Invalid application values remain visible. Finite analysis bounds are diagnostic
  only. Native correspondence does not imply property-preserving refinement.

Existing machine/policy, source inventory, mapping plan, capture health, mode
parity and independent business checks remain separate required gates. Scope
narrowing and semantic confirmation continue through the existing protected
workflow. P4 extends evidence invalidation and recall; it is not claimed by P3.

## Exercised implementations

The new fixtures execute actual Python SQLite transactions, Node asynchronous
file-backed effects and a detached Python queue worker. Their business functions
have no observer imports. The separate `bo_` wiring records selected values;
independent reads establish correspondence. Synthetic mutations remove commit,
handoff or worker evidence, alter selected values, and change identity/build.

See [native behavior guidance](../../../skills/vibelens/references/native-behavior.md)
for agent instructions. Tests, failures and retests are retained under
`docs/review/behavior-contracts-sequential/p3-native/`; no scripted fixture is
presented as an independent conversation trial.
