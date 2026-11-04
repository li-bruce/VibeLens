# Business, state and rule models before implementation

Status: proposed design, not implemented or runtime-validated.

This statement records the inspected baseline. The subsequent implementation
and its acceptance evidence are tracked in the
[implementation report](../review/concept-models-20261104/README.md).

Inspected baseline: `main`, `3a43294d84d38bda4bcd7670a0b67e9985fa3ed5`.

## Purpose and correction

Business, state and rule models are peer conceptual inputs to development. Each needs its own complete, inspectable graph and validation semantics. They share typed references in one network; neither a common canvas nor a business overview replaces the state machine or decision model.

The preceding [layer assessment](../assessment/2026-11-04-layers/README.md) proposed simpler default navigation. That concerns display planes, not removal or subordination of conceptual models. This proposal makes that distinction explicit: the developer can inspect business, states, rules or their connections independently from the beginning, then follow all of them into implementation and runtime evidence.

These models guide confirmed behavior; algorithms, data integrity, architectural boundaries and external integration still need implementation design. The Skill must not invent new business policy to make a model look complete.

## Verified current behavior

| Area | Current fact | Gap |
| --- | --- | --- |
| Initial conversation | [SKILL step 1](../../skills/vibelens/SKILL.md#L25) explicitly requires a business diagram and confirmation. | State understanding is mentioned but has no equivalent structured draft gate. |
| Rule draft | [SKILL:37](../../skills/vibelens/SKILL.md#L37), [policy draft validation](../../skills/vibelens/scripts/bo_observer/policy/definition.py#L74) and [design projection](../../skills/vibelens/scripts/bo_observer/web/bo_design.py#L198) support rules before source functions exist. | Draft-to-bound discovery checks preserve operation IDs, not all confirmed logic and argument meaning. |
| State draft | Discovery permits generic state nodes. | [Design view:183](../../skills/vibelens/scripts/bo_observer/web/bo_design.py#L183) constructs an empty machine. Generic network nodes do not establish initial state, event payload, transition, hierarchy or guard semantics. |
| Readiness | [requirements_dialogue.py:368](../../skills/vibelens/scripts/bo_observer/workflow/requirements_dialogue.py#L368) checks the existing blocking decisions and malformed records. | Omitting a state-model scope can leave no blocking decision to detect. |
| Rule confirmation | Source references, question/answer history and draft projection exist. | [Focus:84](../../skills/vibelens/scripts/bo_observer/web/bo_design.py#L84) and decision affected-ID resolution do not uniformly resolve projected draft rule IDs. |
| Real state contract | [SKILL:49](../../skills/vibelens/SKILL.md#L49) introduces the formal machine; [validate_chart](../../skills/vibelens/scripts/bo_contracts.py#L567) strictly checks values, events, transitions, guards, engine equality and execution structure. | These checks come after the present conceptual draft stage and do not establish an earlier user-confirmed state model. |
| Iteration | Recall, immutable change baselines, source inventory, mapping, native verification and acceptance exist. | Existing decision-history protection is not a semantic baseline for all three conceptual graphs. A changed build hash is not authorization to change confirmed behavior. |

The rule gap has a precise source-level example. [Discovery comparison](../../skills/vibelens/scripts/bo_observer/workflow/requirements_dialogue.py#L107) checks that operation IDs remain present. A bound model can retain that ID while changing `all(A,B)` to `any(A,B)`; this comparison alone does not detect the change. Independent later cases may catch it. This is a static control-flow finding, not a newly executed end-to-end reproduction.

## Basis and limits of the references

| Method | Useful principle | Application here |
| --- | --- | --- |
| [OMG Model Driven Architecture](https://www.omg.org/mda/faq_mda.htm) | Separate platform-independent behavior from platform-specific realization. | Establish state, decision and business contracts before Python/Node/framework bindings. Do not claim MDA conformance or require its entire toolchain. |
| [W3C SCXML](https://www.w3.org/TR/scxml/) | Events, conditions, transitions, nested/parallel states and execution order have formal meaning. | A state-looking node is insufficient. Preserve explicit transition and active-configuration semantics and supported-engine capabilities. |
| [OMG DMN](https://www.omg.org/dmn/) | Decision models complement process/case models and can have reusable dependencies. | Build a complete decision graph rather than an unexplained permission diamond inside a flow. This does not imply current DMN/FEEL support. |
| [GitHub Spec Kit](https://github.com/github/spec-kit/blob/main/spec-driven.md) | Carry specifications through planning and implementation. | Use persistent, scoped artifacts and explicit completion gates. Do not adopt its claims about generation as proof that implementation is correct. |
| [Hypothesis stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html) | Generate action sequences and check invariants against the implementation. | Add sequence tests beyond isolated API examples, with independent expectations. Bounded testing is not a proof over all possible executions. |

No single method guarantees that an AI understood everything. VibeLens should preserve the user's confirmed meaning and expose the actual implementation, deviations and missing evidence.

## Three peer models

| Model | Required meaning within the confirmed scope | What it does not replace |
| --- | --- | --- |
| Business network | Actors, objects, trigger, actions, effects and confirmed alternative routes; source dialogue; required scenarios. | A machine, executable decision logic or every technical call. |
| State model | State-owning object and identity scope; typed context; initial and possible states; events and payloads; transitions, ordered selection, logical guards and effects; relevant hierarchy, activities, waits, resources and joins. | All object instances in one global enum, or generic function entry/return lifecycle. |
| Rule model | Applicable operations; selected typed facts and their scope/read basis; reusable predicates; bound expression instances; combination semantics; decisions and independent examples. | One predicate per function, enumerated authorization instances, or unrestricted recursive inference. |

The current `bo-policy/v1` operation roots are Boolean. Its existing DAG is suitable for permission and Boolean eligibility checks. Numeric or multi-valued decision outputs need an explicit typed extension or native-engine adapter; describing the graph as a decision model does not implement the complete DMN language.

An operation may read state without changing it. A transition may occur through a background event. A shared rule can govern several operations and transitions. The graphs must therefore support complete views and many-to-many references, rather than treating rules and states as children owned by one business node.

The state model should be organized by state-owning object. Several instances of one model have distinct object identities; several object types may need separate machines. Do not flatten their Cartesian product into one software-wide state enum. A machine catalog can reference existing native definitions; preserving the current single `model.machine` as a compatible primary definition does not by itself implement multi-machine execution or observation. Additional native-machine adapters need explicit capability checks and tests.

### Example using file sharing

For an illustrative recipient grant, identify the object by `(file_id, recipient_id)`. The model can distinguish no current grant from a current grant, with share/revoke events, if that matches the confirmed application semantics. Download reads the grant without necessarily changing it. A missing grant row alone does not prove a historical revocation.

The business model names share, revoke and download. The state model defines the grant transitions. The rule model defines who may perform those actions and which current facts it reads. Shared identity/ownership checks can feed more than one decision. Actual rules must come from the user's confirmed scope; this example is not a new prescribed authorization policy.

## Typed cross-model contract

| Reference | Meaning |
| --- | --- |
| Action requests event | A business operation requests a typed state event. It does not guarantee that the transition occurs. |
| Transition guarded by decision | The specified decision controls eligibility for that transition. Link the actual native guard later. |
| Decision reads state/fact | Identify the object, field/type and read timing or supplied basis. |
| Transition has effect | Name the confirmed logical effect and its completion boundary. |
| Concept implemented by source | Bind one or several real declarations, not a guessed name. |
| Observation refers to concept | Bind actual command, object, invocation or check evidence to its declaration revision. |

State loops are legal. Rule expression dependencies remain acyclic within the supported DAG. Shared resources and synchronization use their own constraints. The union graph is not required to be a DAG or a single containment tree.

All referenced IDs must resolve. Operations should declare whether they change state, only read it or have no applicable state semantics. Likewise record which decisions apply or why the current scope has none. This explicit applicability check must catch omitted modeling work without inventing missing business behavior.

## One logical source, phase-aware artifacts

Extend the existing discovery flow instead of asking the user to maintain several new documents. A future versioned discovery envelope can keep `networks`, an independent state-model section, `policy`, typed cross-links, scope/applicability, expectations and confirmation records. Names and exact schema revision must be finalized during implementation; adding unknown fields today will not make the current tools understand them.

Separate four records:

1. Working conceptual definitions: the editable source for current intent.
2. Confirmed semantic snapshot: immutable scope, semantic digest and actual dialogue answer/source, not a second editable model.
3. Bound implementation projection: the same stable concepts plus native declarations, source, capture and case bindings.
4. Runtime facts: actual observations qualified by model/build/object/call/check identity.

Proposed readiness states are draft, confirmed, bound and verified. These are design-process statuses, not new application lifecycle states. The current policy protocol supports `draft` and `bound`; confirmation can be recorded in the surrounding contract without silently treating a new literal as supported.

Draft validation permits missing source and exposes unresolved meaning. Confirmed readiness requires the applicable semantic scope, references and material ambiguities to be resolved. Binding adds real source without changing confirmed semantics. Verification requires the existing native and observation checks. Drafts must never load as executable or accepted runtime definitions.

## Conversation and implementation flow

1. Read existing requirements, decisions and code where present. Choose drive or observe explicitly once. Identify the current feature scope and source ownership.
2. Extract the initial business network and identify state-owning objects and decision sites from the same current description.
3. Construct the relevant state and rule graphs alongside it. Use short, natural questions only for meaning-changing ambiguity. Confirmed answers are reused; a fixed questionnaire is unnecessary.
4. Render each relevant graph independently and their cross-links from the same assembled design model. Show the currently discussed region in the conversation and provide the verified Web address. The page remains a viewer; answers stay in the conversation. A truncated local preview retains omitted conditions as boundaries and cannot silently confirm the complete network.
5. Save explicit scope-bound confirmation. Permit unrelated technical preparation while a question remains open; block implementation of the affected unconfirmed behavior. Do not require the complete future product to be specified before any feature starts.
6. Produce independent examples and implementation obligations: required input/decision/effect/state evidence, interfaces, source bindings and tests. Hand these to the user's chosen coding workflow.
7. During coding, bind the native state module, rule checks, source and selected probes. No fake function/API nodes or dummy captured values are needed before code exists.
8. Before accepting each batch, compare confirmed semantics, bound declarations, independent source inventory, actual execution and independent outcomes. Repair code or mappings according to the evidence, rather than rewriting the specification to match the result.

The three graphs are co-designed iteratively, not rigid sequential waterfalls. Each should be individually meaningful before the affected behavior is implemented.

## Drive and observe remain separate

| Concern | Drive | Observe |
| --- | --- | --- |
| State execution | The application-native executor consumes the bound declaration. | Application logic remains authoritative; bindings read its actual state and transitions. |
| Rule execution | A supported native evaluator may implement the bound decision contract. | Observe the actual native check or external engine; do not evaluate it again for display. |
| Development guidance | Confirmed graphs constrain implementation tasks and cases. | Confirmed graphs also guide implementation, without requiring an executor rewrite. |
| External observer | Collects and validates evidence; does not authorize, transition or rerun business work. | The same boundary. |

The isolated state/rule implementation module remains identifiable in source. Business execution must survive the observation service being unavailable. Hiding the Web UI does not delete state or decision execution.

The current portable FSM supports a strict flat subset, and the Python reference activity checker supports a bounded set of activities/resources/joins. A declaration needing unsupported hierarchy, repeated dynamic activity instances or cross-process resource pools must fail capability binding or use a tested adapter. Do not silently flatten or omit it.

Concurrency semantics already relevant to the project belong in the state/activity contract: active configurations, actual resource scope/capacity/holders, enabling, acquisition/release and join prerequisites. Apply Petri-style resource and synchronization ideas there, as described in the existing [integrated execution contract](../../skills/vibelens/references/integrated-execution.md); do not create a second Petri authority.

## Confirmation-aware iteration

Keep concept confirmation separate from current-build acceptance. The existing recall should additionally restore affected concept IDs, confirmed semantic revision, cross-model dependencies, pending questions and obligations. The user sees the affected graph and relevant question, not internal artifact maintenance.

Semantic comparison must cover states, event payloads, transition source/target/order, guards, effects, rule roots/operators/arguments, input meaning/read basis and typed cross-links. Preserve order where short-circuiting or transition priority makes it meaningful. Display names and source line changes are not semantic identity.

- New policy, changed action meaning, rule `all` to `any`, changed object scope, transition target or guard timing requires explicit confirmation of the affected scope.
- File moves, source decomposition, equivalent implementation refactoring and probe transport changes normally require automatic rebinding and verification, not another business question.
- Resolve uncertain source/adapter details with the coding workflow first. Ask the user only when actual business meaning remains ambiguous, and show that concrete local difference. A coding bug against already confirmed intent should be repaired, not submitted as a new requirement for approval. An AST hash alone cannot prove behavioral equivalence.
- Shared-rule edits select all dependent operations/transitions for review and regression. Confirmation of one operation must not silently authorize changed behavior in another.

Hashes establish freshness and identity; they do not establish user approval or semantic equality. A coding agent cannot obtain acceptance by updating the candidate, model and expected tests together after an unconfirmed behavior change.

## Validation design

| Gate | Required checks | Limits |
| --- | --- | --- |
| Design legality | IDs, references, types, state initialization/transition endpoints, declared guards, rule DAG, operator arguments and applicability. | Arbitrary guards may not permit automatic overlap, reachability or termination proofs. Unsupported analyses are diagnostics, not invented passes. |
| Confirmed semantics | Current scoped graph meaning matches the recorded snapshot, or an explicit accepted change exists. | A static hash is not proof of all behavioral equivalence. |
| Binding and coverage | Concepts, native state/rule declarations, actual source/parameters/capture points and cases agree; pending bindings block runtime acceptance. | Static source analysis does not prove actual invocation. |
| Runtime conformance | State before/after, rule inputs/results/skips, effects and command/call/check causality match actual native evidence. | Do not infer execution from graph position or timestamps alone. |
| Independent behavior | Confirmed examples, rejection cases, boundaries and relevant sequences match independently checked effects. | Reusing the product evaluator as the only oracle is circular. |

Use model-based sequences for confirmed temporal behavior, for example share -> download -> revoke -> next download. When relevant, add concurrent requests, explicit read-timing cases, wait/resume, resource release and same-instance checks. Test defined outcomes, not an invented universal success/failure lifecycle. Keep the user's existing business expectations and white-box checks.

Finite decision domains can support truth-table cases and checks of each condition's intended effect; general numeric/relationship rules need chosen boundary and instance cases. Mutation cases such as `all` -> `any`, changed transition target, omitted guard, wrong object identity or stale read basis should fail the appropriate gate. No claim of universal completeness follows from a finite suite.

## Implementation sequence and acceptance

1. Add versioned state drafts, shared concept-ID resolution and design assembly. Fix policy focus and render all three conceptual views before source exists.
2. Add semantic snapshots/diffs, scoped confirmations, applicability and typed cross-links. Keep existing rule validation and native machine guards.
3. Bind formal runtime projections deterministically from the confirmed definitions, preserving IDs and existing model/engine checks. Keep old protocols explicitly supported during migration.
4. Extend recall, impact analysis and iteration gates to semantic changes and shared dependents. Add the focused mutation regressions.
5. Exercise a fresh empty-project dialogue and a later feature iteration in Python and Node, with drive/observe coverage where supported. Retain dialogue, first failures, fixes, retests, actual runtime and browser evidence separately.

Acceptance must include: no-code three-graph preview; actual state transitions visible; shared rule identity and distinct arguments; typed state/rule links; incomplete answers not confirmed; partial preview not full approval; unauthorized logical drift rejected; source-only refactor rebound without repeated questions; pending source bindings rejected at runtime gate; real state/rule/effect capture; observer controls producing zero business events; and synchronized Graph/Timeline historical identities.

Expected code boundaries are a draft schema and validator, a shared conceptual assembler/resolver, semantic confirmation/diff logic, then integration with `bo_design`, `requirements_dialogue`, `change_sync` and existing state/policy modules. These are proposed responsibilities, not modules already implemented. The execution engine, core observation mechanism and application authority remain unchanged.
