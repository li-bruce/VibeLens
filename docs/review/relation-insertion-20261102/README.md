# Construction-time relation insertion

The graph builder now has a transactional relation index. Each insert, update or removal decides whether a claim remains an admitted edge, repeats an explicit definition, or is represented by a registered typed path. All original claim IDs, payloads and proof paths remain exportable.

This round implements the reusable module, its design/model construction integration, JSON interface and Skill guidance. Composition requires an explicit declaration; existing graphs without one retain their physical relations.

## Decision boundaries

| Case | Result |
| --- | --- |
| Same ID, identical registration | Idempotent insertion. |
| Same ID, different registration | Error; explicit update required. |
| Different IDs, same explicit definition identity, exact complete context and identical non-display payload | One admitted definition; original alias ID and provenance retained. |
| Explicit conceptual summary with a registered type sequence/transitivity, exact context and complete acyclic proof | Represented by the retained witness path. |
| Direct calls/transfers/transitions, unknown meaning/context, different conditions, independent evidence, relevant cycles or search exhaustion | Retained. |
| Invalid protocol, endpoint, selector, rule or persisted decision | Atomic rejection. |

See the [complete criteria and interfaces](../../../skills/vibelens/references/relation-insertion.md). Context includes scope, revision, fact basis, bindings and conditions. Comparisons preserve JSON types. Neither labels nor reachability alone establish equivalent meaning.

## Implementation map

- [contract.py](../../../skills/vibelens/scripts/bo_observer/graph/relations/contract.py): portable values, strict rules and registration meanings.
- [paths.py](../../../skills/vibelens/scripts/bo_observer/graph/relations/paths.py): bounded typed search and retained-leaf proof expansion.
- [index.py](../../../skills/vibelens/scripts/bo_observer/graph/relations/index.py): transactional API, re-evaluation, stable IDs and validated export/restore.
- [model.py](../../../skills/vibelens/scripts/bo_observer/graph/relations/model.py): authored graph/discovery construction and revalidation.
- [bo_relations.py](../../../skills/vibelens/scripts/bo_relations.py): atomic standalone/project JSON operations.

`BODesign` uses this index when `discovery.json` explicitly declares relation rules. Ordinary discovery behavior is unchanged. Existing model and project validators independently reconstruct attached decisions. Physical source/state/data projector additions retain their original checks. The Skill now routes authored relations through this interface and documents the exact criteria.

## Evidence

The new [24 unit cases](../../../tests/test_relation_insertion.py) cover duplicate identity, physical-edge retention, exact contexts, typed/nested proofs, insertion permutations, update/removal restoration, cycles, bounds, atomic rollback, persistence tampering and portable values. Six randomized insertion orders of a complete 10-node conceptual DAG must yield the same consecutive witness chain.

The new [11 integration cases](../../../tests/test_relation_integration.py) cover actual `BODesign` construction, a changed witness in an iteration, malformed discovery, legacy compatibility, both model validators, unchanged native executor output, actual probe-to-collector delivery, external physical facts and atomic JSON commands.

The [six-step exercise](insertion-exercise.json) saves actual registries before/after a path arrives, duplicate registration, independent evidence, witness removal and a rejected ID conflict. Its [reproducer](exercise.py) uses the public API. [Failures and repairs](failures.md) retain the issues found before the successful retests.

Reproduce from the repository root:

```bash
.venv/Scripts/python.exe -B -X utf8 docs/review/relation-insertion-20261102/run_checks.py focused
.venv/Scripts/python.exe -B -X utf8 docs/review/relation-insertion-20261102/run_checks.py quality
.venv/Scripts/python.exe -B -X utf8 tools/verify.py --database
```

All 35 new tests passed. The original complete release gate (`tools/verify.py --database`) passed on 2026-11-02, from 07:42:43 to 07:50:37 UTC. Both managed examples completed verify/accept/check and were frozen before this run. The package check confirms 147 synchronized runtime modules. Source checks cover 133 Python and 94 JavaScript modules. The two new suites extend the release gate; every previous check remains.

Machine-readable results: [acceptance summary](acceptance.json), [unit](unit.json), [integration](integration.json), [complete gate](full-gate.json), [source quality](source-quality-report.json), [managed examples](relation-insertion-20261102-verification.json), [core preservation](core-preservation.json). Full outputs are in `full-gate.stdout.log` and `full-gate.stderr.log` in this directory.

The physical-only batch measurement inserts 3,000 relations using this machine's Python environment; exact timing is in [unit stdout](unit.stdout.log). It measures graph construction, not UI frame rate or a runtime latency guarantee. Search exhaustion retains claims.

No native business rule, state-machine definition, executor or recording is rewritten by this module. Six protected core source hashes remain identical. No publication, merge or version change is part of this round.
