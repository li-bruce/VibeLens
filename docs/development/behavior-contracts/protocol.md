# Protocol and semantic contract proposal

Status: proposed. Names and examples below are design inputs for P1, not formats
accepted by the current release. Pin final schemas and fixtures before coding
consumers. Preserve the protected boundaries in [the overview](README.md).

Implementation status is tracked in [progress.json](progress.json). The first P1
[scalar definition slice](p1-definition-slice.md) is available on the development
branch; discovery/project migration and the remaining sections below are pending.

## 1. Canonical artifacts and ownership

| Artifact | Owner and purpose | Update rule |
|---|---|---|
| Existing `discovery.json`, proposed `business-discovery/v3` | Confirmed business/state/rule intent, human sources, decisions and participation preferences | Extend existing discovery, never create a second decision ledger. |
| Existing `bo_stategraph/project.json`, proposed `bo-project/v2` | Project/mode and native model registry, bindings, reference to behavior contract | Keep `model.machines`, concept and policy identities; retain existing schemas/readers. |
| New `bo_stategraph/behavior.json`, proposed `bo-behavior/v1` | Cross-model behavior, properties, assumptions and refinement declarations | Reference canonical states/rules; define only additional semantics here. |
| New `bo_stategraph/analysis/profiles/<id>.json`, proposed `bo-analysis-profile/v1` | Selected models, property set, finite parameters, abstractions and resource budget | Analysis configuration cannot silently change production limits. |
| Existing observation/source plans under `.stategraph/` | Derived inventory, required bindings and missing evidence | Regenerate from canonical definitions plus independent source scans. |
| New `.stategraph/analysis/<run-id>/` | Generated formal model, source map, tool output and result receipt | Derived, revision-bound output; immutable once accepted. |
| Existing `bo_stategraph/config/views/` | Personal layout, filters, annotations and camera | Preserve through migration; neither validation input nor model authority. |

Paths are project-relative and resolved through existing path validation. Reject
escapes, duplicate definitions, unsupported versions and unresolved required refs.
Hashes pin referenced artifacts; they are not semantic proof or a defense against
an agent able to rewrite every trusted file.

Discovery and native state declarations describe different stages. Existing
semantic binding checks continue to compare them. An action with a native
transition references it; it does not duplicate a separately editable transition.
Properties are independently confirmed expectations, not generated copies of the
implementation's decisions.

## 2. Identity and composition

- Reuse canonical project, network, object, model, node, relation and source IDs.
- Qualify model-local states, transitions and instance IDs. Two models may both
  contain `ready`, and both may have an instance named `1`.
- A source function, a business concept, a state concept and a call instance keep
  independent IDs. Typed mappings connect them; equal labels never merge them.
- A system analysis scope lists participating models and external boundaries.
  Independent networks can remain a forest; a display connection is not execution.
- State identity at analysis time includes relevant values, instances, queues,
  resource owners, local execution positions and environment state. A graph node
  is not one complete global state.
- Source locations and labels may change without changing identity. Meaning and
  source fingerprints invalidate evidence separately.

## 3. Behavior document

| Section | Required information | Validation |
|---|---|---|
| `scope` | Project, participating model/object refs, environment boundaries, explicit exclusions and unresolved items | Every required reference exists; exclusions cannot hide required source coverage. |
| `domains` | Typed values and bounds/abstractions where applicable | Type consistency; finite certification only with a justified finite domain. |
| `variables` | Stable ID, domain, object/model owner, canonical state/fact ref and persistence meaning | One authoritative writer/ownership contract; unknown values are explicit. |
| `initial` | Initial-state expression and any recovery initial-state alternatives | Well typed; at least one initial state in a finite configured instance. |
| `actions` | Parameters, enablement, reads, writes, updates, unchanged values and completion boundary | All selected variables have an explicit next-state rule or remain unchanged. |
| `interactions` | Shared reads/writes, handoff, queue, resource, transaction and join relationships | Valid scopes, ownership, correlation and declared ordering/atomicity. |
| `properties` | Independent state/transition/progress requirement and requirement source | Typed applicability, evaluable expression or explicit unsupported status. |
| `assumptions` | External behavior, scheduling, fault and consistency assumptions | Source, scope, rationale, reviewer/evidence and invalidation trigger. |
| `refinements` | Native-to-concept values, step correspondence, internal steps and completion evidence | Totality/unknown handling within selected scope; evidence level explicitly recorded. |

Discussions can contain unresolved entries. Binding and finite-export gates reject
unresolved entries that affect their requested claim. They must not reject a
legitimate source-free draft merely because implementation evidence is absent.

### Finite domains and boundaries

Record the origin of each bound using `application_limit`, `analysis_bound` or
`abstraction`. Preserve its source and enforcement location.

| Domain | Finite-analysis requirement |
|---|---|
| Boolean/enum | Enumerated values with exact type equality |
| Integer | Finite inclusive bounds and defined arithmetic/overflow behavior |
| String/bytes | Finite values or bounded length over a finite alphabet; otherwise an explicit abstraction |
| Set/map/sequence | Finite element/key domains, bounded cardinality/length and exact duplicate/order rules |
| Object instances | Bounds on simultaneously live instances and a justified identity/reuse abstraction |
| Queue/resource | Capacity, ownership, overflow behavior and release semantics |
| Time/counters | Explicit finite representation or a property-preserving abstraction; elapsed time and accumulated IDs can grow without bound |
| Number/float | No finiteness conclusion from numeric min/max alone; P6 rejects unsupported numeric semantics |

A creation limit on live objects alone does not bound monotonically increasing
identifiers. Queue length alone does not bound an unbounded payload domain. Loops
are permitted in finite models; a maximum test length is a different bound from
exhaustive exploration of reachable states.

For abstractions record the concrete domain, abstract domain, mapping, preserved
properties and justification status. A sampled range is an under-approximation.
An over-approximation can produce spurious counterexamples. Do not generalize
either result without the required correspondence argument. Budget exhaustion
is `incomplete`, not a justification for secretly shrinking the model.

### Action semantics

Each action has `id`, `model_refs`, optional `transition_ref`, `parameters`,
`enabled`, `reads`, `writes`, `updates`, `unchanged`, `completion` and source refs.
All update expressions read the same pre-state; updates apply simultaneously
within that modeled action. A phased implementation uses explicit intermediate
actions. `writes` and `unchanged` partition the selected state variables unless
the action declares a typed bounded nondeterministic update.

An enabled abstract action is not permission to mutate business state from the
observer. Completion binds to the actual native boundary: function return,
transaction commit, message acknowledgement or a separately confirmed event.
Return, exception, commit and business outcome remain distinct.

Pure conceptual actions without native implementations are permitted in drafts.
Bound implementations must explain early returns, exceptions, cancellation,
rollback and detached work where applicable. Missing or unsupported source
semantics remain gaps; no action is synthesized from timestamps or label matches.

### Expression subset

Use a typed JSON expression tree, shared policy references where supported, and
explicit parameter binding. Do not accept executable Python/JS strings or `eval`.

| Expression | Meaning |
|---|---|
| `literal(value, domain)` | A typed constant |
| `var(id, phase)` | A selected variable in `before` or `after` state |
| `param(id)` | An action parameter |
| `all`, `any`, `not`, `implies` | Boolean combination |
| `eq`, `ne`, `lt`, `le` | Typed comparison |
| `add`, `sub` | Integer arithmetic with explicit domain checks |
| `member`, `select`, bounded `forall`/`exists` | Access or quantify an explicitly finite domain |
| `policy_ref(id, bindings)` | Existing rule expression with known supported semantics |

This table is a proposed minimum, not a promise of current support. P1 fixes the
wire encoding, arity, null/unknown rules, number rules and evaluation order in
schema fixtures. P6 accepts only its declared supported operators. Shared
short-circuit predicates retain actual skipped/error/unknown observations. Opaque
callbacks require a reviewed model plus a separate mapping obligation; they never
silently become an always-true predicate.

### Cross-model interactions

Specify the applicable items rather than requiring every project to invent them:

- **Shared facts:** owner, readers, revision, read time and consistency guarantee.
- **Messages/jobs:** producer/consumer, payload domain, correlation, ordering,
  delivery/retry/deduplication, queue capacity, acknowledgements and failure paths.
- **Resources:** shared or instance scope, capacity, holder identity,
  acquire/release, waiting, cancellation and crash/restart behavior.
- **Transactions:** participating effects, real commit boundary, conflict handling
  and actual atomicity. Multiple snapshots with close timestamps do not prove it.
- **Joins:** invocation membership and explicit ALL/ANY/quorum semantics where
  supported. A different invocation cannot satisfy another run's join.
- **Environment:** external inputs/outcomes, clocks and scheduler choices relevant
  to the selected properties. Fairness is never assumed merely to obtain progress.

The integrated state/activity declaration remains authoritative for Petri-style
waiting, resource and join behavior. Analysis consumes its supported semantics.
Unsupported richer semantics require an adapter or stay explicitly unsupported.

## 4. Properties, refinement and evidence

Property kinds are `state_invariant`, `transition_constraint` and
`progress_property`. Liveness checks declare their scheduling/environment
assumptions. Expected termination is distinguished from unexpected deadlock;
do not globally disable deadlock detection to hide a stuck model.

Keep `properties` outside the transition relation. A modeled invalid transition
must remain reachable so the checker can find it. An invariant must not also be
used as a state filter that excludes the counterexample.

Identify the subject of analysis explicitly. `design_model` explores the declared
design. `implementation_model` requires a supported, source-bound abstraction of
the actual native behavior and separate correspondence evidence. Exporting the
intended design alone cannot discover code that violates a correctly specified
guard. P6 initially supports `design_model`; implementation-model analysis remains
unsupported until its adapter and translation checks are actually delivered.

Refinement declarations contain:

1. Selected concrete values/operations and abstract variables/actions.
2. The value mapping and treatment of absent, unknown or inconsistent observations.
3. The actual completion/linearization boundary, where applicable.
4. Internal steps that leave the chosen abstract state unchanged.
5. Expected preservation of properties and independent checking cases.
6. Evidence classification: `declared`, `source_bound`, `trace_checked`,
   `finite_model_checked`, or externally proved with an explicit proof artifact.

These classifications are different evidence kinds, not an automatic ladder.
Trace checking does not imply a proof for all executions. A consistent cross-model
state read needs its own evidence; clock ordering is insufficient.

## 5. Routed questions and durable decisions

Extend discovery's existing decisions. Keep current source validation and history.

Questions serve [model construction](model-construction.md): their targets include
capability boundaries, business relations, state ownership/transitions, shared rules
and cross-model interactions. Existing `affects` IDs locate valid concepts. P1 must
also specify strict source-backed construction targets for an omitted/not-yet-valid
model, without allowing dangling executable references. Modeling obligations and
question records remain distinct: the absence of authored questions cannot establish
that the requested model scope is complete.

| Field | Purpose |
|---|---|
| `kind` | `business_intent`, `technical_choice`, `implementation_fact`, `analysis_assumption`, or `verification_gap` |
| `owner` | Human decision-maker, coding agent, or named checker |
| `authority` | Scope of an actual decision/delegation; a role title grants nothing |
| `stage` | Before implementation, during coding, before acceptance, or before optional analysis |
| `trigger` / `affects` | Why it exists and which requirements/models/actions/source regions depend on it |
| `depends_on` / `priority` / `blocking_scope` | Existing scheduling semantics with explicit affected scope |
| `evidence_required` | Conversation confirmation, source reference, runtime witness, independent assertion or checker receipt |
| `invalidated_by` | Meaning, source, environment, adapter, property or build changes that reopen/recheck it |
| `resolution` | Answer, source, rationale where delegated, and exact evidence version |
| Proposed modeling target/reference | Existing model/member/link or source-backed construction target, plus the obligation the answer resolves; final encoding is fixed in P1 |
| Proposed review reference | Model scope, semantic revision, presentation source and omitted boundary shown before confirmation; not a replacement for semantic snapshots |

Separate a decision's human status from its implementation verification status.
A confirmed requirement may remain confirmed while its implementation evidence
becomes stale. A source-only move rebinds evidence without re-asking the meaning.

Illustrative decision record (hypothetical trial IDs):

```json
{
  "id": "D_QUEUED_DOWNLOAD",
  "kind": "business_intent",
  "owner": "human",
  "stage": "before_implementation",
  "question": "After sharing is revoked, may a queued download still begin?",
  "affects": ["download.start", "grant.revoke"],
  "depends_on": [],
  "priority": 1,
  "blocking_scope": ["download.start"],
  "status": "open",
  "evidence_required": ["authorized_conversation_answer"],
  "invalidated_by": ["revocation_meaning_changed"]
}
```

Participation preferences contain optional `knowledge_domains`,
`explanation_depth`, `preferred_participation` and language. Decision authority is
a separate explicit record. Ask one short preference question when useful; skip
it when the conversation already establishes the preference. Allow mixed roles,
changes, delegation and "not sure". Do not persist sensitive personal profiling.

Unknown business meaning routes to a human. Pure implementation uncertainty
routes to the coding process and actual evidence. Technical choices can remain
with the agent within existing authorization. If a choice changes user-visible
meaning, present its consequence for confirmation.

Every round selects relevant ready human issues only; the three-question budget
is not a total cap. A partial answer resolves only its addressed scope. Silence,
a viewed graph and an agent-authored answer are not human confirmation. Questions
can be clarified later without deleting the original answer/history.

Group answers by their model or interaction boundary. A host may render question
cards or ordinary conversation from the same records. Preserve branching history,
partial answers and return/change across sessions. Derived readiness reports retain
separate intent, definition, support, binding and evidence dimensions per model.
Role adaptation changes wording/depth; all applicable modeling obligations remain.

## 6. Analysis profiles and result receipts

Illustrative profile; referenced IDs are hypothetical and need real definitions
before use:

```json
{
  "schema": "bo-analysis-profile/v1",
  "id": "queued-download-small",
  "subject": "design_model",
  "model_refs": ["grant", "download", "transfer_slots"],
  "property_refs": ["revoked_cannot_start", "slot_capacity"],
  "bounds": {
    "users": {"value": 2, "origin": "analysis_bound"},
    "files": {"value": 1, "origin": "analysis_bound"},
    "live_downloads": {"value": 2, "origin": "analysis_bound"},
    "queue_length": {"value": 2, "origin": "analysis_bound"}
  },
  "assumption_refs": [],
  "engine": "tlc",
  "budget": {"wall_seconds": 60, "memory_mb": 1024},
  "required_for_acceptance": false
}
```

The profile cannot self-certify finite state. The admission check inspects all
reachable domain references, generated identities, counters, queues, environment
choices and unsupported operations before export. A budget does not change the
model's meaning. Enabling a mandatory profile becomes a protected requirement.

Results use a separate category `formal_analysis`; existing `model_checks` retain
their structural-assertion meaning. Each result records:

- analysis subject, contract, declaration, property, profile, mapping, source/build and environment fingerprints;
- adapter/compiler version, engine version/checksum, command configuration and completion;
- explored-state statistics and applicable property coverage;
- `pass`, `fail`, `incomplete`, `unsupported`, `error`, `stale`, `pending` or
  `not_applicable`, with precise reasons;
- counterexample provenance and original artifact references, when present.

Only completed checking of all selected supported properties may report `pass`
for that exact finite model. Tool absence, timeout, truncation, unsupported syntax
and an empty initial-state set are not passes. Preserve accepted results as
historical evidence; relevant changes create new attempts and mark old results
inapplicable according to the receipt's dependency set.

Design-model receipts depend on semantic definitions, properties, assumptions,
profiles and analysis tools. A source-free design has no application build yet;
record that explicitly. Native mapping/runtime receipts additionally depend on
the actual source/build, adapters and observation boundary. A source-only refactor
can preserve a design-analysis result while invalidating native correspondence.
A locale/layout change invalidates neither. Never reuse a design receipt as
evidence for a new application build.

A model counterexample uses `origin: model_analysis`, logical step indices,
before/after values, stable model/action refs and optional loop-back index.
It has no invented wall-clock duration or producer invocation. Actual replay in a
test creates separate `origin: runtime` evidence linked to that counterexample.

## 7. Validation and migration

Validation order:

1. Versioned JSON structure and types.
2. Referential integrity and identity/ownership conflicts.
3. Semantic checks: initial states, action frame conditions, property scope,
   interaction rules and assumption consistency.
4. Native-engine and optional analysis capability admission.
5. Independent source/binding/observation checks.
6. Applicable business, state, project and optional formal checks.

Invalid definitions fail before execution/loading. Actual invalid runtime facts
remain recorded with diagnostics; never normalize them to a valid state. Optional
analysis failure must not stop a running application's business operations.

Migration provides plan/apply/check through the existing managed migration path.
Version the discovery, project and affected model schemas deliberately; keep old
readers and fixture round-trips. Missing new fields in old files mean unconfigured,
not "complete". Never fabricate a bound, authority, confirmation or supported
formal semantics during migration. Schema unknown fields stay strict.

Serialize deterministically, resolve references inside project/tool boundaries,
write atomically and reject stale revisions. Preserve IDs, local views, hidden
elements, notes and frozen recordings. Keep a reversible pre-migration manifest
and test failure partway through a multi-file update. Acceptance must reject a
mixture of contract revisions.
