# Source proximity inside type clusters

The shared layout now uses a small source-locality hint inside an existing node-type cluster. Nearby functions, parameters and API handlers are easier to inspect together. Existing graph relations, containment ownership and cross-cluster bridge placement remain the layout's structural constraints.

## Implemented behavior

- Prefer an existing graph neighbor when choosing the next local item.
- Otherwise prefer the same source file and a nearby source line.
- For items without source locations, use tokens from the source identifier or signature. AI explanations, translated labels and annotations do not affect the hint.
- Apply the same compact local seeds to the planar cluster solver and the standalone spatial solver. The normal 3D view preserves the exact shared 2D coordinates.
- Use proximity ordering when packing newly visible sibling circles, while larger footprint bands retain packing priority.
- Preserve saved positions during normal refresh and all explicit pins during automatic arrangement.

No source relationship is inferred from spelling. The hint creates no graph nodes, edges, or changed IDs.

## Cost bounds

Source metadata is cached by immutable node object. Each layout request builds one reusable adjacency index; each item considers at most 32 candidates, and identifier token lists contain at most 12 entries. Source-file candidates come from a local line-sorted window. The rendering loop does not tokenize labels or recompute this ranking.

## Verification

`tools/test_proximity_layout.mjs` checks source locality, real-link precedence, lexical fallback, alias invariance, deterministic input ordering, hub limits, source-object immutability, pinned positions and shared planar/spatial coordinates. A 96-function fixture compares source-aware placement with the same solver receiving no source locations. Mean within-file distance improves by 28.77% (457.71 to 326.05); this measures that fixture, rather than a universal readability guarantee.

Hint preparation for 1,000, 4,000 and 10,000 nodes is recorded in [proximity-results.json](proximity-results.json). These timings cover the bounded hint preparation, not the full force simulation or browser rendering.

Additional passing regressions:

- `node tools/test_shared_layout.mjs`
- `node tools/test_spatial_workspace.mjs`
- `node examples/delivery/tests/test_graph_layout.mjs`
- Targeted ESLint and Prettier checks for the new helper and modified solvers.
- `node tools/test_cluster_browser.mjs`: actual 2D type neighborhoods, bridge-node layout, pin preservation after arrangement, identical 2D/3D seeds, mouse orbit, and a responsive 4,000-node cluster worker. [Browser result](browser/results.json) and screenshots preserve the interaction evidence.

The first browser attempt stopped before launch because plain Node could not resolve Playwright. Reusing the already installed Codex Node dependency directory and Chrome resolved the environment issue; no package or product source change was required.

Reproduce the dedicated evidence:

```powershell
$env:BO_LAYOUT_EVIDENCE = 'docs/review/graph-quality-20261104/layout'
node tools/test_proximity_layout.mjs
```
