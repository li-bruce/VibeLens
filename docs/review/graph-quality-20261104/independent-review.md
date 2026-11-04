# Independent implementation review

Date: 2026-11-04 (Asia/Shanghai)

Scope: the working graph-quality changes, reviewed independently from the implementation agents' conclusions. Source review covered 2D/3D containment, routed endpoints, API discovery and grouping, source explanations, strict documentation reporting, source-proximity layout and its package integration. The reviewer initially had read-only ownership; the root subsequently assigned the narrow spatial-renderer fixes described below.

## Findings and resolution

| Priority | Finding | Reproducer and consequence | Resolution |
| --- | --- | --- | --- |
| P1 | Imported API handlers escaped the strict source-documentation check. | `api.py` imports `read_file` from `handlers.py`, then calls Flask `app.add_url_rule('/files', view_func=read_file, methods=['GET'])`. The code graph resolves the actual handler, but the initial report constructed `api.py::handlers.read_file`; an undocumented handler produced `valid: true`, `checked_symbols: []`. | API implementation now shares `handler_key` resolution between graph construction and documentation checking. Independent rerun passed the Python and JavaScript imported-handler regressions. |
| P2 | Python decorator method sorting changed existing endpoint identity. | Legacy `@app.route('/files', methods=['POST', 'GET'])` produced a different endpoint hash when the new extractor sorted it to `['GET', 'POST']`. | Existing decorator method order is preserved. The explicit stable-identity regression passed independently. |
| P2 | One JavaScript middleware registration produced repeated endpoint nodes. | `app.get('/files', authenticate, download)` was represented as one endpoint per handler. | Exact registrations now group to one retained primary endpoint, with all handler mappings, old registration IDs/bindings and endpoint aliases. Distinct declarations remain distinct. Independent middleware and registration regressions passed. |
| P2 | Hidden projection rings still influenced edge routing. | A region-only owner has children on another plane. Turning projections off hid its shell, while routing could still terminate on the invisible projected ring. | `visibleSpatialBodies` supplies one displayed-volume inventory to meshes, labels, picking and routing. A projection-only owner retains a selectable glyph with its original ID and saved coordinates when its rings are hidden. |
| P2 | Tight circles exposed stale-owner depth in perspective dragging. | A fitted/projected circle is far from the hidden owner's saved position. `startDrag` constructed its camera-facing plane through that stale position, so pointer movement used the wrong perspective depth. | Canvas ring picking and ring labels carry the actual visible circle center into the drag-plane calculation. Real glyphs continue to use their physical centers; whole-branch IDs and saved-coordinate snapshots remain unchanged. |
| P2 | Camera fitting, layer-plane extents and projection guides still used invisible owner points. | Real Chrome screenshots showed correctly fitted circles in a tiny corner of oversized planes, with long guide lines leaving the visible graph. | Camera/plane bounds now follow displayed glyph and ring extents. Projection guides connect visible glyphs or occupied owner regions. Focused regressions and the final real browser rerun pass. |
| P2 | Nested circle captions overlapped and intercepted neighboring caption drags. | Actual tilted-view screenshots put the database and enclosing business captions over one another. The wrong enclosing owner could receive the drag. | A bounded screen-space sweep separates caption rectangles below their circle rims, using cached dimensions and non-interactive leaders. The final browser run asserts actual rectangle separation, `elementFromPoint` ownership and correct branch-only movement when the exact database caption is dragged. |

The reported database fixture now fits a radius of approximately 747.11 instead of 2882.18. The test uses the actual six saved table coordinates and deliberately keeps the distant hidden owner unchanged. Browser interaction acceptance was subsequently executed as a separate gate: see [browser evidence](browser/README.md).

## Independent checks executed

All of the following passed in the working tree:

- `python -B -X utf8 -m unittest discover -s tests -p test_code_graph.py -v`: 31 existing code-graph regressions.
- `python -B -X utf8 -m unittest discover -s tests -p test_source_documentation.py -v`: 17 source-documentation/API regressions after the reviewed fixes, including inventory-declared parameter descriptions.
- `node tools/test_containment_bounds.mjs`: reported-fixture geometry, nested disks, exclusion behavior, same-ID empty-owner fallback, routing and 10,000-disk containment.
- `node tools/test_spatial_interaction_bounds.mjs`: projection visibility, visible fallback glyphs, correct routed endpoints, real self glyphs, perspective drag anchors, displayed-body camera bounds/guide endpoints and unchanged IDs/coordinates.
- `node tools/test_proximity_layout.mjs`: deterministic source-neighborhood hints, graph immutability, pinned positions, identical planar/spatial coordinates and bounded 1,000/4,000/10,000-node preparation. The independent sample showed approximately 28.77% lower mean same-file distance than the unhinted fixture.
- `node tools/test_source_documentation.mjs`: source-backed names, source mode, capture-role placement and no source-documentation inheritance onto captured fields.
- `node tools/test_graph_names.mjs`, `tools/test_layered_view.mjs`, `tools/test_spatial_workspace.mjs`, `tools/test_spatial_planes.mjs`, `tools/test_shared_layout.mjs`.
- `python -B -X utf8 tools/test_graph_quality_browser.py`: real Chrome/WebGL execution passed, including later reruns after exact API integration and legacy focus compatibility; the final evidence is `browser/final-05-legacy-focus`. Tilt/orbit, non-overlapping nested captions, exact caption dragging, empty-circle branch dragging, unchanged unrelated branches, pins, layer hide/restore, explicit exclusions/restoration and saved projection visibility/routing all passed without page/console errors. The portable browser check is wired into the GitHub browser job.

An attempted unittest discovery of `test_multilanguage.py` found zero tests: that module supplies fixtures rather than a unittest test case. It is not counted as an executed passing suite.

## Remaining review boundaries

- The route extractor proves supported literal framework receiver registrations. Chained Express `app.route('/files').get(handler)`, project-owned router factories/objects, Fastify plugin receiver parameters, computed mounts and dynamic prefixes require additional resolution or an explicit project binding. Their absence must not be described as complete framework route discovery.
- Grouped middleware documentation now retains the endpoint's exact method/path and exposes individual handler summaries. The first middleware's comment is not used as the endpoint caption; this behavior is covered by the middleware regression.
- Source documentation is an extraction/completeness check. It does not prove the prose accurately describes every possible behavior. Independent business, source-mapping and runtime gates remain required.
- The focused and browser tests do not replace the root's complete verification or requested new-chat project trial. Source navigation, business/runtime correctness and iteration refresh are separate from this geometric fixture. The page has no dedicated projection toggle button; its saved preference was tested through persistence/reload rather than claiming a native toggle exists.

No business/state execution core, relation facts, source IDs or telemetry outcome semantics were intentionally changed by the reviewer's renderer patch. Projection glyph fallback is display-only. No commit or push was performed by the reviewer.

The root's subsequent release review identified a concrete API runtime projection gap. Its exact-ownership fix, source/runtime boundary, concurrent-call tests and final actual browser evidence are recorded in [the API observation follow-up](api-observation-review.md). The existing geometry/caption browser checks were rerun after that integration and passed.
