# P1 contract interfaces

This is the development branch's implemented wire/API reference. Consult
[progress.json](progress.json) for the phase verdict and executed evidence.
These interfaces do not change the native application's execution authority.

## Canonical documents

| Document | Implemented purpose |
|---|---|
| `business-discovery/v1` | Existing legacy checks; no invented conceptual confirmation |
| `business-discovery/v2` | Existing strict business, state, policy and binding definitions |
| `business-discovery/v3` | V2 semantics plus construction targets, obligations and scoped presentations |
| `bo-project/v1` | Existing project selection and native model envelope |
| `bo-project/v2` | V1 content plus exact-byte references to discovery, behavior and analysis profiles |
| `bo-behavior/v1` | Domains, variables, actions, initialization, interactions, independent properties, assumptions and refinement declarations |
| `bo-analysis-profile/v1` | Selected representation and optional finite-analysis bounds/budget |

The schemas live in `skills/vibelens/scripts/bo_observer/schemas/`. Unknown
versions/fields fail. The canonical state/activity and policy validators remain
authoritative. Definition errors carry a stable code and JSON pointer.

## Definition services

- `behavior.assess(contract, discovery)` validates typed references, unchanged
  values and action updates. Canonical transitions retain their original source,
  target, guard and effect definitions.
- Interactions distinguish shared reads, handoff, resources, joins and transactions.
  Revision reads must be declared; transaction completion identifies a commit;
  acknowledgement differs from return. Resources and joins reference existing
  activity definitions instead of redeclaring capacities or execution rules.
- Assumptions retain scope, source, status and invalidation basis. A coding-agent
  statement cannot become human confirmation. Progress properties require an
  explicit fairness choice and the applicable scheduling assumption.
- Recovery alternatives supply typed values for the whole selected state.
  Refinement tables reject duplicate concrete inputs. Partial mappings remain
  partial; claimed correspondence evidence is recorded as not yet checked.
- `analysis.capabilities.admit(...)` reports invalid, unresolved, unsupported or
  eligible. It checks referenced domains, callbacks, omitted transitions and
  boundaries. Analysis bounds modify a detached representation, never production
  capacity. Eligibility does not execute TLC or establish a passing property.

The initial export capability is a flat design model of Boolean/enum/bounded
integer/fixed identity values and supported pure expressions. Native callbacks,
hierarchical configurations, activity/resource/join export, richer domain export
and progress checking remain explicitly unsupported until the P6 adapter tests
them. The definition protocol can describe more than this export subset.

## Construction and review

A construction target records missing modeling work outside the executable
registry. It has a stable `target:` ID, kind, meaning, sources, scope and unresolved
items. A model/relation/state-owner obligation can reveal missing content even
when there are no authored questions.

Presentations preserve an exact semantic snapshot and partition its scope into
visible, explained and omitted references. A confirmation may cover only reviewed,
unchanged meaning. Historical presentations and confirmations remain immutable.
Migration preserves V2 confirmation records but does not grant new presentation
coverage. No targets/obligations means construction coverage remains unconfigured.

Use the existing concept command:

```text
python SKILL/scripts/bo_concepts.py present --root PROJECT --scope MODEL_ID --id P1 --sources SOURCE_ID --visible NODE_ID ...
python SKILL/scripts/bo_concepts.py confirm --root PROJECT --scope MODEL_ID --id C1 --sources ANSWER_SOURCE_ID --presentation P1
python SKILL/scripts/bo_concepts.py promote --root PROJECT --target target:MODEL --candidate candidate.json --concept MODEL_ID --expected-revision SHA256
```

The host records the actual shown message and answer sources. The command validates
recorded provenance; it cannot authenticate a quoted conversation. Promotion is one
validated replacement with a stale-write check. It creates no runtime events.

## Project readers and migration

V2 uses `contracts.discovery`, `contracts.behavior` and
`contracts.analysis_profiles`. A configured reference contains a project-relative
path, schema version and SHA-256 of exact file bytes. Unconfigured optional
definitions are null/empty rather than fabricated valid examples.

`project_artifacts.load_project(root, path)` validates one consistent artifact
set. The existing observer session and model loaders use it. The Node
`bo_readProject` adapter checks transport identity, paths, pinned bytes and versions.
Python owns full cross-model validation; native Node executors retain their own
strict supported-machine checks. Node transport parsing alone is not a definition
or binding acceptance result.

Use the existing upgrade command:

```text
python SKILL/scripts/bo_upgrade.py plan --artifacts --root PROJECT --plan-file review/migration.json
python SKILL/scripts/bo_upgrade.py apply --artifacts --root PROJECT --plan-file review/migration.json
python SKILL/scripts/bo_upgrade.py check --artifacts --root PROJECT
python SKILL/scripts/bo_upgrade.py recover --artifacts --root PROJECT
```

For intentional V2 definition edits, `plan --artifacts --refresh-contracts` stages
new reference hashes only after validating the new definition set. Apply rechecks
the exact inputs. It does not confirm changed intent or refresh runtime evidence.
P4 integrates this operation into the existing iteration workflow.

Migration snapshots exact before/after bytes in a project-local journal before
canonical writes. Readers reject a pending migration. Recovery rolls back an
interrupted write or completes a fully committed set; external edits cause a
conflict and are preserved. Old model IDs, confirmation history, views, annotations,
source and recordings are not regenerated by migration.

## Remaining phases

P2 builds the guided review/routing loop around these definitions. P3 supplies
native witnesses. P4 checks iteration closure and evidence validity. P5 presents
that evidence, P6 optionally executes formal analysis, and P7 runs fresh independent
conversations. None of those outcomes follows merely from valid JSON.
