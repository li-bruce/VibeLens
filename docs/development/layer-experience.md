# Layer experience and end-to-end acceptance

## Work order

1. Reproduce the published demo layout and identify which solver it uses.
2. Exercise one runnable project, compare each of the nine graph layers with
   independent source/runtime expectations, then repeat after a real feature edit.
3. Improve semantic clustering and share the planar starting coordinates with
   the spatial viewer while retaining saved layouts and manual pins.
4. After functional acceptance, replace the introduction's depth section with
   an interactive layer explorer. Explain each layer with one concrete question.
5. Run regressions, browser interaction checks and scale checks. Preserve failures,
   repairs, retests and screenshots in `docs/review/layer-experience/`.

## Acceptance boundaries

- Static structure, declared behavior and runtime evidence are checked separately.
- An unchanged layer after an unrelated edit is expected, not a missing update.
- Observer requests, source navigation and layout actions create no business events.
- Business meaning still comes from the confirmed conversation; source scans do
  not invent business semantics or observed execution.
- Existing user layouts remain intact. New demonstration defaults may be reseeded
  in the demonstration's own preference namespace.

## Status

Completed locally. The demo now uses the semantic cluster solver, sparse and
dense bridges retain distinct placement, and initial spatial coordinates reuse
planar centers. The full verification suite, nine-layer application iteration,
bilingual browser checks and clean staged export passed. One Windows filesystem
symlink case was skipped because the host lacks the required privilege.

See [the review materials](../review/layer-experience/README.md) for source,
recordings, screenshots, failures and retests. The branch has not been published.
