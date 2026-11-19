# Model construction through dialogue

Status: proposed refinement of P0–P7, reviewed on 2026-11-18 against the maintained
Skill, concept services, binding/runtime checks, viewer integration and the entire
behavior-contract plan. This document changes the development plan, not the released
Skill. Read it with [protocol.md](protocol.md) and [acceptance.md](acceptance.md).

## Purpose and terminology

The dialogue has a concrete modeling outcome: construct and confirm the application's
business networks, object state models, shared rule networks and their interactions.
Questions about implementation support that outcome. Adapting question wording to a
respondent's role is one part of this process, not its organizing principle.

The user's word **forest** means a collection of models/subnetworks with independent
or shared responsibilities. It does not impose a graph-theoretic tree constraint:
business paths may loop, state machines may cycle, and rule operations may share
expression dependencies. Keep those structures and their existing stable identities.
An isolated component may be an intentional capability or an omitted relationship;
connectivity alone cannot decide which.

A layer is a viewing category. Network membership is a projection of existing
definitions. A model defines meaning. An instance identifies an actual object/run.
Do not introduce a new forest execution engine or another editable model registry.

## Source-grounded audit

| Project mechanism | What the current implementation establishes | Gap this plan must address |
|---|---|---|
| [Skill steps 1–3](../../../skills/vibelens/SKILL.md) | Requires peer business/state/rule design, multiple capabilities, explicit mode, binding, probes and later recall | The entrypoint names the obligations but does not provide a complete model-construction session or per-model review progression |
| [Concept assembler](../../../skills/vibelens/scripts/bo_observer/concepts/model.py) | Validates `networks`, objects, facts, `state_models`, policy, applicability, crosslinks and expectations before source exists | Validation of supplied definitions cannot discover every omitted capability or unstated relationship |
| [Network membership](../../../skills/vibelens/scripts/bo_observer/concepts/networks.py) | Projects business roots, state models and each rule operation's dependency closure; shared rules retain identity | A list of projected networks is not evidence that their boundaries and interactions were understood and reviewed |
| [Network review](../../../skills/vibelens/scripts/bo_observer/concepts/network_review.py) | Distinguishes behavioral edges from containment and reports components/unconnected concepts by layer | Add per-model context and the interpretation of reported gaps; a disconnected forest must not automatically become an error or gain fabricated edges |
| [Question scheduler](../../../skills/vibelens/scripts/bo_observer/workflow/requirements_dialogue.py) and [development questions](../../../skills/vibelens/scripts/bo_observer/development.py) | Validate authored decisions and their history, select ready questions, distinguish user issues from unresolved source calls | Add the step that derives modeling work from the requested scope and defined model obligations, before question selection |
| [Concept semantics](../../../skills/vibelens/scripts/bo_observer/concepts/semantics.py) | Dependency-expanded snapshots, scoped confirmations, semantic change and shared-dependent review | Persist what a review presentation actually covered and how incomplete construction targets are resolved; preserve existing confirmation strictness |
| [Crosslinks/applicability](../../../skills/vibelens/scripts/bo_observer/concepts/obligations.py) | Typed action/event, transition/rule, decision/fact and transition/effect links; every operation declares state/rule applicability | Rich handoffs, shared ownership and multi-model completion still need the behavior interaction contracts proposed in P1/P3 |
| [Binding](../../../skills/vibelens/scripts/bo_observer/concepts/binding.py), [associations](../../../skills/vibelens/scripts/bo_observer/concepts/associations.py), [runtime](../../../skills/vibelens/scripts/bo_observer/concepts/runtime.py) | Compare confirmed definitions to native models, rules, source, cases and selected actual witnesses | Make each construction result produce explicit implementation and observation obligations; new interaction semantics require new witnesses |
| [Iteration recall](../../../skills/vibelens/scripts/bo_observer/workflow/iteration_recall.py) | Restores concepts, current/previous model inventories, source changes and layer/probe obligations | Reopen the affected modeling work when a capability, model boundary or interaction changes; a source inventory is evidence, not automatic business approval |
| [Design preview](../../../skills/vibelens/scripts/bo_observer/web/design_preview.py) and existing viewer | Present shared concept projections and focused graphs | Offer model overview, individual networks and boundary reviews from the same definitions; a clear picture does not itself confirm hidden semantics |

Rules currently use one `discovery.policy` expression registry with multiple Boolean
operation roots. These roots provide inspectable rule subnetworks sharing predicates.
This supports a collection of rule networks; it does not establish arbitrary separate
policy dialects or general multi-valued decision engines. Reuse the current registry
and qualified references; propose an additional registry only for a demonstrated need.

## What the guided session must construct

| Deliverable | Human meaning to confirm when unclear | Agent-maintained definition | Expected review |
|---|---|---|---|
| Capability/model overview | Which stated capabilities are independent, share an object, or depend on an outcome | Source-backed inventory derived from `networks`, `objects`, `state_models`, `policy.operations` and explicit boundaries | All in-scope model roots, pending items and connections; no forced single start/end |
| Business networks | Who acts on what, what initiates the action, what can follow and what outcome matters | Actions, conditions, triggers, effects and typed progression/branch/parallel relations | Routes and alternatives within each network, with relevant external endpoints |
| State models | Which object owns the state, how one instance is identified, allowed changes and their completion | Initial state, typed states/events/context, transitions, guards/effects and applicable activities/resources/joins | Each state model independently, including incoming events and outgoing effects |
| Rule networks | What is being decided, relevant facts, combination logic, reuse and when facts are current | Typed inputs, predicate arguments, expression DAG, operation roots and read basis | Each decision root plus its dependency closure and other consumers of shared conditions |
| Cross-model interactions | How an operation, state change, rule or another capability affects the others | Existing applicability/crosslinks, plus proposed behavior interactions for handoff, ownership, ordering and completion | A boundary view showing the actual relation and its meaning |
| Expectations and limits | Observable examples, prohibited outcomes, required progress and environmental assumptions relevant to the request | Independent cases/properties, unresolved assumptions, implementation obligations and optional analysis profiles | Small scenarios linked to the exact models; application limits separated from analysis bounds |

Completeness is scoped to supplied requirements and discovered implementation
evidence. Do not claim that this process recovers every unstated intention. An
operation can have no state change, no separate rule, or a read-only state relation;
retain the existing explicit applicability reason instead of manufacturing a model.

## Construction loop

1. **Restore and inventory.** Read the request, accepted decisions, existing forests,
   current scope and source inventory when available. Produce an overview of named
   capabilities, object identities, candidate state owners and decisions. Mark which
   entries come from the user, adopted project rules, source or agent interpretation.
2. **Construct candidate definitions.** Extend existing JSON with the applicable
   networks and links. Keep stable IDs. Work on a new model without forcing unrelated
   confirmed models back into initial setup. A wholly unknown model stays a scoped
   construction target until its minimum valid draft exists.
3. **Identify specific modeling gaps.** Check applicable model obligations and
   compare the inventory with stated scope. Examples include a mentioned independent
   capability with no model, unknown state owner, omitted branch, ambiguous rule
   composition, or a claimed cross-model effect without a completion boundary.
   Every candidate gap needs a source and affected scope. A generic checklist alone
   supplies neither a requirement nor a reason to ask the user.
   Schema/reference diagnostics can be deterministic; extracting an unmodeled
   capability from natural language remains agent interpretation and needs that
   provenance. Neither checks nor language-model confidence prove all intent was found.
4. **Route by meaning and evidence.** The agent resolves representational choices and
   implementation facts. Human questions clarify intent or approve a meaningful
   interpretation. A structural diagnostic may be fixed directly when the existing
   answer is already explicit. Technical choices that affect user-visible behavior
   return with a short explanation of that consequence.
5. **Present the relevant model.** Show the current network and the exact ambiguity,
   in the respondent's language and preferred depth. Use the same IDs/projection as
   the viewer. Explain any omitted boundary. An answer should visibly resolve or
   change a node, edge, condition, identity, scope or expectation.
6. **Review the result.** Reuse explicit answers where they already confirm the exact
   meaning; otherwise show the small model change for confirmation. Preserve history
   and dependencies. Do not require another approval of a separately authored spec.
7. **Bind and verify.** Translate confirmed model obligations to native execution or
   observation, source anchors, probes and independent cases. Keep design, support,
   implementation coverage and runtime results separately inspectable.
8. **Reconcile the next iteration.** A source refactor rebinds evidence. A new feature
   or semantic change revisits its model scope and shared dependents. Retain unaffected
   forests, confirmations, identities and user layouts.

The loop runs within each affected increment. It does not require freezing the
entire application's future design before developing one confirmed capability.

## Role adaptation is model-specific

| Review target | Product/business wording | Architecture/development detail |
|---|---|---|
| Business boundary | Can these two requested activities be used independently? | Entry/trigger and dependency boundary for their declared networks |
| State ownership | Is this status about the file, a particular recipient's access, or one download? | Subject type, identity tuple and separation of instances/models |
| Rule reuse | Do these actions use the same permission condition? What differs? | Predicate identity, argument binding, fact revision and independent operation roots |
| Model interaction | After this action completes, what changes in the other activity? | Event/payload, effect completion, handoff and consistency boundary |
| Expected behavior | In this already relevant situation, what should the user observe? | Independent assertion, property scope and source/runtime witness |

These are equivalent review targets, not a requirement to ask every wording variant.
The optional participation preference from protocol section 5 selects presentation
depth. It never suppresses a required model obligation or grants decision authority.
The agent translates an answer into structured definitions and presents its meaning;
users need not author JSON, enumerate transitions mechanically or select graph IDs.

## Many questions: a model review workbook

Use a short model index with status per network, followed by one focused review
group at a time. Group by the actual model/boundary being constructed, not by a
generic questionnaire category such as "all concurrency questions".

- Reuse explicit answers, then ask at most 1–3 ready human questions per round.
- Offer relevant choices, free text, an explanation and "not sure". Keep unresolved
  answers visible. Preselected values and saved drafts do not count as confirmation.
- Show a small graph beside or directly before the questions where the host permits.
  Keep a clickable viewer link and a compact text/diagram fallback in other hosts.
- Allow review/change of previous answers. Recompute only dependent questions and
  model changes; preserve unrelated answers after branching, restart or role change.
- Track intent resolution and implementation/evidence status separately per model.
  A completed questionnaire cannot imply that source binding or tests passed.
- Prefer host question cards/conversation. Current Web remains the graph viewer.
  An optional external form would need an explicit future host adapter using the
  same discovery decisions and versioned confirmation; it is not required here.

Borrow neutral probing from `interview-script`, progressive presentation from
`onboarding-design`, answer review from `form-design`, and single-issue wording
from `survey-design`. The VibeLens model obligations determine what must be built.
Do not copy long interview scripts, user-research scales or a second decision store.

## Proposed protocol integration

Finalize encoding during P1. Extend existing discovery decisions rather than adding
an unrelated questionnaire document. The following are proposed responsibilities,
not fields accepted by the current release:

| Record | Additional responsibility |
|---|---|
| Construction target | Identify a not-yet-defined model/boundary from a source statement, its intended kind/scope and unresolved meaning. It is not a synthetic runtime node or a valid executable definition. |
| Modeling obligation | Target an existing model/member/relationship or a construction target; identify the required definition, reason, owner and evidence. Keep these obligations independent of whether an agent happened to author a question. |
| Decision | Link its answer to the obligation and intended semantic change. Retain the existing `affects`, dependency, original answer and change-history contract. |
| Review presentation | Record model IDs, semantic revision, visible/reviewed scope, omitted boundaries, and the corresponding conversation presentation. A user answer cannot approve a newer or unseen scope. |
| Confirmation | Continue using immutable dependency-expanded semantic snapshots. Explicit source evidence and matching scope remain required; a presentation record alone is not approval. |
| Readiness report | Derive model inventory, definition gaps, pending decisions, engine support, bindings and evidence from canonical records. Do not maintain another mutable forest registry. |

For missing models, current `affects` references cannot simply point at nonexistent
IDs. P1 must specify a strict draft-target representation and atomic promotion to a
valid concept ID, with provenance and reference checks. Never relax executable
validation or insert fake states/edges to make the question scheduler accept a draft.

Reuse current typed crosslinks for their existing meanings. Rich interaction
contracts in `behavior.json` reference the same endpoints and extend meaning only
where needed. A visual membership, containment edge or source-name match does not
establish triggering, synchronization, policy reuse or atomicity.

## Whole-plan changes

| Phase | Required adjustment and completion evidence |
|---|---|
| P0 | Baseline a project with multiple business roots, multiple state owners and shared rule dependencies. Retain both legitimate independence and a known missing relation. |
| P1 | Define construction targets, modeling obligations and scoped review records; preserve current model schemas and add precise interaction contracts. No new forest execution authority. |
| P2 | Implement inventory → candidate models → gap routing → focused questions → model review. Role adaptation and optional grouped question cards operate within this loop. |
| P3 | Derive bindings/capture cases for each confirmed model and boundary. Preserve native authority, independent observers and language adapters. Shared declarations must retain distinct invocations. |
| P4 | Reconcile source discoveries, added/removed models, splits/merges and changed shared rules. Reopen the affected interpretation and evidence, retain unrelated networks. |
| P5 | Add compact model overview and per-network/boundary review using existing projections. Preserve full hidden dependencies, personal layouts and runtime/Timeline identity. |
| P6 | Build an analysis scope from selected models plus their interaction/environment boundary. Missing relevant behavior stays unresolved; role or questionnaire completion cannot imply exhaustive verification. |
| P7 | Test initial multi-network construction, misunderstanding correction, semantic iteration and source refactor in fresh trials. Product visuals show these same confirmed models before/after coding. |

Add A29–A34 to the existing acceptance matrix; keep A01–A28 and existing gates.
Public copy can explain: "Build the application's flows, states and rules together,
then follow them into the running code." Present multiple networks progressively;
avoid implying one graph layer equals one model or requiring a technical questionnaire
before the first useful view.

## Verification of this review

On 2026-11-18, four existing focused suites were invoked with
`.venv/Scripts/python.exe`: `test_model_networks.py` (15 passed),
`test_concept_models.py` (47 passed), `test_requirements_dialogue.py` (22 passed),
and `test_concept_workflow.py` (22 passed, 1 setup error among 23 tests).

The error occurred in
`test_contract_parent_replacement_cannot_escape_with_identical_bytes` when its
Windows `cmd /c mklink /J` subprocess returned exit 1. Its junction-based assertion
was not reached; the cause and that security check remain unresolved for P0.
Interpreter startup also reported a Miniforge path-location warning, while the
other suites executed successfully. These results are a focused baseline check,
not full product acceptance, role-dialogue validation or acceptance of this proposal.
