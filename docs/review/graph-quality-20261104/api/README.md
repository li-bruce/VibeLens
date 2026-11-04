# API identity and source explanations

The existing file-sharing trial has four literal HTTP registrations and five
OpenTelemetry capture anchors. `api_get` and `api_post` select different methods
of the same catch-all route. They are useful capture addresses, but they are not
two additional endpoints. The old API view mixed those observation addresses
with static route registrations.

`trial-analysis.json` records the original source hash, physical endpoints,
capture registrations and missing source comments. `inspect_trial.py` reproduces
this inspection with `persist=False`; it does not edit application source or
write a new accepted baseline. The inspected `app/web.py` hash was unchanged.

## Changes

- Verified capture bindings carry `api_role: capture` and their exact telemetry
  selector. They appear in Functions and values. Literal endpoint declarations
  carry `api_role: endpoint` and remain in API. Runtime event IDs are unchanged.
- Different methods, paths and independent registrations remain separate. One
  Express registration with several middleware handlers has one endpoint and
  several `handles` edges. Its primary existing ID is retained; retired duplicate
  IDs and bindings are exported in `registration_ids`, `registration_bindings`
  and `endpoint_aliases`. Personal positions, exclusions and annotations are not
  reassigned: entries on retired IDs remain dormant for review.
- Python route decorators now use the same receiver proof as programmatic route
  registration. JavaScript tracks known Express, Fastify and Koa router factories
  and lexical shadowing. An arbitrary `cache.get('/key', callback)` is no longer
  presented as an HTTP endpoint. The original source calls remain indexed.
- Python docstrings and JavaScript/TypeScript JSDoc are extracted as source facts.
  React and Vue use their existing language adapters. Source path, symbol, comment
  range and file hash accompany explanations. Node captions use one short source
  sentence; complete comments remain metadata. IDs and source names are stable.
- Verified manifest bindings supply declaration coordinates to authored nodes as
  well as optional code nodes. Exact parameter declarations receive their own
  documented descriptions. Captured event fields remain capture fields.
- A grouped route retains its HTTP name and shows handler comments separately;
  an authentication middleware comment cannot name the entire endpoint.

## Source-documentation check

```text
python skills/vibelens/scripts/bo_code.py docs --root PROJECT --strict
python skills/vibelens/scripts/bo_code.py docs --root PROJECT --all --strict
```

The default scope checks mapped source declarations, independently discovered
API handlers, `represents` parameters and `implementation.features[].parameters`.
The optional `--all` includes every scanned declaration and parameter. Without
`--strict`, missing comments are reported for adoption review; parser failures
still fail. `--out PROJECT_RELATIVE_JSON` saves the structured report. Existing
mapping, runtime, policy and business checks retain their original requirements.

The check reads fresh source facts. It reports missing comments, removed physical
parameters and stale bindings rather than accepting old descriptions from nodes.
An existing project can therefore contain valid runtime capture and missing source
documentation at the same time. The trial inspection records this distinction.

## Failure, repair and retest

1. Reproduced meaningless GET/POST capture captions and the four-route/five-anchor
   mismatch from the original trial declarations. Reclassified by registered
   provenance, keeping all capture IDs and selectors.
2. Added absent-comment and false-route fixtures. The scanner now rejects the
   invented endpoint interpretation while preserving the original source calls.
3. Independent review found imported Python handlers escaped the first docs check.
   The checker now shares the graph's handler resolver, including imported Node
   handlers. Both languages have regressions.
4. Independent review caught decorator-method sorting changing old endpoint IDs.
   Existing decorator order is preserved; a regression asserts the previous ID.
5. The first JavaScript test fixture omitted the required machine transition array.
   Corrected the fixture, retained production validation and reran the test.
6. Review added inventory-only parameter obligations and grouped-route naming
   checks. Both now have failing-condition and repaired-source regressions.

Final focused results are in `focused-tests.json`: 17 new Python tests, 31 existing
code-graph tests and the JavaScript source/role regression passed. Earlier focused
checks also passed 30 telemetry tests, three source-inventory tests and the graph
naming, layered-view and viewer-semantic JavaScript regressions. Root acceptance
records the subsequent integrated formatting, runtime and browser checks.

The second full verification found a compatibility regression: an externally
supplied JavaScript `app.post('/create', create)` lost its original callback
`entrypoints` evidence when receiver proof was required. Those two facts are now
separate. The original syntactic callback entrypoint is retained, while only
`http_endpoints` with proven framework receivers create API nodes. The original
multilanguage test is unchanged. `callback-compatibility-tests.json` records all
28 multilanguage tests, 18 source-documentation tests, 31 code-graph tests and
the JavaScript documentation/role regression passing after this correction.

## Exact HTTP runtime projection

The integrated review found a further defect: classifying native GET/POST capture
addresses as execution nodes removed their durations from the physical API view.
The correction is an exact observation projection, independent of the optional
full code index. It keeps the original producer events, invocation identities,
trace/parent identities and endpoint identities.

Each endpoint receives `observation_sources` only when an actual telemetry
registration matches its resolved source handler, literal HTTP method and literal
route. GET and POST captures can therefore observe one combined registration.
Two routes sharing a handler remain distinct. Ambiguous registrations, conflicting
selectors and a capture address reused across different endpoints are reported
and receive no inferred API lifecycle. Snapshot mapping edges have
`mapping_role: http-observation`; they represent the same observed event rather
than an extra function call.

```text
python skills/vibelens/scripts/bo_code.py api-check --root PROJECT --strict
```

`api_observation_check()` reports mapping validity separately from coverage.
Configured selector mismatches fail even when full code visualization is disabled.
Strict mode also fails unobserved routes, missing methods of a combined route and
projects with physical endpoints but no HTTP registrations. Projects without HTTP
endpoints report `not_applicable`. Nonstrict adoption reports incomplete coverage
explicitly. Both modes scan current source; neither writes the optional code cache.
`errors` contains every failing cause, and `CodeGraph.check()` returns the report
under `api_observation` for the managed verification gate.

`exact-http-projection-tests.json` records 15 exact-projection regressions,
31 existing code-graph tests, 18 source-documentation tests and 28 multilanguage
tests passing. The tests cover selector mismatch, imported middleware handlers,
ambiguous receivers, shared handlers, reused capture IDs, missing registrations,
missing methods, fresh configuration changes and CLI exit status/cache isolation.
The first new fixture failed native validation because its business summary was
absent; the fixture was corrected without changing the validator.

`old-trial-http-coverage.json` records a read-only strict check of the unchanged
file-sharing trial: all four literal endpoints are covered, with no mapping issues
or missing methods. This check uses the canonical backend against actual project
source; the live process requires the separately recorded managed runtime upgrade
and restart before serving these new snapshots.

## Scope

Static route facts describe literal registrations. They do not expand dynamic
dispatch branches into guessed APIs or manufacture fully mounted paths for
unknown router prefixes. Chained Express registrations, dynamically imported
router objects and generated framework routes still need adapter support or
explicit source bindings. Runtime HTTP capture keeps reporting actual paths and
framework responses independently of those static limitations.
