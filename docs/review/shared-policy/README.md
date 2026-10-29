# Shared-policy implementation review

Branch: `feat/shared-policy-graph`, based on `9796ca3`. Implementation and regression evidence are separate from the independent file-sharing trials and their scripted conversations.

## Implemented

- A portable `bo-policy/v1` rule declaration, projected into the existing graph during initial design and each coding iteration.
- Reusable predicate definitions, separate argument-bound expressions, shared dependencies and operation roots.
- An optional independent Python evaluator with actual source bindings, fresh per-request facts, short circuit, unknown/error distinctions and isolated concurrent evaluations.
- Actual evaluation records and original graph events, including values, check identities and causal dependencies. A sidecar result cannot substitute for graph capture.
- Source signatures, current source bytes, exact projections, case coverage and recorded composition checks integrated with the existing completion gates.
- Rule replay that does not reuse a previous request's result for a skipped condition. Diagnostic identities remain available at advanced detail.

## Evidence

| Check | Current result | Record |
|---|---|---|
| Policy behavior, source, events, upgrades and repeated changes | 23 tests pass | [Log](checks/policy-tests-23.log) |
| Existing clarification gate | All 13 steps pass | [Log](checks/policy-clarification-env-retest.log) |
| Maintained-source syntax and lint | Pass | [Report](checks/policy-source-final.json) |
| Existing Python/JS/React/Vue fixture | Both modes, 18 cases pass | [Log](checks/policy-multilanguage-retest.log) |
| Installed delivery and archive examples | Inspect/verify/accept/check pass | [Review run](checks/policy-release-review-retest.log) |
| Complete repository release command | Pass, including observer-free packages | [Final run](checks/policy-release-final.log) |
| Clean Git export with frozen approvals | Both examples pass; no regeneration or reapproval | [Report](checks/policy-clean-export.json) |
| Independent design-to-run file-sharing trial | V1 passed; V2 in progress | `01a18332-cb51-7471-83f8-990d88886b9d` |

Failures, repairs and their scope are described in [the development record](../../development/policy-failures.md). The [first whole-release attempt](checks/policy-release-retest-2.log) and [first example review](checks/policy-release-review.log) remain available.

## Boundaries

The evaluator currently supports scalar string/Boolean/number inputs and acyclic Boolean composition. Native functions own relationship traversal and database reads. A shared definition does not cache an authorization grant between requests. A supplied fact revision identifies the application's read basis; it does not create transactional isolation.

The portable protocol can describe native results from other implementations. This branch supplies a Python evaluator and recorder; it does not claim a tested integration with every external policy engine or language. Mapping checks establish selected source/evidence consistency. Independent business cases still determine whether a predicate and its resulting effects satisfy the confirmed requirement.
