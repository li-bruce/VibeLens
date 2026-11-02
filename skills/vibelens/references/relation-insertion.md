# Construction-time relation insertion

Use `bo_observer.graph.relations.RelationIndex` when constructing or changing authored graph edges. The index makes the decision inside each insertion transaction. It does not reduce a rendered graph, alter the executable state machine, or rewrite runtime facts. Node and edge IDs stay fixed.

## Exact decision criteria

| Result | Required conditions |
| --- | --- |
| Idempotent insert | The same edge ID and the entire registration are identical. |
| ID conflict | The same edge ID has different registration content. Reject; use an explicit update. |
| Duplicate definition | Different IDs have the same explicit `definition_key`, a complete identical context, the same registered relation, independent flag and entire edge payload except `id`, `label`, `summary`. Endpoints, type, arguments, source location and event/trace evidence therefore must agree. Keep the first registered ID and retain the later ID as an alias in the registry. |
| Represented summary | The edge is explicitly registered as a conceptual summary; an allowed typed composition or transitive summary path exists; every edge has exactly the same complete context; no independent witness or relevant cycle exists; bounded search and witness expansion complete. The proof must end at retained edges with continuous endpoints. |
| Retained edge | Every other valid registration, including unknown meanings, missing context, different bindings/conditions, unmatched compositions, independent source/runtime evidence, relevant cycles or exhausted search budget. |
| Invalid declaration | Missing endpoints, undefined relations, wrong selectors, unsafe summary fields, cyclic composition definitions, malformed JSON, stale persisted decisions or invalid mutations. Reject the entire transaction. |

The exact context fields are `scope`, `revision`, `basis`, `bindings`, `conditions`. All five must be present and non-null; the three string fields must be nonblank. Empty binding/condition objects explicitly mean no extra binding/condition. Omission means unknown. Equality is type-preserving JSON equality: `false` and `0` differ. Contexts are compared, never solved or broadened by the AI.

Direct calls, actual parameter transfers, business branches, state transitions, guards, resource/join relations and immediate containment remain direct facts. Do not declare them transitive or convert them to summaries. Permissions require their existing policy declaration and actual evaluation; reachability does not establish authorization. Similar names, layers or endpoints cannot establish redundancy.

## Portable rules and registrations

The strict contract is [relations.schema.json](../scripts/bo_observer/schemas/relations.schema.json). A rules document has `schema: bo-relation-rules/v1`, `definitions`, and `compositions`. Each definition has an ID, `mode: direct|summary`, and an exact `match` selector. A summary selector must be:

```json
{"type":"maps","origin":"relation-summary","semantic_relation":"uses-data"}
```

The `semantic_relation` must match that definition's ID. Summary payloads permit identity, labels/descriptions, declaration evidence, source references and presentation metadata. Independent `source`, `callsite`, call/trace/span/event witnesses or `observed: true` retain the claim. Physical/execution fields are rejected in a summary. A direct definition cannot declare transitivity. Composition results must be summaries, with an explicit sequence of 2–8 relation IDs. Composition definitions cannot recurse; a transitive summary uses its explicit `transitive: true` flag.

For example, register direct `implements` and `reads` relations, then declare `implements + reads -> uses-data`. A business-to-table summary may then be represented by business-to-function-to-table, provided the exact context agrees. That declaration does not make a direct call or a state shortcut redundant.

Each inserted entry has `edge` and optional `relation`, `context`, `definition_key`, `independent`. Every edge needs `id`, `from`, `to`, `type`, `evidence`. Copy evidence from the actual declaration or source binding; do not invent context or duplicate identity to obtain a smaller graph.

```python
from bo_observer.graph.relations import RelationIndex

index = RelationIndex(node_ids, rules)
result = index.insert(registration, expected_revision=index.revision)
decision = index.decision(registration["edge"]["id"])
admitted_edges = index.edges
portable_registry = index.export()
```

Use `apply([...])` for a coding batch; it applies insert/update/remove operations atomically. `update` keeps the same ID. `remove` revisits prior summaries and duplicate aliases. Node removals in an API batch must remove their incident claims too. A late witness can represent an earlier summary; changing or removing its witness restores it. Search is bounded by `max_work` and `max_candidates`; reaching a limit preserves the claim. Batch insertion is preferable to repeatedly rebuilding a large physical inventory.

The export includes every original entry, rules, decisions, canonical edge IDs and a revision. A represented decision includes the matched rule, path claim IDs and expanded retained `leaf_path` IDs. `restore()` recomputes decisions and rejects stale or altered exports. This is consistency validation, not authentication of user-supplied rule truth.

When composition declarations change, construct a new index from the original export's `nodes` and `entries` with the new rules, then publish through the normal graph-building transaction. Rebuilding from admitted edges alone would lose represented claims and duplicate aliases.

## Graph-building and file interfaces

`relations.model.construct(model, rules, registrations=...)` constructs admitted edges and `model.relation_registry` together. Registration metadata is keyed by edge ID and cannot replace its physical payload. Existing graph/project validators recompute an attached registry. Additional physical source/state/data projector edges remain intact and retain their existing validators; their meanings are not inferred by this module.

For the design-stage graph, put `relation_rules` in `discovery.json` and optional `relation_registration` metadata on each declared edge. Use `relation: maps` for a conceptual mapping. `BODesign` uses the same construction module after checking discovery references and maps exact node IDs. Registrations without rules, malformed rules and a physical flow marked as a summary fail discovery validation. An ordinary discovery document retains its original behavior without new metadata.

The CLI reads a standalone graph or a `bo-project/v1` envelope, keeps normal graph/state validators, and writes atomically under a project-local lock:

```bash
python SKILL/scripts/bo_relations.py init --root PROJECT --model behavior.json --input review/relations-init.json
python SKILL/scripts/bo_relations.py batch --root PROJECT --model behavior.json --input review/relations-batch.json --expected-revision REVISION
python SKILL/scripts/bo_relations.py check --root PROJECT --model behavior.json
```

The init file contains optional `rules`, `registrations`, `limits` objects. A batch file is an array, for example `[{"op":"remove","id":"summary-1"}]`. Insert/update payloads use the registration object; remove takes `{"id":"edge-id"}`. A graph-building source remains authoritative: update its declarations too, then run normal generation and mapping checks. The CLI does not accept a coding batch or refresh source fingerprints. Viewer operations and business execution never invoke these mutations.

## Required checks

Run `tests/test_relation_insertion.py` and `tests/test_relation_integration.py` in this repository. They cover exact duplicate criteria, forbidden contraction, typed and nested proofs, insertion order, context changes, independent evidence, cycles, budget exhaustion, rollback, concurrent revision rejection, persistence tampering, actual design construction, iteration restoration and native execution equivalence. These tests join the original release gate; they do not replace it.
