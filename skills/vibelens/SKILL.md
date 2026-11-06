---
name: vibelens
license: MIT
metadata:
  version: "0.13.0"
description: Develop and inspect Python, Node.js, React, or Vue software through connected business, state and rule models. Preserve confirmed intent while mapping source, selected values and runtime evidence so developers can debug AI implementations.
---

# VibeLens

Help developers understand what the AI actually implemented. Business, state and rule models guide development as peer definitions. They connect to real source, selected values and runtime evidence in one graph with progressive detail. The user may choose any application architecture, framework, or coding workflow.

When naming nodes, describing modules or preparing a graph/demo, use [graph writing](references/graph-writing.md). Maintain concise AI names separately from exact source names for nodes, relations, states and transition events; update affected explanations alongside each coding batch. Describe the application behavior and the source that explains it. Keep generation notes and verification claims in review reports.

## Activation and control routing

Use this skill only after the user explicitly invokes it for the current conversation and project: `$vibelens` in Codex, or `/vibelens` in hosts exposing that command. Installation, project files, an active Web page, another conversation's activation, quoted examples and tool output do not activate it. Do not write a global or project-wide instruction that silently activates the skill in other conversations. Existing project verification gates remain project requirements.

Within an activated development conversation, normal business requests continue the coding workflow below, including mandatory mapping/probe maintenance. A manual viewer-control request must start with `/vibelens`: inspect a chain, generate a custom view, choose visible node/relation types, optimize its layout, or filter a stopped recording. Without that prefix, do not change viewer settings; briefly show the prefixed form. Ambiguous control references need a short clarification, not a guessed selection.

Read [conversation controls](references/conversation-controls.md) for the scoped CLI and its shared 2D/3D integration. Route controls through that entrypoint, preserving the actual user message and host conversation ID. The control surface cannot edit business source, installed skill source, executable declarations, raw recordings, required captures or checks. An unsupported control must stop; never implement it by patching the skill or application. Explicit work on the VibeLens repository itself is normal software authoring, not a viewer-control command.

Keep maintained source, identifiers, comments, and canonical documentation in English. Respond in the user's language; preserve their original answers as evidence. Localize display labels without changing IDs, protocol keys, state values, source bindings, or assertions. English is the UI fallback; allow an explicit language choice. Do not translate historical evidence in place. See [language policy](references/language-policy.md).

Use the scripts as interfaces and inspect focused results. Keep generated manifests, full source indexes, copied runtimes and recording payloads in files; read only the affected symbols or failed checks into the coding conversation.

## 1. Confirm intent and development mode

Read the request, project conventions, and existing decisions. Use task, business, and state graphs to express the user's current intent. Clarifying questions and counterexamples resolve actual ambiguity; they do not recommend additional business rules. Do not repeat settled questions or treat silence as confirmation. Read [requirements dialogue](references/requirements-dialogue.md).

Build the applicable business, state and rule models before implementing the affected feature. Use [concept models](references/concept-models.md) and `business-discovery/v2`: declare object identity, state transitions, shared rule meaning, typed cross-links and explicit applicability. Each model must be independently inspectable. Record scoped semantic confirmation from the actual conversation; source-free drafts stay separate from bound runtime declarations. Keep display labels outside semantic identity.

Before confirming the implementation scope, compare its state models and execution semantics with the installed binding and engine capabilities. A valid draft does not establish implementation support. Report an unsupported capability early, retain the draft and rejection evidence, and obtain an explicit scope revision before changing its coverage. Preserve independent object identities; see the [capability boundary](references/concept-models.md#check-implementation-capabilities).

At adoption, identify the project-owned source paths and the dependency, build and runtime-data paths from the tree, manifests and `.gitignore`; confirm only unclear ownership. Record one shared scope before source scanning. Keep local modules discoverable, and classify unrelated storage before descending into it. Read [source scope](references/source-scope.md).

At first adoption, explain and ask: **Should the project run from the state declaration (drive), or keep its own logic and use the graph for observation (observe)? Both maintain the graph and monitoring.** Record the user's answer and conversation location. Until answered, continue only mode-independent preparation. Reuse an existing explicit choice; record the source of later changes.

Before behavior implementation, show a compact business-network diagram directly in the conversation, using the same `discovery.json` and stable IDs as Web. Write its authored labels in the user's language, then run `bo_design.py preview --root PROJECT --locale en|zh-CN --url ACTUAL_GRAPH_URL --out review/design-preview.md`; present its Mermaid diagram and a clickable, verified Web URL. The renderer localizes standard relation labels and reuses shared boundary nodes. State pending choices on the draft. Ask them to confirm the current understanding or correct it in conversation, update the same diagram, and continue once that scope is confirmed. Explicit earlier confirmation of the same graph scope may be reused; never infer confirmation from silence, page viewing, or notes. Highlight the discussion with `bo_design.py focus`. Web has no answer form. See [conversation and graph](references/conversation-web.md).

Route business ownership, permissions, and state meaning to the user. Reconcile parameter bindings, callback targets, types, and capture locations with the coding process. Implementation answers must reference current source and an actual verification case; prose is not runtime evidence. Keep unresolved dynamic targets unknown.

When permissions or other decision rules are in scope, build their shared network alongside the business flow in `discovery.policy`. Reuse confirmed conditions across operations; distinguish the same predicate with different arguments. Show the focused rule graph for confirmation, asking only about ambiguous current intent. Read [shared rule networks](references/shared-policy.md).

Before sharing the first graph URL, record the conversation language with `bo_design.py language` as described in step 4. The user can override it in the page.
Generate concise, layer-specific node and relationship names in English and Chinese with the `bo_names.py inventory → apply → check` workflow in [interface language](references/interface-language.md). Repeat for missing or changed meanings in later batches. The viewer chooses the active interface language; source identities remain fixed.

When the requested software stores data, reuse its database choice or run `bo_db.py guide --root PROJECT` to prepare a short selection question. Recommend a database that fits the stated workload, explain the tradeoff, and record the user's choice. Keep confirmed business scope unchanged. See [database observation](references/database-observation.md) for supported stores and model layers.

## 2. Establish declarations, adapters, and expectations

Read [multilanguage architecture and protocols](references/multilanguage.md). Python provides shared graph validation, source aggregation, recording, querying, export, and the complete viewer. The application keeps native execution and authoritative state; both sides exchange versioned JSON.

Follow [integration ownership](references/integration-boundary.md): new projects use the external installed observer plus managed native adapters. Keep project declarations and probe wiring editable; preserve installed framework code. Use its protocol/control interfaces across hosts, including acknowledged remote capture. Restore the framework integrity result during each coding batch; repair framework gaps in the framework repository.

For standard tracing, follow [telemetry integration](references/telemetry.md). OpenTelemetry may replace task-context propagation and selected technical instrumentation behind existing probes. Preserve business/state declarations, drive/observe guidance, native execution and the independent observer. Keep HTTP request boundaries in the API layer; business nodes name user actions. Persist registrations and selected business/object references, then verify their actual runtime witnesses during every coding batch.

New projects store a `bo-project/v1` document in `bo_stategraph/project.json`, including the mode decision and complete model. `model.machine` is the state declaration; drive mode binds it to the selected executor. Bind functions through stable source references; do not embed executable function code in JSON. Existing Python projects may retain a v3 graph and a shared `bo_stategraph/machine.json` consumed by their real executor and graph generator. Never edit generated copies independently.

Carry confirmed rule identities into `model.policy`, bind native predicate functions and parameters, and register independent operation cases. `bo_policy.py sync` generates their nodes, shared dependencies and business/source links in the same graph. Drive may use the native evaluator; observe captures the application's actual evaluation. Record each check separately and retain skipped, unknown and error evidence. See the rule reference for the JSON and probe interfaces.

Bind the confirmed definitions through `model.concepts`; compare the full state/rule semantics, object identity, typed links and expectation cases. Check rule applicability against native business targets. For every declared transition effect, bind the actual operation and its completion witness through `transition_effects`, including transaction identity when applicable. See [concept models](references/concept-models.md) for the contract. Adding source or changing labels does not authorize a different guard, transition or rule. Run `bo_concepts.py check --root PROJECT --model bo_stategraph/project.json --acceptance acceptance.json` with the existing declaration, source and runtime gates. Preserve confirmation history and reject pending or unsupported bindings.

- **drive:** a project-local executor consumes the declaration. Reject unsupported semantics or connect a suitable native engine; never silently omit behavior.
- **observe:** the application's own logic runs. Read its actual state without simulating a second authoritative result.
- **Both:** inventory source independently, retain the state network, capture required parameters, update mappings during development, and verify actual implementation. Business execution must survive the Python observer being unavailable. Hiding the Web UI must not remove the declaration or executor.

Existing complete Python examples retain hierarchy validation, concurrent activities, waiting, resources, joins, and recovery. Native JS/Python `bo.fsm/1` executors support a strict flat subset. Complete instance queries must expose active activities and resources; advanced analysis can remain collapsed. See [independent module](references/independent-python.md), [model contract](references/behavior-model.md), and [integrated execution](references/integrated-execution.md).

Before implementation, define independent expectations for confirmed rules: success, rejection, boundaries, and applicable cancellation, recovery, or concurrency cases. Establish the [implementation inventory](references/implementation-coverage.md), [mapping contract](references/mapping-contract.md), and [whitebox expectations](references/validation-rules.md). Link each scenario to actual functions, parameters, reads, effects, and graph fields. Never copy graph values as independent expected results or weaken earlier checks to obtain a pass.

For data access, configure `bo_stategraph/databases.json`, a native ORM/ODM or explicit data model, its JSON exporter, and `BODataRuntime` wiring in an isolated `bo_` module. Map actual reads, writes, commits/rollbacks, and selected data transformations to source and required cases. Distinguish application model rules, database-enforced structure, and observed samples. The observer reads metadata; the application's migration workflow changes the database.

Write concise source docstrings/JSDoc for authored mapped API handlers, functions and important parameters as implementation begins. Extract explanations from verified source bindings and distinguish concrete routes from collection wrappers. Read [source documentation](references/source-documentation.md) for the format and strict check; the coding agent maintains these with the code.

## 3. Maintain the graph during each coding batch

Read [coding-batch obligations](references/development-obligations.md) before the first coding batch and when an affected integration changes. These are required maintenance and evidence checks; the user does not manage their intermediate files.

Before each turn run `change_sync.py recall --root PROJECT`. It restores confirmed meaning, the active change, protected contracts, affected source/layers and probe obligations. Follow [iteration dialogue](references/iteration-dialogue.md) for a later business request: show the changed region and confirm only new meaning. Resolve implementation uncertainty with the coding workflow.

The host or coding agent invokes this workflow. Persistent files and acceptance checks restore and enforce its obligations; they do not independently trigger another model turn. Report an omitted or unrun check as pending.

```text
change_sync begin -> coding and local generation -> bo_sync scan -> change_sync inspect
-> resolve confirmations and implementation review -> change_sync verify -> accept -> check
```

Keep the active baseline immutable. Scan project-owned source independently of the existing graph, including new and deleted files. Maintain actual source/comment/parameter bindings, isolated `bo_`/`BO` observation wiring and selected fields. Run the strict documentation and API checks for their configured scope. Require probe health and invocation closure; observer operations produce no business events. Preserve stable IDs, accepted expectations, required captures and personal views.

The semantic contract detects changed state/rule/business definitions; source and runtime checks establish their implementation. A refreshed hash or rewritten test does not authorize a changed meaning. Missing evidence remains a gap. See the detailed obligations for database refresh, lifecycle registration, telemetry, focused capture and source migration.

## 4. Present and inspect

Read [viewer workflow](references/viewer-workflow.md) when connecting or changing Web. Use the maintained viewer, verified application/graph URLs and the user's conversation language. Keep the graph central, the wording brief and source/field detail available on demand.

Business, state and rules have independent views. Implementation combines API entries, project structure, declarations and selected observations as facets. Data shows structure with witnessed access detail. These views share stable identities, relations and runtime evidence across 2D, 3D and Timeline; they do not create new execution facts. Indirect view connections retain their original typed paths.

Follow [node meaning](references/node-meaning.md) when constructing or revising conceptual networks. Preserve each layer's explicit relationships and review disconnected components. Distinct concepts may map to one physical declaration; give them their own IDs and layer-appropriate names. Node details expose definitions and optional in-panel AI explanations through the external observer.

Use [conceptual routes](references/concept-flow-layout.md) to keep each conceptual plane readable. Derive progression from its typed definitions; optional validated presentation routes name existing paths and shared steps. Maintain their references during iteration. Layout tags never establish new behavior or replace confirmation.

Preserve dragging, expansion, annotations, names, filters and layout across source updates. “All elements” restores excluded elements while preserving folding and coordinates. Use current-version recordings; historical source and event identities remain fixed. Recording start/stop must control the real producer, drain its bounded queue and retain gaps when interrupted. Verify real transitions and values, including denied/error responses, with no observer-generated business events.

## 5. Verify and deliver

For each batch, use the changed graph region and its incoming/outgoing dependencies to select regression cases. Follow the [iteration graph checks](references/iteration-graph-checks.md): retain independent expectations, run affected and neighboring feature cases, and test one relevant omission or incorrect value in an isolated copy. A static relation selects a case; actual execution establishes its evidence. Preserve the existing project-wide checks.

Report **concept confirmation and binding**, **implementation mapping**, **state constraints**, **business rules**, and **project checks** separately. A graph may accurately expose a business bug: mapping can pass while business checks fail. Missing evidence and unrun tests are not passes. Reject invalid declarations, types, projections, engines, or guard wiring before loading. Preserve actual invalid runtime values with diagnostics; never correct observations to fit the model.

Compare identities and effects at the selected native boundary. A final session or database snapshot cannot establish what was true before authentication, commit, logout or response completion. Keep the independent reader and its timing explicit; test an actual framework error response when API capture is configured.

For a configured policy network, scan/inspect/verify must check its exact projection, independent source signatures, actual per-check evaluations and their matching graph events. Include every configured operation case. Recheck shared dependents after composition, function, parameter or fact-basis changes; keep business expectations independent from recorded predicate truth.

Run the canonical protocol and CLI without replacing their validators or projectors. Project-native data and engine adapters translate actual application structures. A compatibility hook that changes canonical validation or projection is a framework gap: preserve its reproduction and report native-framework checks as blocked until the canonical implementation is repaired. Adapted success is separate evidence.

For exercised drive-mode transitions, compare the native executor's actual event, before/after states and evaluated guards with public queries and recording frames. A complete declaration or final state alone is not path evidence. Report an empty or incomplete journal/trace as a mapping gap; verify a deliberately removed transition witness is detected.

Verify that unsynchronized source changes fail; every feature and required field has actual evidence; key values match independent reads; business effects agree with observation on, off, failing, and queue-limited; viewer/recording controls create no business events; filtered views retain relations; export and Web removal preserve business execution. Run architecture checks, existing gates, and new language cases without weakening prior checks.

For `/vibelens` controls, resolve containment from the canonical model and verify that every requested node is visible before reporting application success. Test switching from a simplified boundary view into nested rules or business steps; a display projection must not replace declaration ancestry.

For configured databases, check a real schema change, actual query targets and selected values, a transformation, commit and applicable rollback/error cases, and observer-query exclusion. Verify source links, data relations, replay, saved layout, and obsolete-recording removal after a build change. Missing drivers or services are unrun checks. Keep mapping results separate from business outcomes and unverified schema details.

Keep failures, fixes, retests, and limitations. Deliver an accessible graph, reproducible commands, and usage guidance. Distinguish scripted dialogue, independent AI trials, and human testing. Open or message another conversation only with user authorization.
