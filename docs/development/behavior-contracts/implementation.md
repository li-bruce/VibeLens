# Ordered implementation plan

Current implementation branch: `feat/behavior-contracts-sequential`, restored from
the complete approved plan at `a8f569d7`. P0–P6 are complete; P7 is next.
Follow [progress.json](progress.json) and its linked evidence before starting the
next phase. The planning commit alone satisfies no product acceptance phase.

## Module boundaries

Reuse the current implementation described in [audit.md](audit.md). Proposed new
paths are marked **new** and must not be confused with existing APIs.

| Responsibility | Existing integration point | Proposed implementation |
|---|---|---|
| JSON and pure semantic validation | `bo_observer/protocol.py`, `schemas/`, `bo_contracts.py`, `concepts/`, `policy/` | **New** `bo_observer/behavior/{contract,domains,expressions,actions,interactions,properties,refinement}.py` |
| Guided model construction and review | `concepts/model.py`, `networks.py`, `network_review.py`, `workflow/requirements_dialogue.py`, `concept_review.py` | Extend concept review with modeling obligations and scoped presentations; **new** focused `workflow/question_routing.py` handles ownership/presentation. Keep canonical models and decisions in discovery |
| Recalled obligations and impact | `workflow/iteration_recall.py`, `bo_sync.py`, `change_sync.py` | Reuse these entrypoints; add behavior-specific helpers, not a second iteration coordinator |
| Source and actual native witnesses | Language adapters, `observation_requirements.py`, `mapping_contract.py`, `concepts/runtime.py` | Extend bindings/capabilities and narrow observation hooks; keep native execution authoritative |
| Evidence coverage and expiry | `workflow/sync_verify.py`, existing receipts | **New** `behavior/coverage.py` and `behavior/evidence.py` for scoped reports and dependency fingerprints |
| Optional model export/run/import | Existing dependency setup and artifact path helpers | **New** `bo_observer/analysis/{capabilities,manifest,runner,trace}.py`, `analysis/tla/{exporter,source_map,results}.py` |
| Shared graph/Timeline presentation | Existing concept details, capture projections and shared renderer data | Add contract/evidence sections and analysis-trace adapter; renderers share the same records |
| CLI | Existing public `bo_*.py` shims | At most **new** `bo_behavior.py` and `bo_analyze.py`; normal coding uses the existing iteration commands |

Module names are proposed seams, not a requirement to create empty files. Combine
small cohesive units; split only when responsibilities differ. Domain functions
accept typed inputs and return structured diagnostics. File IO, subprocesses,
HTTP, presentation and command parsing stay outside the semantic core.

Dependency direction: workflow/CLI → behavior services → existing model/type
contracts. Analysis adapters consume normalized behavior; core validation never
imports TLC, viewer code or application packages. Native language adapters emit
protocol facts and keep their current executor responsibilities. Do not duplicate
the complete Python tool in Node, React or Vue.

## P0 — Preserve the baseline

Priority: required before semantic changes.

- Record current HEAD, clean/dirty status, protocol versions, installed-copy
  manifests and relevant test entrypoints.
- Freeze representative existing fixtures: source-free draft; drive and observe;
  multiple models sharing state/instance names; shared policy; native activity /
  resources / joins; API error capture; retained personal views.
- Include multiple business roots, independent state owners and a shared rule
  dependency. Retain a legitimate disconnected capability and a known omitted
  behavioral link so network review cannot confuse them. Resolve the focused
  baseline test error recorded in [model-construction.md](model-construction.md).
- Establish readable ownership/dependency notes and record existing failures
  independently. Do not clean an unrelated working tree to create a baseline.
- Carry BC-01–BC-12 into a machine-checkable requirement/case inventory in the
  implementation, preserving the existing protected acceptance contract.

**Exit:** existing fixtures run unchanged, pre-existing failures have reproductions,
and the candidate's additional checks cannot replace those gates. See A23/A24/A28.

## P1 — Contracts, reference resolution and migration

Priority: core. Depends on P0.

- Implement the versions and canonical artifact boundaries in [protocol.md](protocol.md).
- Resolve domains, actions, properties, model interactions and source-free refs
  through one semantic loader. Return stable diagnostic codes and JSON paths.
- Validate initialization, unchanged fields, single ownership, parameter types,
  completion boundaries and supported expression operators.
- Distinguish runtime limits, finite analysis bounds and abstractions. Expose
  unknowns without forcing the application to become finite.
- Reuse current model/policy/statechart/activity validators. Preserve their
  errors; do not override them with a permissive compatibility hook.
- Add migration plan/apply/check, interrupted-write recovery and exact-version
  snapshots. Read old project/discovery versions without inventing new guarantees.
- Define the initial finite-export subset as capability data even before a runner
  exists. A structurally valid contract can remain unsupported for analysis.
- Define source-backed construction targets for models not yet valid enough to
  enter the concept registry, modeling obligations and scoped presentation records.
  Promote targets atomically to valid concepts; retain strict executable validation.
  Derive the model overview from existing registries rather than maintaining a
  second editable forest. Follow [model construction](model-construction.md).

**Exit:** positive, invalid and legacy fixtures cover A04–A10/A23/A29/A30. Unsupported
semantics are distinguishable from invalid definitions and unbound drafts.

## P2 — Guided model construction and question routing

Priority: core. Depends on P1.

- Implement the [construction loop](model-construction.md): restore the full model
  inventory, build candidate business/state/rule networks, identify source-backed
  modeling gaps, route questions, review the affected models and retain confirmation.
  Derive obligations independently of authored questions; an empty question list
  does not establish complete modeling of the declared scope.
- Review each model's actual semantics and the relevant connections between models.
  Business routes, object lifecycles and shared rule dependencies retain distinct
  meanings. Legitimate independence is allowed; containment is not a behavioral link.
- Extend existing discovery decisions, scheduling and source-history validation.
  Add kind, owner, stage, authority, evidence requirements and invalidation.
- Offer one short participation preference when useful. Do not make a job title
  or technical quiz a prerequisite for building a graph.
- Provide equivalent business and technical wording for the same unresolved
  meaning. A product user can answer consequences; a developer can inspect detail.
- Generate human questions only from current ambiguity or changed meaning.
  Route implementation facts to the coding agent/checkers; preserve scoped human
  delegation without treating it as approval of invented requirements.
- Preserve unanswered, partially answered, deferred and contradicted decisions.
  Reopen evidence checks without unnecessarily reopening a confirmed intention.
- Keep 1–3 ready human questions per round; allow any number of necessary rounds.
  Continue independent implementation work when an unrelated scope is waiting.
- Preview the affected business/state/rule region and its boundary using existing
  conversation/Web projection. Record the reviewed semantic revision and omitted
  boundary. Confirmation remains in chat; host question cards can collect answers.
  Web remains the viewer, with no new answer form required by this plan.
- For many questions, provide a short model index and focused review groups. Support
  conditional questions, explanation, free text, partial answers, return/change and
  interruption recovery through the same decision history. Review statuses describe
  intent separately from binding, engine support and runtime verification.

Initial construction review must work in P2 through existing previews and compact
model summaries. Do not postpone the user's first model review until P5; that phase
extends the runtime/analysis presentation after binding and iteration integration.

Update `SKILL.md` with a short routing decision and links to focused references.
Update `requirements-dialogue.md`, `iteration-dialogue.md`, `concept-models.md` and
`project-setup.md`. Avoid embedding the full protocol in the Skill's entrypoint.

**Exit:** A01–A03/A17/A29–A32 pass, including a product respondent, technical respondent,
mixed role, skipped preference, partial answer and role change without authority change.

## P3 — Native bindings and cross-model observation

Priority: core. Depends on P1.

- Bind model variables to actual fields/functions and independent readers. Bind
  each action to its entry, actual completion and relevant error/cancel paths.
- Expand each confirmed model and cross-model obligation into source/probe/case
  requirements. Every registered model and shared-rule consumer retains identity
  and coverage; one successful business route cannot stand for the entire forest.
- Identify all application-owned entrypoints and relevant state/effect writers
  independently of authored nodes. Keep helpers and static-only symbols classified
  without pretending that every statement requires a probe.
- Reuse OpenTelemetry and current ContextVar/AsyncLocalStorage mechanisms for
  technical lineage. Preserve object, model, invocation, attempt and build identity.
- Add declared handoff/read/commit witnesses where existing adapters lack them.
  Cover queued/detached work, callback boundaries, HTTP denial/error responses and
  database commit/rollback where configured.
- Model shared-resource ownership and multi-model effects without synthesizing a
  distributed transaction. Independent state reads require revision/transaction
  evidence when a check needs a consistent joint state.
- Keep probes in isolated `bo_` wiring. Observe actual values; invalid values stay
  visible. Redact sensitive fields and avoid unrestricted payload collection.
- Verify observation on/off/failing/queue-limited modes preserve business effects.
  Polling, source viewing, analysis and control operations must create no business events.
- Require concise English docstrings/JSDoc on mapped API handlers, functions and
  important parameters. Extract names into locale-specific display overlays.

**Exit:** A07–A16/A27/A34 pass in real Python and Node fixtures. React/Vue coverage
reuses the language adapters and includes a real frontend entrypoint; it does not
claim that a static callback relation proves a runtime call.

## P4 — Iteration closure and evidence invalidation

Priority: core. Depends on P2/P3.

Extend, rather than replace:

```text
recall → begin → code/bind/instrument → scan → inspect
       → resolve scoped questions and missing evidence → verify → accept → check
```

`recall` shows the affected confirmed requirements, model/network inventory,
behavior assumptions, missing bindings, protected checks and next required work.
Full artifacts remain in files; avoid copying complete source graphs into prompts.

| Change | Required response |
|---|---|
| Business meaning, guard, rule arguments, transition target or outcome changes | Identify requirement basis, show local semantic diff and obtain any missing confirmation |
| File move, handler split, callback resolution or probe refactor | Rebind and test automatically; do not ask the user to certify source facts |
| New/deleted entrypoint, state writer, effect or background job | Independent inventory and coverage diff, new obligations and relevant cases |
| Domain, queue bound, environment or fairness changes | Invalidate affected property/analysis evidence and reassess assumptions |
| Engine, adapter, compiler, property or analysis profile changes | Invalidate receipts keyed to those semantics/tools |
| Label, color, layout or locale changes only | Preserve semantic confirmation and analysis; test display identity/interaction only |
| Capability/model added, retired, split or merged; an unmodeled source feature discovered | Reconcile the model inventory, record the intent basis and affected scope, update crosslinks/bindings and review any new interpretation; preserve unrelated models |

Compute impact through actual typed dependencies, including consumers of shared
rules/facts and interaction boundaries. Start conservatively; optimize reuse only
after differential tests establish safe invalidation. Never infer equivalence from
an unchanged node ID or file hash alone.

Reuse evidence by its subject: unchanged design semantics can retain a design-
analysis result through a source refactor, but the new native build needs fresh
mapping/runtime evidence. Display-only changes retain both. Persist the exact
dependency set and the reason for every reuse or invalidation.

Host integration must explicitly invoke this workflow in an activated chat. Use
supported hooks where available, and an explicit agent checklist elsewhere. Report
the integration capability. Detect a source revision newer than the accepted
batch; it remains pending until reconciliation and checks finish.

Keep separate result categories for intent/definition, mapping, capture, state
rules, business outcomes, project checks and optional formal analysis. Each has a
scope, coverage denominator, current evidence and missing items. A required gap
blocks acceptance; optional unavailable analysis is reported without stopping
native execution. Check removal and scope narrowing against the protected baseline.

**Exit:** A14–A20/A23/A33/A34 pass, including deliberately omitted recall/probe/model update
and invalidated evidence. Existing acceptance cannot be bypassed by the new report.

## P5 — Progressive graph and Timeline inspection

Priority: core UI. Depends on P4.

- Preserve the initial compact business view. State/rule subnets remain separately
  inspectable and connected by typed mappings. Do not add a mandatory formal layer.
- Reuse model memberships for a compact overview, per-network review and selected
  boundary views. Show independent capabilities without a fabricated common path.
  Shared rule dependencies keep their IDs across views and review scopes.
- Add concise on-demand details: meaning, possible states, action changes,
  properties, source bindings, latest evidence and unresolved boundary.
- Highlight a selected property/path across hidden layers using existing typed
  projections; retain the original path instead of inventing a direct physical call.
- Keep actual invocation lifetimes and state intervals consistent between Graph
  and Timeline, including concurrent event groups and actual handoffs.
- Build an analysis-trace adapter for P6: logical steps and value changes, separate
  provenance, loop-back for liveness traces, no invented wall-clock durations.
- Preserve annotations, expanded groups, node/edge exclusions, saved custom views,
  camera and IDs through code/model refresh. Old runtime recordings follow current
  version-selection rules; frozen review artifacts stay intact.
- `/vibelens` uses existing allowlisted scoped controls for view/filter/detail
  operations. It cannot edit business semantics or framework source through a
  graph command. Analysis launch, if added, accepts a validated profile ID and
  bounded options, never arbitrary shell text.

**Exit:** A21/A25/A32/A34 pass in desktop 2D/3D and Timeline, in English and Chinese.
Viewer operation remains usable without the optional analysis dependency.

## P6 — Optional TLA+/TLC adapter

Priority: optional verification backend. Depends on P4; display depends on P5.

Start with booleans/enums/bounded integers, fixed finite object sets, flat state
actions, supported shared rule expressions, bounded FIFO messages and resources.
Model concurrency through explicit interleavings; do not claim arbitrary runtime
thread, callback, database or distributed-system equivalence.

- Generate TLA+ and configuration from the canonical normalized contract and
  selected profile. Retain stable-ID/source maps and deterministic output hashes.
- Mark the initial adapter's subject as `design_model`. A correct design may pass
  while faulty application code fails mapping or business checks. Do not claim
  implementation-model verification without a supported native abstraction and
  independent translation/correspondence evidence.
- Support state invariants and declared transition constraints first. Add a narrow
  progress/fairness subset only with separate supported and rejected fixtures.
- Check model admission before starting TLC: initialization, domains, environment,
  frame conditions, property applicability and unsupported callbacks/operators.
- Select models with their interaction/environment dependencies. A missing related
  network must remain an explicit boundary or unresolved gap, not silently disappear
  from a "complete" analysis because its view was hidden or its questions were skipped.
- Pin a tested TLC distribution/checksum and supported Java runtime. Resolve it
  as a tool dependency using the current download/cache/fallback convention.
  Retain notices; do not copy tools or Java into the user's application bundle.
- Run out of process with explicit argument arrays, time/memory limits, cancellation,
  project-contained artifacts and no production credentials. Preserve stdout,
  stderr, exit status, completion and tool identity.
- Parse actual results; distinguish failed property, malformed model, deadlock,
  intentional termination, timeout, unsupported semantics and partial exploration.
- Map counterexample states/actions back to graph IDs. Retain loop witnesses for
  supported liveness failures. Convert reproducible paths into native regression
  cases; a failed reproduction is a mismatch to investigate, not a suppressed trace.
- Test the translator with hand-derived small state spaces, independently written
  TLA fixtures and semantic mutations. Shared declarations are allowed; the same
  exporter cannot be the sole oracle for its correctness.

**Exit:** A19–A22 pass with actual TLC executions. Removing TLC still leaves the
core observation workflow working. Any deferred semantic subset stays unsupported
and is omitted from release capability claims.

## P7 — Independent trials, cleanup and product delivery

Depends on the phases included in the intended release.

- Use fresh isolated Python and Node project trials, each initially receiving only
  the candidate Skill and a natural user request. New chats require explicit user
  authorization at execution time; this plan does not create them.
- A designated simulated user answers only after being asked, using the trial's
  intended business meaning and conversational language. Preserve questions,
  corrections, confirmations, source snapshots and usage counters when available.
- Complete initial design, implementation, real observation, one semantic change
  and one source-only refactor. Inspect every configured layer and interaction.
- Inspect the initial model inventory and construction dialogue, including independent
  capabilities, different state owners, shared rules and an interpretation corrected
  by the simulated user. Retain graph revisions and the exact confirmed boundaries.
- Diagnose framework/Skill failures at their source; repair the maintained
  package, then repeat in a clean trial. Do not teach only the sample app a workaround.
- Retain failures, fixes and the final complete retest, with screenshots of initial
  graphs, actual replay, drilldown and updated graphs. Mark simulated conversation
  and model-generated traces accurately in the review material.
- Remove replaced production paths only after callers, fixtures and migration are
  covered. Preserve historical evidence. Rebuild managed packages rather than
  hand-editing example/install copies.
- Update the source guide, capability inventory, Skill references and release
  notes. Product pages follow accepted evidence, as specified below.

**Exit:** A24–A34 pass. Merge/tag/publish only when the release is requested; this
planning task does not authorize a release or a new public feature claim.

## Readability and implementation standards

- English code, identifiers, comments, schema documentation and default docs;
  translated user-facing names follow the interface language.
- Document public functions' inputs, outputs, ownership, failure semantics and
  evidence meaning. Explain subtle concurrency/refinement decisions in comments.
- Use typed records for normalized domain data; do not spread unvalidated nested
  dictionary access or opaque booleans across the workflow.
- Thin CLI and HTTP adapters call the same domain services. Diagnostics include a
  stable code, path, affected IDs and a short actionable explanation.
- Keep IO and lifecycle side effects explicit. Tests can exercise core validation
  without starting a server, browser, business app or model checker.
- Use dependency direction checks. Avoid generic `utils` modules becoming another
  owner of model semantics. Add modules only with a clear responsibility.
- Separate behavior changes from formatting/comment cleanup. Existing AST
  equivalence checks support readability-only edits; they do not prove a refactor.
- Scan owned source only. Respect the shared source-scope inventory and preserve
  local modules while excluding dependencies, build output and runtime data.

## Risks and engineering decisions

| Risk | Planned control | Decision owner |
|---|---|---|
| A second description drifts away from the native models | Reference existing definitions, generate derived artifacts, compare confirmed/native semantics | Protocol and binding implementation |
| Role-aware dialogue collects answers without constructing models | Model inventory and obligations first; grouped graph review, optional preference and scoped questions; measure redundant questions and unresolved model obligations separately | Skill workflow implementation |
| Formal export silently drops unsupported code or behavior | Capability admission, explicit unknowns, translation fixtures and separate analysis subject | Analysis adapter implementation |
| State explosion | Estimate profile size, set time/memory limits and report incomplete; preserve the original model | Analysis runner; user only if business meaning must change |
| More checks make each coding batch noisy or expensive | Focused recall, dependency-based selection, measured cold/warm scan and receipt reuse | Workflow implementation |
| Source events give an inconsistent cross-model snapshot | Record actual revisions/transactions and independent reads; report insufficient evidence | Native integration and mapping checks |
| New contract fields weaken legacy strictness | Versioned fixtures and atomic migration; no unknown-field bypass | Protocol/migration implementation |
| Attractive product claims exceed actual support | Link each public claim to accepted cases and package version | Release review |

P1 settles final wire names and normalized record types. P6 pins the actual tested
TLC/Java versions and subprocess budgets. These are engineering choices to record
with evidence; they need not become user questions unless they affect confirmed
business behavior, compatibility or a user-specified constraint.

## Homepage, README and demonstration

Publish this story after the corresponding acceptance gates:

| Product section | Message | Visual/evidence |
|---|---|---|
| Opening | See the logic behind AI-written code / 看懂 AI 写出的程序 | A clean, focused product graph |
| Establish intent | Shape the application's flows, states and rules / 一起理清流程、状态与规则 | Short dialogue, model overview and matching individual business/state/rule networks |
| Inspect execution | Follow a change through the system / 沿着变化逐层查看 | Macro replay followed by one code/data drilldown |
| Iterate | Check what changed / 修改后，核对变化 | One changed region, preserved layout and actual rerun |
| Optional analysis detail | Explore difficult sequences / 检查难遇到的执行顺序 | A clearly identified model counterexample, only after P6 passes |

Homepage copy describes VibeLens's benefits and interactions. Detailed protocol,
agent obligations and finite-model limits belong in technical documentation and
result details. Keep headlines short, screenshots legible and English/Chinese
consistent. Avoid generic defensive slogans, implementation checklists and demo-
specific feature lists in the main product pitch.

Demo outline: request a small file-sharing app → construct and confirm its applicable
business networks, state models and shared rules → run and record → inspect a revoked-but-queued download problem → drill
to the actual permission read/start boundary → describe the problem to the coding
AI → update code and graphs → rerun. The chosen revocation semantics must be
confirmed in that trial; they are not a default business rule imposed by the Skill.

Combine repetitive setup into one scene. Separate coding chat from VibeLens
record/filter/replay interactions. Use prebuilt focused scene data, prefetch the
next scene and show a short loading state; load the full graph only on request.
Screenshots and animations must share the accepted graph IDs and actual records.
Technical/model findings must not be staged as real runtime discoveries.

Update GitHub README, Pages, SkillHub and other maintained metadata from the same
verified capability/release inventory during an authorized release. Do not let a
marketplace describe a newer capability than the installable package contains.
