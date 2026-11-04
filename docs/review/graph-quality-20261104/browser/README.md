# Real browser acceptance

The current passing run is [`final-05-legacy-focus/results.json`](final-05-legacy-focus/results.json). It uses the canonical repository viewer assets in real headless Chrome with WebGL, a tilted perspective camera and native mouse/keyboard interactions. The fixture supplies a small nested sharing graph and project-local preferences; it does not represent recorded application execution.

| Check | Evidence |
| --- | --- |
| 2D regions fit current child bodies while distant hidden-owner coordinates remain saved. | [Planar view](final-05-legacy-focus/01-tight-planar.png) |
| 3D regions fit the same nested graph with real perspective and an orbit gesture. | [Tilted 3D view](final-05-legacy-focus/02-tight-tilted-3d.png) |
| Nested circle captions have distinct rectangles and mouse targets; dragging the database caption moves only its branch. | [Caption and group drag](final-05-legacy-focus/03-group-drag.png) |
| Dragging empty circle space moves only its complete branch; children retain relative offsets and pinned status. | [Group drag](final-05-legacy-focus/03-group-drag.png) |
| Hiding child layers displays the same parent ID as a glyph; restoring layers restores child positions exactly. | [Hidden-layer fallback](final-05-legacy-focus/04-hidden-children-fallback.png) |
| An individually hidden node is restored through its native filter action. | Assertions in `results.json` |
| A saved `projections: false` preference hides projected circles and routes an external edge to the visible same-ID fallback glyph. | [Hidden projections](final-05-legacy-focus/05-projections-hidden.png) |

Projection visibility is exercised through project preference persistence and page reload. The current page has no dedicated projection toggle button; this check does not claim such a button exists. Layer controls, exclusion/restore, orbit and circle dragging use the native controls.

The earlier tilted screenshots exposed overlapping nested-circle captions that could intercept a drag intended for a neighboring label. The final run covers the correction: a deterministic screen-space sweep keeps captions below their own circle rims, separates their rectangles and adds a short non-interactive leader when displaced. The test checks the actual `elementFromPoint` target and branch coordinates after a native caption drag. Circle planes, circle geometry, owner IDs and saved layout positions are unchanged by caption placement.

The first browser screenshots exposed an additional effect of stale owner positions: viewport fitting and layer planes still used invisible anchors even after circle fitting was corrected. Camera/plane bounds now use displayed glyph and circle extents. Projection guide lines also connect occupied circles rather than start at a hidden owner point.

## Preserved runs

- `attempt-01-fixture-setup`: the initial fixture omitted a required manifest field and used a network-idle wait incompatible with the live page's 400 ms polling. This is a test-fixture failure.
- `attempt-02-fixture-route-identity`: a draft assertion compared an original edge ID against its visible aggregate's ID. The final test follows the aggregate's original member IDs.
- `attempt-03-fixture-restore-locator`: native layer and branch interactions ran; restoration selected text from the row as if it were the button caption. The corrected test selects the row and its `Show again` button separately. Its screenshots also retain the stale-anchor viewport issue found during inspection.
- `final`: the first fully passing browser run, before removing hidden-anchor projection-guide origins.
- `final-02`: passing rerun including corrected visible projection-guide origins; its screenshots preserve the caption overlap discovered during visual inspection.
- `final-03-captions`: final passing rerun with separate nested-caption targets, correct exact-caption dragging and all earlier browser checks.
- `final-04-api-integration`: passing geometry rerun after the exact API observation integration.
- `final-05-legacy-focus`: latest passing rerun after preserving legacy capture-owner selection without inferred API activation.

Exact API recording replay has its own [latest Chrome result](api-observation-05-legacy-focus/results.json) and [review](../api-observation-review.md). It covers qualified GET/POST lifecycle bars, captured response values and cross-layer causal links. Its serialized request facts are a deterministic fixture, distinct from real application HTTP execution.

The reusable test is [`tools/test_graph_quality_browser.py`](../../../../tools/test_graph_quality_browser.py). Run it with Python Playwright installed and a fresh output directory:

```text
BO_GRAPH_QUALITY_EVIDENCE=.validation/graph-quality-browser
python tools/test_graph_quality_browser.py
```

`BO_BROWSER_EXECUTABLE` optionally selects an installed Chromium/Chrome executable. Otherwise the test uses the standard Windows Chrome location when available, then Playwright's installed Chromium. It refuses to overwrite an existing `results.json`. The GitHub browser job installs the pinned Playwright version and uploads this evidence separately from the normal source verification gate.
