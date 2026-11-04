# Repeated transition effects in the design graph

The fresh v0.12.0 conversation produced a valid `file_review` draft in round 03,
revision 02. Its state preview drew the approve-to-review-record and
reject-to-review-record associations twice each. The duplicated lines existed in
the canonical graph, not only in Mermaid rendering.

## Cause

Each transition declared `retain_review_record` in its `effects` list. That
generated a `has_effect` relation. An explicit `transition_has_effect` crosslink
asserted the same association. The crosslink validator already required the
effect to belong to that transition, but the projector emitted both edges.

The [preserved input](before-discovery.presented.json), [original preview](before-state-preview.md)
and [before result](before.json) retain the source files and SHA-256 hashes.
The trial itself was not edited by this reproduction.

## Correction

Only this declared relation pair is consolidated, when its exact transition and
effect identities match and neither association carries additional semantics.
The generated edge keeps its original ID. Its `equivalent_relations` contains
the full explicit assertions, including IDs, types, captions and source references.

Semantic records, confirmation revisions, dependency entries and native binding
obligations remain separate. Original edge IDs still select the same relation in
design focus and previews. Both original types work in focus filters. The bound
projection and control inventory retain the original assertions; ambiguous IDs
are rejected. Observation events and their IDs are unchanged.

A crosslink with `argument` stays separate. Unknown semantic fields fail the
existing strict schema. Different transitions sharing the same effect retain
separate associations. Ordinary parallel relations, conditions, polarity and
timing are not inferred equivalent.

## Verification

[Reproduction script](reproduce.py) checks the preserved input and regenerates
the preview with the same focus selection. [After result](after.json) records:

- Four displayed effect edges become two associations, with all four original IDs retained.
- The semantic revision and source file hashes remain unchanged.
- Both original relations retain their semantic records and dependencies.

[The corrected preview](after-state-preview.md) is a source-free design result;
it does not claim that the application ran.

Python regressions cover original-ID focus, type filters, boundary provenance,
multiple assertions, separate transitions, arguments, malformed aliases, control
inventory drift, binding omissions and missing completion obligations. Runtime
checks use the existing effect observation fixture and assert that neither the
model nor recorded events are rewritten.

| Check | Result | Evidence |
|---|---:|---|
| New projection regressions | 11 passed | [Log](regression.log) |
| Existing concept/model/capture/workflow regressions | 84 passed | [Log](concept-regression.log) |
| Design preview regressions | 4 passed | [Log](design-regression.log) |
| Conversation control regressions | 22 passed | [Log](control-regression.log) |

The Windows junction regression required execution outside the filesystem
sandbox; its final run passed. Frontend original-ID preferences and browser
acceptance are recorded separately in the v0.12.1 release review.
