# Exact API observation follow-up

The release review found a runtime gap after separating concrete API endpoints from technical HTTP capture anchors: the endpoints could remain static while their capture anchors had real events. Generic handler/source mappings could also attribute an observation to another route using the same handler.

## Corrected behavior

`api-observation.js` consumes only backend-qualified `observation_projection` and `observation_sources`. Each source records its native observation node, HTTP method, registered route and exact handler source. Display labels and arbitrary source-map paths are excluded from matching.

The shared mapping now supports:

- Graph activation, current inputs/outputs and native lifecycle state.
- Separate native GET and POST intervals on one combined endpoint, including concurrent intervals.
- Recorded snapshots containing `api_structure`, available independently of the optional full code view.
- Replay step ownership and explicit HTTP observation mapping animation.
- Timeline API bars and original causal call/return links. A qualified API representation takes the visible HTTP scope; native collector intervals remain available.
- API revision changes invalidating display indexes and graph-bound recordings. Legacy graph-version strings are retained when no API snapshot exists; unrelated preferences do not change graph identity.

Native event IDs, call IDs, observed times, entry/exit ordinals and parent references remain unchanged. A projected bar carries its native source and `http-registration` evidence. Displayed flow endpoint IDs are accompanied by their original observed subjects, so concurrent API subtracks use the correct representation without rewriting causal facts.

A source handler and another route sharing it receive no inferred duration. HTTP 403 is displayed as the captured response value; it is not converted to a failed business outcome. Raw capture IDs reused across different endpoints are rejected by the backend qualification step because the recorded node identity alone cannot distinguish those requests.

## Verification

`node tools/test_api_observation.mjs` passes these independent behavior checks:

1. `/files` accepts exact GET/POST observation IDs while `/archive`, despite sharing its source handler, stays static.
2. Native request intervals remain separate: GET 60 ms, POST 30 ms; active counts retain concurrent requests.
3. Values from GET and POST cannot merge through a reused call ID.
4. Graph state, inline captured values, Timeline bars and replay steps use the same qualification.
5. Business → API → function and return paths remain visible when collector rows are hidden or shown. Concurrent calls connect to their own API subtracks.
6. API snapshots merge by existing IDs, source-only nodes stay static and serialized recording bytes remain unchanged.
7. API revisions refresh the view while preference changes do not invalidate the graph.

Actual Chrome replay passed against the final frontend at [`browser/api-observation-05-legacy-focus/results.json`](browser/api-observation-05-legacy-focus/results.json):

- [GET active in the recorded API view](browser/api-observation-05-legacy-focus/01-get-active-api-view.png).
- [POST return with the original HTTP response](browser/api-observation-05-legacy-focus/02-post-return-values.png).
- [Cross-layer causal Timeline](browser/api-observation-05-legacy-focus/03-cross-layer-causality.png).

These browser fixtures contain deterministic serialized observation facts. They verify rendering, seeking, ownership and representation behavior; they do not claim that an independent business application generated those facts. Backend selector/source qualification and the requested new-chat application trial have their own evidence.

The root's full verification caught a legacy focus-selection regression in unchanged `tools/test_layered_view.mjs`: older endpoints with no qualification metadata previously located their source observation owners through handler mappings. That source-based focus/capture selection has been preserved. It cannot activate the endpoint or create an HTTP duration. New endpoint inventories with an explicit `observation_sources` array, including an empty array, continue to require exact qualified IDs. The new regression checks all three outcomes, and the old layered test passes unchanged.

The existing layered/code/engineering views, semantic focus, lifecycle, viewer-semantic, graph-name and recording-Timeline checks passed unchanged. The 20,000-event Timeline fixture indexed in approximately 287 ms in the last focused run. The complete geometry/caption browser suite was rerun after the legacy focus correction and passed at [`browser/final-05-legacy-focus/results.json`](browser/final-05-legacy-focus/results.json). Earlier passing browser runs and the root's failed full-verification run remain retained.

Both browser regressions are wired into the dedicated GitHub browser job. No state-machine execution engine, authorization decision, raw event identity or application command is modified by this display projection.
