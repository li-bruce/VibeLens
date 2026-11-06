# Coding-batch obligations

For a new project, follow [First project setup](project-setup.md) to assemble the
source-free confirmation, executable baseline and independent verification commands.

For a later business request, first follow [iteration dialogue](iteration-dialogue.md): restore confirmed decisions, locate the affected graph region and its boundaries, show the proposed local change in conversation and Web, and resolve only new or changed business meaning before implementation. Reuse explicit confirmations of the same scope. Source-only refactors keep their business meaning and update mappings without repeating business questions.

Connect these commands to the project's verification entrypoint. Conversation guidance applies only after explicit adoption in that conversation; project instruction files must not silently activate the skill elsewhere. The AI runs the commands; the user does not maintain intermediate files:

```text
change_sync begin -> coding and local generation -> bo_sync scan -> change_sync inspect
-> resolve confirmations and implementation review -> change_sync verify -> accept -> check
```

Before every coding turn, run `change_sync.py recall --root PROJECT` and read its concise output. It restores mode, current request, protected contracts, observation-module paths, affected layer nodes and verification commands from project files. `begin` also produces this recall automatically. Detailed per-layer sources, fields, lifecycles and cases are in `.stategraph/observation-plan.json`; inspect only affected entries. Recall does not accept source changes. See [observation continuity](observation-continuity.md).

Read the recalled `framework` integrity result. Use the installed Skill's commands;
edit project-owned definitions/wiring through the [integration boundary](integration-boundary.md).
Maintain affected [conceptual route references](concept-flow-layout.md) when the
confirmed graph changes. Dependency tampering is a framework failure, independent
of business outcomes and graph coverage.

Commands require the project `--root`; `begin` also needs `--change` and the actual request. Continue an active change instead of replacing its baseline to hide drift. See [continuous development](continuous-development.md).

For an empty project, first use the [source-free concept workflow](concept-models.md)
to preserve confirmed meaning. Source recall and `begin` start once the first
parseable scaffold and bindings exist. Its initial review still runs all source,
runtime and business checks; later iterations must begin before editing.

Record confirmed requirement statuses and the actual allowed requirement IDs before `begin`. Keep the resulting baseline bytes immutable, including scope metadata; missing metadata is a failed initialization.

`bo_sync scan/watch` discovers new, changed, and deleted files independently of nodes already in the graph. Python, JS/TS, React, and Vue adapters produce common source facts. Missing parsers, syntax errors, and unsupported languages are explicit gaps. Watch produces maintenance tasks; the host or active coding AI must consume them. It cannot wake arbitrary editors or agents by itself.

Review source ownership when new directories, dependency/output paths or `.gitignore` change. Apply the same scope to graph, API, documentation and completeness checks; reject physical bindings into pruned storage while retaining hashed configuration and review inputs.

The optional [code structure](code-structure.md) is derived from that independent scope. Once enabled, refresh it during maintenance and verify its saved nodes, relations and file hashes against current source. Keep its source revision distinct from the running application's build. Preserve unresolved calls; never infer runtime execution from static edges. Include recognized API entries and handler links, and verify explicit business/state links rather than joining similar labels. See [graph evidence](types-rules-capture.md#readable-graph-evidence) for capture fields, source parameters and relation meaning.

Configured data projects also refresh their native model exports and database metadata during `bo_sync scan/watch`. `bo.py serve` watches configured data and reloads validated graph builds automatically. The native development launcher must reload its producer with the new build identity; old-build events remain rejected. `bo_db.py check` and `change_sync verify` independently recompute data mappings and require executed cases. A failed collector leaves the previous graph marked stale; never accept it as current.

Read `confirmations.user` and `confirmations.coding`. Ask users only about unresolved business meaning; reconcile unresolved calls and implementation changes within coding. Configure `reconciliation` records when dynamic bindings need protection. Stale source answers, absent targets, and missing verification cases must fail; records do not replace actual value and call checks.

Map all implemented features, including later login, messages, queries, configuration, and frontend actions. Give entrypoints, parameters, helpers, and runtime cases a traceable place in the graph. Collapsing a feature is not excluding it. Static edges are candidates; capture actual calls, decisions, state changes, and effects at their execution boundaries. Do not invent results for conditions skipped by short-circuit evaluation. See [source isolation](source-isolation.md) and [semantic probes](semantic-pins.md).

Use `bo_` for observation wiring and `BO` for adapter classes; keep domain names for business methods. Select fields explicitly. Never collect credentials, tokens, or arbitrary bodies. Isolate builder, transport, and storage failures; bound queues. Events identify project, model, build, run, producer, entity, call, and parameter version. Internal rule, state and value facts retain their actual enclosing invocation, including when file identities differ. Enable protected `require_observation_closure`; missing ownership fails mapping. Source-bound external point notifications may declare `observation_root`, as detailed in [observation continuity](observation-continuity.md). Arrival order across processes is not causality. Use application/entity scope for features such as login outside a selected task.

At node construction, register existing lifecycle meanings with `lifecycle.states` and explicit event/value `bindings`. Clarify uncertain business meanings with the user and implementation bindings with coding. Otherwise use neutral entry, wait/resume, return and exception observations; a return or exception does not establish business success or failure. A broad exception class cannot establish a specific outcome such as permission denial; capture the actual cause or retain the generic exception. Preserve real call ownership, including detached work with its own interval. Graph and timeline share these facts. Keep independent semantic and source parameter IDs connected by explicit `represents` mappings. Follow [lifecycles and representations](lifecycles-and-representations.md); test registered meanings against actual captured values, timed bars, same-track and cross-layer links, live inspection and recording without business writes.

Collection, reporting, polling, source viewing, layout, and recording controls must not produce business events. Exclusions need exact source and identity. Split mixed business/observer handlers rather than exempting them wholesale. Preserve real login, message, and state-change capture. See [observer exclusions](observer-exclusion.md).

Track source moves explicitly, preserving node identities, parameters, and assertions. Generate from canonical sources and check installed copies. Do not reset capture baselines, fabricate events, or relax expectations to remove failures. Keep personal layouts in `bo_stategraph/config/views/local.json`; upgrades must preserve them. See [source migration](cochange.md).

Keep project, node, and relation IDs stable across iterations. Use explicit `presentation.node_aliases` / `edge_aliases` for one-to-one renames; retain dormant personal settings and migration conflicts. Do not derive identity from labels, source line numbers, or build versions. A changed title is not a new project.

Route authored relation construction and updates through the [relation insertion](relation-insertion.md) interface. Register exact context, duplicate identity and permitted conceptual compositions from confirmed declarations. Keep physical execution facts direct. Missing meaning or evidence retains the edge; invalid or conflicting registrations stop the batch. Preserve raw IDs and witness paths, and check restoration after a witness changes or disappears.

Focused capture selects value builders and retains minimal witnessed caller boundaries. Unselected inputs and results remain uncollected; boundary metadata adds no ordinary replay steps. Disclose any remaining partial ownership without inferring parents or claiming full capture. See [observation continuity](observation-continuity.md#focused-values-and-execution-context).

Update affected source explanations with each coding batch. Run `bo_code.py docs --root PROJECT --strict` for new projects' mapped scope and keep it in their verification entrypoint; adopted code reports missing explanations while retaining complete mapping and all existing checks. A missing comment cannot be replaced by an AI label or a fabricated source reference.

For HTTP applications, also run `bo_code.py api-check --root PROJECT --strict`. Bind observed requests by actual handler source, method and route; verify their intervals in Graph and Timeline, including routes sharing a handler. Keep this gate in new projects so adding an unregistered API cannot silently lose observation.
