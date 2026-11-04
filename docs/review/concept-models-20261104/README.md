# Concept model implementation and acceptance

Date: 2026-11-04. Branch: `feat/concept-model-contracts`.
Baseline: `3a43294d84d38bda4bcd7670a0b67e9985fa3ed5`.
Status: implemented and locally verified. Complete repository gate and clean staged Git export passed. This feature branch has not been merged or released as a new main tag.

Inputs: [layer assessment](../../assessment/2026-11-04-layers/README.md) and
[concept-first design](../../development/concept-model-first.md).

## Implemented boundaries

| Area | Responsibility | Independent verification |
| --- | --- | --- |
| Concept definitions | Source-free business, state and rule graphs; typed references and applicability | Schema, semantic legality, graph relations and scoped confirmation |
| Confirmation | Immutable semantic snapshot and original conversation evidence | Changed meaning, shared dependents and history checks |
| Implementation binding | Explicit state/rule/source/field/case anchors | Existing source inventory, native definitions, mapping and business assertions |
| Runtime context | Validated metadata pinned to a build and its recording | Byte freshness, actual events, invocation closure and independent native outcomes |
| Presentation | Business, state, rules, implementation and data concerns | Shared 2D/3D/Timeline vocabulary, saved-view migration and typed path witnesses |
| Source identity | One physical declaration with separate contextual/capture identities | Source/API/data regressions and identity checks |

The application retains its native execution authority in drive and observe modes.
The conceptual assembler does not execute an application, permission policy or
second Petri engine. Function intervals remain different from business state
residence. Static implementation links do not create runtime events.

## Scope and compatibility

- API entries, source hierarchy, functions/parameters and data operations are
  implementation facets. Their registrations, identities and evidence remain.
- Native reads, writes, transactions and transformations have distinct roles.
  Captured JSON fields remain available as explicit detail, with all-elements
  visibility checks.
- Hidden-layer connections are bounded typed paths in the current view. Explicitly
  excluded nodes cut paths. Original relation witnesses remain inspectable.
- Version 1 discovery retains its existing checks and reports legacy status.
  Version 2 adds confirmation and binding gates; downgrading an active version 2
  baseline fails inspection.
- One primary native state model is currently supported by the new binding
  contract. Multiple active state models report an unsupported binding; they are
  not silently folded into one machine. Existing engine capabilities remain
  authoritative for hierarchy and execution constraints.
- Independent assertions establish the exercised cases. Neither snapshots nor
  finite tests prove arbitrary natural-language understanding or all executions.

## Read the changes

[Source guide](../../source-guide.en.md) describes the module boundaries and call
paths. [Concept workflow](../../../skills/vibelens/references/concept-models.md)
contains the agent-facing commands. Detailed coding and viewer obligations moved
out of the main Skill into linked references; the original gates remain required.

Maintained sources are canonical under `skills/vibelens`; managed example copies
are refreshed with `tools/sync_runtime.py`. Historical acceptance evidence and
third-party libraries are outside cleanup scope.

## Verification

| Scope | Result | Evidence |
| --- | --- | --- |
| Concept definitions, scope, history and binding | 36 tests passed | `tests/test_concept_models.py` |
| Public discovery/preview/confirmation and iteration workflow | 21 tests passed | [Workflow output](root-evidence/concept-workflow.log) |
| Concept selection, exact native capture ownership and HTTP controls | 10 tests passed | `tests/test_concept_capture.py` |
| Source identity, API registrations and standalone native loading | 14 tests passed | `tests/test_layer_source_identity.py` |
| Python/JavaScript focused snapshot handling | 3 tests passed | `tests/test_snapshot_scope.py` |
| Source/API/data regression batch | 292 tests passed across the recorded suites | [Source report](source-verification.md) |
| Viewer and browser | Typed concern projection, exact lifecycles, filters, saved views, 2D/3D interaction and focused recording passed | [Viewer report](viewer-verification.md) |
| Four real databases | PostgreSQL, MongoDB, Redis and Neo4j passed catalog, Python runtime and native Node checks | [Live run](root-evidence/databases-live.log) |
| Independent Skill trial | Initial design, recipient iteration, maintenance and portable replay passed separate five-part gates | [Dialogue, project and receipts](trial/README.md) |
| Maintained-source quality | Ruff, ESLint, Black and Prettier passed | [Source checks](root-evidence/source-check.log) |
| Complete repository gate | Passed, exit 0, in the final serial run | [Full output](root-evidence/full-verification.log) |
| Clean staged Git export | Both shipped examples passed using frozen approvals | [Export receipt](root-evidence/clean-export.json) |

The source batch and focused rows overlap; they are not additive counts. The
browser performance fixture uses 20,000 synthetic events and reports its exact
measurement boundary. Live database evidence includes actual native effects;
fixture-only tests are identified separately.

The independent trial uses natural Chinese questions and simulated user answers,
with English authored code. It builds a local colleague file-sharing application
in observe mode, then changes grants from one recipient per file to independent
recipients. Revoking Bob's access preserves Carol's access. Actual HTTP responses,
SQLite rows, captured fields, state revisions and closed invocations are compared
with independent expectations. The retained dialogue identifies its synthetic
answers; it is not a human usability study.

## Repairs retained for review

[Failures and repairs](failures.md) records defects in preview export protection,
policy/source composition, scope handling, conceptual capture, standalone imports,
focused snapshots, initialization, name selection and recording-query source scans. It also distinguishes
outdated display fixtures and environment interruptions from product defects.
Original failed receipts remain alongside successful reruns. The final serial
repository run passed after correcting the overlapping acceptance jobs. Both
observer-free core exports execute without importing observer modules.

## Remaining boundaries

- The new semantic binding contract accepts one primary native state model.
  Multiple active models are explicitly rejected until their binding is supported.
- Static calls establish supported syntax, not arbitrary dynamic dispatch or
  complete data-flow proof. Unresolved targets remain visible as unresolved.
- All-elements 3D graphs can remain dense. Focused views are readable; this round
  does not claim that every expanded source graph is an effective overview.
- The trial uses local synthetic actors, not production authentication. It proves
  its exercised sharing rules and native effects, not every possible application.
- This branch changes the maintained Skill, shipped examples and layer description
  data. It does not publish a new Pages deployment or change the main release tag.

## Reproduce

Install the documented project and optional database/telemetry test dependencies,
then run from the repository root:

```text
python tools/check_source.py --format
python tools/verify.py --database
python tools/verify_databases.py --live --native
python tools/check_release_export.py --staged
```

The live database command needs the repository's database test containers.
Browser entry points and portable project replay commands are listed in the
viewer and trial reports. The clean export check restores frozen acceptance
records; it cannot generate a replacement approval to hide an export mismatch.
