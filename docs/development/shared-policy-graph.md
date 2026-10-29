# Shared policy graph implementation

## User objective

Build a complete network of confirmed business rules alongside the business graph. Reuse stable condition identities across permissions, distinguish a predicate definition from its parameter bindings, connect concept-level rules to source-level implementations, and retain actual per-request evaluation evidence. Iterations must refresh the projection and reject missing or stale mappings.

## Work in progress

- Branch: `feat/shared-policy-graph`, isolated worktree based on `main` at `9796ca3`.
- Product/demo branch: `feat/file-sharing-demo` in the primary repository; it has unpublished work in progress.
- Independent product trial: `01a1830f-3fb2-73c1-b8aa-becffa72e8e3`, project `VibeLensTrials/file-sharing-demo-20261028`.
- Unassisted control: `01a18318-4fde-7633-a768-f0aff1cf25b5`, project `VibeLensTrials/file-sharing-control-20261028`.
- Complex reference: conversation `01a182ad-7d40-7e52-acb1-8b9b07d17022`; read-only candidate model in `task-permission-policy/`. It is a reference scenario, not an accepted production policy or a VibeLens implementation.

## Design decisions

1. Store a language-neutral `bo-policy/v1` declaration in the existing model. Project its expressions and cross-layer links into the same nodes/edges; do not add a disconnected analysis graph.
2. Separate reusable predicate definitions, argument-bound expression nodes, and per-request evaluations. Memoization is local to one evaluation and one supplied fact basis. Different arguments, requests, revisions and snapshots never share a result cache.
3. Validate identity, parameter types, operator arity, references, acyclicity, reachability, provenance, operation roots, source bindings and exact graph projection. Recursive relationship traversal belongs inside a bounded native reader; the expression DAG is not a universal representation of arbitrary recursive business flow.
4. Keep draft modeling usable before source exists. Bound runtime models require real source mappings and verification cases. Drafts cannot be accepted as implemented mappings.
5. Drive mode may use the optional native evaluator. Observe mode accepts actual native evidence without silently reevaluating business functions. Unknown facts, short-circuited expressions and execution errors remain distinguishable.
6. Extend existing scan/inspect/verify gates. Do not weaken checks for ordinary non-policy nodes. Recompute projections and source expectations on each iteration; preserve stable graph IDs and personal views.
7. Keep implementation mapping, state constraints, business-rule expectations and project checks separate.

## Acceptance sequence

- Strict malformed-definition and typing tests; shared subexpressions and distinct argument bindings.
- Fresh callbacks/snapshots, short circuit, errors, absent context, multiple concurrent checks and source changes.
- Exact projection and cross-layer relationships, missing-node/edge/parameter mutations, unchanged existing gates.
- Multiple changes to rule composition, predicate code and function location; stale or incomplete evidence must fail.
- Independent dialogue trial and compact file-sharing presentation.
- Paired coding comparison with a common task and scripted follow-ups, isolated directories, model/settings record, token telemetry by phase, and honest limitations of a small comparison.

## Research basis

- OpenFGA configuration language: https://openfga.dev/docs/configuration-language
- Cedar policy validation: https://docs.cedarpolicy.com/policies/validation.html
- Cedar authorization diagnostics: https://docs.cedarpolicy.com/auth/authorization.html

These references inform separation of policy, facts, evaluation and diagnostics. The new protocol does not claim to implement either external engine.

## Verified implementation checkpoint

On 2026-10-29 the complete `tools/verify.py` command passed, including the 23 policy tests, unchanged existing gates, real HTTP tests, native multi-language cases and observer-free package execution. Maintained-source lint and Skill validation passed. A clean staged Git export restored both frozen reviews and passed their checks without regeneration or reapproval. See [review evidence](../review/shared-policy/README.md). The paired file-sharing V1 has passed; its revocation iteration and product presentation are still being tested separately.
