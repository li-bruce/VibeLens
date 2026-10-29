# Shared rule networks

Use this when the user's requested behavior includes permissions or other decisions. Keep the business overview small; expand its rules, actual inputs, functions and data readers on the same graph.

## Confirm the intended rules

Use natural questions to identify the actor, action, object, conditions, relevant relationships and when facts must be read. A counterexample clarifies an ambiguous answer; it does not add a new business policy. Preserve original answers in `discovery.sources`.

Store a `bo-policy/v1` draft as `discovery.policy`. Reuse expression IDs when the same bound condition feeds several operations. A reusable predicate definition is different: `same_identity(actor, owner)` and `same_identity(actor, parent_owner)` use one function but are distinct expressions. Do not merge them.

The declaration contains:

- `schema`, `revision`, `stage` (`draft` or `bound`).
- `inputs`: named `string`, `boolean` or `number` facts explicitly supplied by the application.
- `predicates`: reusable IDs, named parameter types, provenance, and real `source: {path, symbol}` once bound.
- `nodes`: stable IDs, `source_refs`, and `op`: `input`, `constant`, `predicate`, `all`, `any`, or `not`. Predicate `arguments` map parameter names to expression IDs. Logical `inputs` are ordered expression IDs.
- `operations`: permission/action IDs, Boolean `root`, `business_nodes`, independent verification `cases`, and `source_refs`.

The [example declaration](../assets/policy.example.json) includes shared ownership/session checks, file recipient grants, and a direct-parent task check with different bindings to the same predicate. The repository's `examples/policy-network/` also contains its native functions and behavioral tests. It is an example, not a policy to impose on a project.

```bash
python SKILL/scripts/bo_policy.py validate --root PROJECT --policy policy-draft.json --draft
```

`bo_design.py preview` and the design Web view project `discovery.policy` into the existing business graph. Keep business nodes as the initial overview and focus the relevant rule region for conversation confirmation. A draft has no executed facts and cannot pass the runtime mapping gate.

## Bind during coding

Copy confirmed identities into `model.policy` in the canonical project JSON; set `stage: bound` only after real source and cases exist. Implement using the user's architecture. The policy projection provides conceptual dependencies and source mappings; it does not embed executable function text.

```bash
python SKILL/scripts/bo_policy.py sync --root PROJECT
python SKILL/scripts/bo_policy.py check --root PROJECT
```

The existing `bo_sync scan/watch` refreshes the projection and emits internal maintenance tasks. The active coding AI reconciles changed source, bindings, cases and business meaning before its ordinary completion gate. This does not depend on a user manually maintaining the graph, and it does not wake unrelated conversations.

Do not weaken source checks for ordinary nodes. Only an exact validated policy projection can contain source-free logical composition. Its `maps` edges connect rule expressions to actual function nodes; its `guard` edges retain shared dependencies and business-action links. Static mappings do not prove runtime execution.

## Execute or observe

For Python drive mode, the optional `bo_observer.policy.runtime.evaluate` accepts the declaration, operation ID, allowlisted scalar inputs, actual predicate callables, `source_root`, and a current `fact_revision`. It validates callback signatures/source and rejects a loaded function that no longer matches its file. The application explicitly uses the returned value; the observer cannot authorize work.

There is one cache per evaluation. Reuse across permissions is a shared definition, not a reusable permission grant. New actor/resource/arguments/facts need a fresh `check_id`. A fact revision is a supplied read-basis identity; it does not prove a transaction snapshot. Read consistency remains the application's responsibility.

The native evaluator copies the selected scalar inputs at entry. Predicates must use the declared inputs and a consistent supplied read basis; move volatile database/time reads into explicit input acquisition. Function binding does not prove purity. A definition allows at most 4,096 expressions and 128 dependency levels; budget overflow is an error, not partial permission.

`all` and `any` short-circuit in declared order. Missing inputs produce unknown; skipped expressions have no invented value. Predicate failures are recorded as errors with unknown truth. Transport failure cannot change the business decision. External engines may use different semantics: preserve their actual trace and diagnostics instead of applying this evaluator to them.

In observe mode, emit the same `bo-policy-evaluation/v1` report from actual native decisions; never rerun functions just to populate the graph. Reports carry declaration hash/revision, check identity, fact basis, operation, selected inputs, actual function bindings, visited expression steps and diagnostics. The Python adapter can send these completed facts through `record_evaluation` and the existing bounded `BOProbe`; nodes and event identities are shared with the viewer. Deferred reporting records capture time, not a precise predicate-duration trace.

Arbitrary recursive relationship checks are not forced into an acyclic business model. A native predicate may perform bounded traversal and report its real reads through the existing data layer. Record incomplete context or traversal limits as unknown. Do not enumerate every database permission instance as a new definition.

## Check each iteration

Existing `change_sync inspect/verify` adds policy checks when configured:

1. Valid operators, argument names/types, references, acyclic expressions, reachable nodes, provenance and operation cases.
2. Exact generated nodes/edges, business anchors, source functions and parameter signatures.
3. Declaration/build/source freshness; per-request check identity and actual child dependencies.
4. Every configured case has a real evaluation and matching graph events, including values, arguments and causal links. A sidecar success report alone is insufficient.
5. Independent business assertions check whether the actual predicate truth and resulting effects satisfy the user's confirmed rule.

Report mapping and business outcomes separately. A correctly bound predicate can contain a business bug; an accurate observation should expose its actual arguments and result. Do not declare behavioral equivalence from an AST hash or a matching label.

Reference methods: [OpenFGA configuration language](https://openfga.dev/docs/configuration-language), [Cedar validation](https://docs.cedarpolicy.com/policies/validation.html), and [Cedar diagnostics](https://docs.cedarpolicy.com/auth/authorization.html). No generic OpenFGA/Cedar engine adapter is claimed by this module.
