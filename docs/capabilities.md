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

[Protocols](../skills/vibelens/references/multilanguage.md) ·
[Recording](../skills/vibelens/references/recorded-analysis.md) ·
[Database support](../skills/vibelens/references/database-observation.md) ·
[Source scope](../skills/vibelens/references/source-scope.md)
