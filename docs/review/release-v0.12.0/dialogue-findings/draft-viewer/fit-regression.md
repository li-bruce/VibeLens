# Fit after arranging a filtered view

The trial screenshot in `.validation/draft-viewer-complete/business.png` showed
the business circle below the visible canvas after Expand → Arrange → Fit.

## Reproduction

`tools/test_containment_bounds.mjs` now reproduces the underlying geometry without
a browser: create a cached business-layer projection, move the shared node boxes,
refresh the full graph, then fit the cached projection. Before the fix this failed
with `AssertionError: Fit includes the arranged glyph's top edge`.

The layer projection deliberately reuses topology and node boxes. Its copied
`minX`, `minY`, `width`, and `height` values remained from before the move. The
existing containment pass rebuilt circles but carried those stale extents into
the camera calculation. This was a viewer defect, not a missing trial graph or
a fabricated business state.

## Change and regression checks

`containment-view.js` now derives fit bounds from the current visible glyphs and
containment circles. It leaves complete-graph data, cached topology, expansion
choices, and saved coordinates untouched. Hidden owner anchors and filtered nodes
do not reserve camera space; an empty view has finite bounds.

Passed focused checks:

- `node tools/test_containment_bounds.mjs`: cached projection movement, region
  coverage, hidden-anchor exclusion, empty view, and existing circle regressions.
- `node tools/test_concept_view.mjs`: concept projection, typed containment,
  guard polarity, and function-relation regressions.
- `node tools/test_viewer_semantics.mjs`: viewer semantic regressions.
- ESLint for `containment-view.js`; Prettier for the changed JavaScript files.

The failed pre-fix assertion above is retained as failure evidence. Real browser
screenshots and screen-coordinate bounds are recorded separately by the design
viewer runner; these focused checks alone do not claim browser acceptance.
