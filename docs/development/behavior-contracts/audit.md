# Current implementation and design evidence

Baseline: `106fddb3`. Inspected on 2026-11-17. This is a source/document audit;
existing tests were inspected, not rerun as a new product acceptance exercise.

The 2026-11-18 [whole-plan modeling review](model-construction.md) adds current
source findings, four focused suite results and planned A29–A34 cases. The dated
2026-11-17 baseline and document-check counts below are retained as history.

## Existing capability, gap and reuse point

Paths below are relative to the repository. References describe the inspected
baseline; future changes must update this inventory rather than erase its history.

| Area | Present at baseline | Remaining gap / planned change |
|---|---|---|
| Concept models | [concepts/state.py](../../../skills/vibelens/scripts/bo_observer/concepts/state.py) validates initial states, transitions, guards and effects. Guards/effects can still rely on descriptive meaning. | Add explicit behavioral expressions and classify nonformalized terms; retain source-free drafts. |
| Multiple models | [bo_models.py](../../../skills/vibelens/scripts/bo_models.py) and [model networks](../../../skills/vibelens/references/model-networks.md) register independent models and qualify instances. | Add precise interaction, shared-state and atomicity contracts; registration alone supplies none of these. |
| Values | [bo_contracts.py](../../../skills/vibelens/scripts/bo_contracts.py), `validate_value_spec`, accepts typed values and optional numeric bounds. | Finiteness also needs instance limits, string alphabets/abstractions, collection sizes, queue bounds, clocks and counters. |
| Native execution | [Python executor](../../../skills/vibelens/scripts/bo_observer/adapters/python/bo_executor.py) and existing native adapters execute a flat subset. | Preserve the capability boundary. External/native engines need explicit contracts and witnesses, not silent flattening. |
| Rules | [policy/definition.py](../../../skills/vibelens/scripts/bo_observer/policy/definition.py) and [shared-policy.md](../../../skills/vibelens/references/shared-policy.md) provide a reusable expression DAG and native predicate bindings. | An arbitrary bound predicate has no automatically known formal meaning. Reuse supported operators; require evidence or mark unsupported. |
| Resources and joins | [execution_contract.py](../../../skills/vibelens/scripts/execution_contract.py) checks the integrated activity configuration and actual journal. [worknet_contract.py](../../../skills/vibelens/scripts/bo_observer/graph/worknet_contract.py) checks selected bounded P/T declarations/journals. | Retain these checks; they do not explore all schedules or establish general liveness. Avoid a second authoritative Petri layer. |
| Questions | [requirements_dialogue.py](../../../skills/vibelens/scripts/bo_observer/workflow/requirements_dialogue.py) implements priority, dependencies, blocking, answer sources and `ready[:3]`. | Three is a per-round display budget. Add explicit issue owner, decision authority, stage, evidence expiry and participation preference. |
| Iteration | [iteration_recall.py](../../../skills/vibelens/scripts/bo_observer/workflow/iteration_recall.py), [bo_sync.py](../../../skills/vibelens/scripts/bo_observer/workflow/bo_sync.py) and [change_sync.py](../../../skills/vibelens/scripts/bo_observer/workflow/change_sync.py) restore, inventory, compare and gate changes. | Restore behavior-contract assumptions and impact closure. Detect an omitted batch and stale analysis receipts; host integration must invoke the workflow. |
| Model assertions | `change_sync.py:structural_errors` evaluates existing `acceptance.model_checks` through path lookup and expected-value digests. | These are structural assertions, not TLC-style model checking. Keep backward compatibility and name new results unambiguously. |
| Runtime capture | [observation_requirements.py](../../../skills/vibelens/scripts/bo_observer/workflow/observation_requirements.py), [mapping_contract.py](../../../skills/vibelens/scripts/bo_observer/workflow/mapping_contract.py), telemetry and lifecycle adapters check configured observations. | Extend obligations to modeled message handoff, state reads and effect-completion boundaries; missing capture never becomes a model fact. |
| Verification | [validation-rules.md](../../../skills/vibelens/references/validation-rules.md) already separates mapping, state, business and project checks and discusses fairness assumptions. | Add machine-readable assumption/property coverage and model-analysis results without collapsing existing categories. |
| JSON | [schemas/](../../../skills/vibelens/scripts/bo_observer/schemas/) includes strict project/discovery envelopes and semantic validators. | Extend versioned protocols and semantic validators together. JSON Schema alone does not check cross-reference meaning or code correspondence. |
| Ownership | [integration-boundary.md](../../../skills/vibelens/references/integration-boundary.md) separates the installed tool from project-native definitions/adapters. | All new analysis code and dependencies remain tool-owned. Application changes are declarations, native implementation and isolated wiring. |
| Viewer | [source guide](../../source-guide.en.md) documents shared identity, projected relations, concept capture, 2D/3D and Timeline. | Add on-demand contract/evidence details and a separate model-trace mode. Preserve camera, layout, filtering and recorded lifetimes. |
| Public story | [homepage](../../site/index.html), [home messages](../../site/home-messages.mjs), demo and frozen case exports already exist. | Describe the new confirmed capability only after acceptance; source all screenshots from the accepted candidate. |

No maintained TLA+/TLC export or runner implementation was found in the inspected
Skill scripts, references and tests. Existing prose about fairness is not such an
implementation. No current runtime or portable-executor expansion is claimed here.

## Source discovery boundary

Inspection focused on tracked/maintained source and selected documents. Dependency
trees, vendored assets, caches and trial runtime data are not application semantics.
One early search included the nested TypeScript dependency; the corrected search
excluded `**/node_modules/**` and `**/__pycache__/**`. No dependency hit is used as
evidence of VibeLens feature support.

Historical development plans can contain stale planned items. Current source,
capabilities and executable contracts take precedence when determining what to reuse.

## Primary references and limited use

| Reference | Borrowed idea | Boundary |
|---|---|---|
| [Lamport et al., Specifying and Verifying Systems With TLA+](https://lamport.azurewebsites.net/pubs/spec-and-verifying.pdf) | Initial states, actions, behavior and finite model instances | A translated specification is not automatically a verified implementation. |
| [Lamport, Specifying Systems, section 5.8](https://lamport.azurewebsites.net/tla/book-02-08-08.pdf) | Refinement mappings and internal steps that leave abstract state unchanged | An ordinary graph mapping edge is not a refinement proof. |
| [TLC model overview](https://tla.msr-inria.inria.fr/tlatoolbox/doc/model/overview-page.html) | Separate behavior, constants, invariants, temporal properties and deadlock checks | An intentionally terminated system is different from unexpected deadlock. |
| [GitHub Spec Kit](https://github.com/github/spec-kit) | Carry a specification through planning, implementation and verification | Reuse the workflow principle; do not force another toolkit or its commands into every project. |
| [Hypothesis stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html) | Generate sequences of actions and values and minimize failures | Generated tests exercise examples; they are not exhaustive model exploration. |

References checked on 2026-11-17. The protocol and module design in this directory
are VibeLens proposals derived from the user's requirements and this audit.

## Planning-delivery checks

The planning delivery checks local links, Markdown JSON examples, requirement-to-
phase/test coverage, unchanged application/runtime files and `git diff --check`.
Its results are recorded after validation in this document. Product acceptance,
TLC runs, independent dialogue trials, screenshots and publication belong to the
implementation phases and have not occurred in this planning delivery.

Planning validation completed on 2026-11-17:

| Check | Result |
|---|---|
| Planning documents and navigation | 7 documents; English/Chinese source-guide links added |
| Repository-local links in the plan | 45 resolved targets; no missing/escaping paths |
| Illustrative JSON | 2 examples parse; this does not validate a future schema or its semantics |
| Listed existing command files | 21 paths exist; commands were not executed as product acceptance |
| Requirement/phase/case links | 12 BC requirements, ordered P0–P7, 28 unique A cases; all cases linked |
| Whitespace and changed-file scope | `git diff --check`; documentation changes only |

The local document check used Node.js 20.19.6 and retained its report under
`.validation/behavior-contracts-plan/`. The optional planning-session recovery
helper could not initialize the local Miniforge Python location; repository state
and relevant conversation context were recovered through direct reads instead.
No product check is reported as passing on the basis of that helper or this audit.
