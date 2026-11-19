# P1 implementation: scalar definition checks

This is the first P1 slice on `feat/behavior-contracts-sequential`. P1 remains in
progress. The full [protocol proposal](protocol.md) and its acceptance obligations
remain the target; this slice does not replace them with a smaller release scope.

## Implemented wire format

The branch's strict `bo-behavior/v1` schema currently accepts project identity,
selected canonical model/object IDs, explicit unresolved scope and exclusions,
scalar domains, state/fact variables, initial predicates, actions and properties.
It reuses `business-discovery/v2` without migrating or rewriting it.

The runnable pair is [scalar.behavior.json](../../../tests/fixtures/behavior-contracts/scalar.behavior.json)
and [forest.discovery.json](../../../tests/fixtures/behavior-contracts/forest.discovery.json).
Both are evaluator-authored fixtures, not production requirements.

```powershell
python skills/vibelens/scripts/bo_behavior.py validate --root . --contract tests/fixtures/behavior-contracts/scalar.behavior.json --discovery tests/fixtures/behavior-contracts/forest.discovery.json
```

The command is read-only. Exit 0 means this definition is structurally/semantically
valid within the implemented subset. It does not confirm intent, bind source,
run an application, close an iteration or invoke a model checker. Those fields
remain `not_checked` / `not_run` in the result. Existing gates are unchanged.

## Ownership and expression semantics

- A state variable references its exact `state-model:<id>`; a fact references its
  canonical fact and object. Equal labels in separate models remain separate.
- An action partitions every selected variable into `writes` and `unchanged`.
  Typed parameters and all explicit or canonical transition reads are checked.
- State writes derive from `transition_ref`. An action cannot redeclare the
  transition's destination in `updates`. The normalized result retains its source,
  target, guards and priority from the original definition. Fact updates remain
  typed expressions reading the same pre-state.
- Initial state values derive from their canonical state models. The contract's
  initial predicate adds constraints. Definite contradictions fail; unknown fact
  values remain unresolved. General satisfiability is not solved by this check.
- Supported expressions are typed literals, before/after variables, parameters,
  Boolean combinations, equality, integer ordering and integer addition/subtraction.
  After-state reads are restricted to transition constraints. State invariants
  apply to the selected state; transition properties need a nonempty action set.
- Bounds carry `application_limit`, `analysis_bound` or `abstraction`. Their origin
  is never applied to the application's settings. Finite-domain cardinalities are
  representation metadata, not a finite-system or exhaustive-verification claim.
- Enum identity preserves JSON types. Floating-point enum identities are rejected
  because producers do not consistently preserve lexical `1` versus `1.0` identity.
  Number domains are valid declarations but unsupported for finite analysis.

Diagnostics have `code`, JSON-pointer `path` and `message`. Invalid original
state/rule models retain the existing validator's failure. An unsupported scalar
mapping is reported as `unsupported`; it is never flattened silently.

## Module boundaries

| Module | Owns |
|---|---|
| `behavior/contract.py` | Validation order and scoped result |
| `behavior/references.py` | Canonical identity, owner and variable references |
| `behavior/domains.py` | Scalar domain types and representation bounds |
| `behavior/expressions.py` | Type/read analysis and limited initial consistency |
| `behavior/actions.py` | Frame conditions and canonical transition projection |
| `behavior/diagnostics.py` | Structured failures |
| `workflow/behavior_cli.py` | Project-contained JSON input and command output |

The semantic modules do not import a native executor, browser, application package
or external analysis tool. New modules are copied to fixtures only through the
existing managed synchronization command.

## Still required to complete P1

1. Collection/identity domains, supported policy references and capability data.
2. Cross-model interactions, assumptions and refinement contracts with precise refs.
3. `business-discovery/v3` construction targets, independent modeling obligations,
   scoped review records and strict promotion into existing concepts.
4. `bo-project/v2` references and existing Python/JS reader integration.
5. Managed plan/apply/check migration with version snapshots, stale-writer and
   interrupted-write recovery, retaining existing checks and personal files.
6. Remaining A04–A10/A23/A29/A30 cases. Passing this slice's unit tests does not
   mark any whole A case or P1 complete.

P2 routing, P3 bindings, P4 iteration closure, P5 presentation, P6 analysis and P7
independent dialogue trials remain pending until their prerequisites are complete.
