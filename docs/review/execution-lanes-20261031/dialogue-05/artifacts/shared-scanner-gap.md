# Shared Source Scanner Gap

## Reproduction retained without a workaround

1. Current `app/web.py` lines 123-130 registers eight literal routes with `app.add_url_rule`, binding `routes.index`, `login`, `logout`, `upload`, `review`, `share`, `file_info`, and `download`.
2. The fresh server returned HTTP 200 for `/api/code/graph?projection=all&limit=1500&depth=2`. Exact response: `final-code-graph.json`.
3. All 733 returned code nodes have kind function or data. There are no endpoint nodes. API direct observations/declared nodes were also zero in the configured verification layer report. An outer `http_request` event does not supply the missing endpoint/handler mappings.
4. Installed canonical `observer_runtime/bo_observer/code_graph/endpoints.py` reads `symbol.entrypoints` and recognizes decorator-style get/post/route/etc calls. It does not process imperative `add_url_rule` registrations. The exact installed source is retained in `source-runtime-snapshot.zip`.
5. The same graph's `project.entries` includes 154 `.tmp` entries, including pip metadata, build trackers and wheel caches. These installation artifacts are not application source. Exact paths are retained in `freeze-verification.json` and the unmodified graph response.

The coordinating conversation independently reported the same issues and explicitly froze this trial. Its earlier 108-event snapshot and 14 data-parent links are a different snapshot from this round's final 490 events and 136 data-parent links. Do not conflate their counts.

No route was converted to a decorator. No installed scanner, validator, source index, graph response or historical event was hand-patched. Shared repair and regression testing belong to the maintained repository, which remains read-only here. A new conversation must upgrade normally and verify actual endpoint/handler ownership and a clean engineering projection.

## Existing parent-context repair

The final live snapshot has 136 database events and every one has a parent ID. `freeze-verification.json` preserves exact call IDs and resolved enclosing nodes from the raw stream. This is sampled runtime evidence; it is not a completed independent concurrent isolation test. No parent IDs were inferred from timestamps or added to events.
