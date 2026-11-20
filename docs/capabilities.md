# Capabilities and implementation scope

[Product overview](../README.md) · [Source guide](source-guide.en.md)

| Area | Implemented capability | Useful detail |
|---|---|---|
| Concept models | Multiple business/state/rule networks, shared members, confirmation and semantic-drift checks | Independent components are valid; explicit crosslinks connect related capabilities. |
| Development modes | Drive or observe, independent project state module, external observer | Native Python/JS `bo.fsm/1` executes a strict flat subset; richer engines need an adapter. |
| Source | Python and JS/TS inventories, React/Vue entry points, project tree, symbols and source highlighting | Dynamic targets remain unresolved until supported by evidence. |
| Runtime | Selected values, invocation lineage, state changes, decisions, database operations | Recording covers configured probes and adapters. Capture health reports missing events. |
| Storage | Relational, document, key-value and graph-store structure and operations | SQLite, PostgreSQL, MongoDB, Redis and Neo4j have retained real-runtime checks. |
| Viewer | Desktop 2D/3D graph, custom views, stable-ID layout and notes, live/recorded playback and timeline | Concept, source and runtime identity remain distinct and linked. |
| Hosts | Codex Skill and packaged DeepSeek Harness provider | The Harness compatibility version and actual checks are listed in its guide. |

Current display planes are business, states, rules, entry points, project
structure, code execution and storage. They are selectable views of one typed
network. A focused function, a declared state and one runtime invocation retain
their own identities and explicit mappings.

The agent-managed iteration workflow restores requirements, scans owned source,
reconciles mappings and probes, then runs checks. File watching detects change;
the coding agent performs semantic reconciliation and repairs. Repository,
dependency, build and runtime-data boundaries stay explicit.

The `model.machines` registry binds every confirmed state model independently.
Model-qualified state snapshots, names, instance queries, exports and replay keep
identical local state/instance names separate. Each layer can expose named
subnetworks through the normal view menu. See [model networks](../skills/vibelens/references/model-networks.md)
and this branch's [acceptance record](review/model-networks-20261112/README.md).
The portable executors still implement the strict flat subset; registration does
not establish cross-model transactions or universal invariant verification.

The prior independent trial's capture/recording findings remain preserved in its
[assessment](review/clarity-story-20261105/TRIAL-ASSESSMENT.md). Product and packaging
regressions do not establish universal application correctness.

## Behavior-contract development branch

The [ordered plan](development/behavior-contracts/implementation.md) has completed
P0–P6 implementation and regression. P7's independent native trials and product
delivery remain in progress; the [execution ledger](development/behavior-contracts/progress.json)
records the evidence and current status. This section describes the development
branch, not a completed release acceptance.

| Area | Implemented behavior | Evidence boundary |
|---|---|---|
| Model construction | Inventory independent capabilities, state owners and shared rules before binding source | Missing-model obligations remain open even when no questions are pending. |
| Dialogue | Optional role/depth preferences, grouped questions, partial answers and scoped graph confirmation | Implementation facts go to the coding agent; its recommendation does not become user confirmation. |
| Behavior definitions | Versioned typed facts, actions, parameters, effects and frame conditions | Invalid references, types and unsupported bound semantics fail validation. |
| Native correspondence | Source-bound state, decision and effect witnesses with actual invocation ownership | Static mapping, runtime capture and business outcomes have separate results. |
| Iteration | Restore durable obligations, compare semantic dependencies and expire affected evidence | Unchanged display text can reuse evidence; changed meaning or source bindings require the relevant checks. |
| Optional finite analysis | Explicit finite domains and assumptions, pinned TLA+/TLC adapter, preserved logical counterexamples | Checks the admitted design subset. Native implementation correspondence requires independent runtime evidence. |
| Inspection | Original model identities connect definition details, runtime replay and logical analysis | Logical steps carry no invented runtime duration; actual producer clocks retain their own ownership. |

See the [source guide](source-guide.en.md) for module
ownership and the [acceptance matrix](development/behavior-contracts/acceptance.md)
for the required native, iteration and desktop checks. Capture capacity is an
explicit finite transport budget; overflow remains a reported gap and cannot
silently produce a complete-recording result.

[Protocols](../skills/vibelens/references/multilanguage.md) ·
[Recording](../skills/vibelens/references/recorded-analysis.md) ·
[Database support](../skills/vibelens/references/database-observation.md) ·
[Source scope](../skills/vibelens/references/source-scope.md)
