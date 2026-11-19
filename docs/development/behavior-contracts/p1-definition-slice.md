# P1 implementation: definition checks

This records the first P1 slices on `feat/behavior-contracts-sequential`.
The subsequent [complete P1 contract reference](p1-contracts.md) supersedes the
remaining-work list below. Consult [progress.json](progress.json) for the tested
phase verdict; this historical slice does not define a smaller release scope.

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

## Collection, identity and rule reference extension

The second definition slice adds sets, sequences and maps of named domains.
Sets use unique arrays, sequences retain order and duplicates, and maps use unique
typed key/value entries. Nested domains are resolved once; cycles and unknown
dependencies fail. Lookup specifies its fallback and uses zero-based sequence
indices. Bounded quantifiers have typed local parameters and reject unbounded
domains. Their general evaluation belongs to the later analysis adapter.

Representation counts inspect keys and payloads as well as container length.
Large finite counts are reported without materializing the state space. A finite
set of values differs from a sequence of arbitrary length. A cap on live object
count does not make growing object identities finite; a fixed identity pool is
an explicit, model-qualified representation choice. These declarations never
change the application's limits or collected values.

`policy_ref` selects a canonical rule operation and binds exactly its reachable
inputs. Shared expressions retain their IDs. Native predicates stay opaque,
including a predicate whose name appears to describe a familiar operation. The
validator does not execute them or infer their truth. Input reads participate in
the action's existing read checks.

`definition_capabilities` is versioned, machine-readable parser/type-checker
capability data. Finite export and a model-checking runner remain unimplemented;
the domain cardinalities are not exporter admission or runtime verification.

Additional modules are `domain_size.py` (bounded cardinality arithmetic),
`policy_refs.py` (canonical dependency/input resolution), and `capabilities.py`
(implemented capability declaration). Scalar-only facts in discovery v2 remain
scalar: collection parameters/literals do not silently widen that schema.

## Remaining work recorded after the numeric slice

1. Formal-export admission data, supported predicate semantics and any required
   richer canonical fact mapping. The parser capabilities above do not establish
   these analysis/native capabilities.
2. Cross-model interactions, assumptions and refinement contracts with precise refs.
3. `business-discovery/v3` construction targets, independent modeling obligations,
   scoped review records and strict promotion into existing concepts.
4. `bo-project/v2` references and existing Python/JS reader integration.
5. Managed plan/apply/check migration with version snapshots, stale-writer and
   interrupted-write recovery, retaining existing checks and personal files.
6. Remaining A04–A10/A23/A29/A30 cases. Passing this slice's unit tests does not
   mark any whole A case or P1 complete.

These items are addressed by the [P1 completion candidate](p1-contracts.md), with
[separate failure and retest evidence](../../review/behavior-contracts-sequential/p1-completion/README.md).
P2 routing, P3 bindings, P4 iteration closure, P5 presentation, P6 analysis and P7
independent dialogue trials retain their own phase gates.
