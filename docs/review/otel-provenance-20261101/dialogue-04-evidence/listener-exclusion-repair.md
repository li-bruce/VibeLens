# Observer listener identity and native application 404s

## Retained finding

The parent supplied a live reproduction at
`SoftwareStatusObserverSkill/docs/review/otel-provenance-20261101/dialogue-04-exclusion-reproduction/result.json`.
Its exact bytes are retained at `pre-listener-repair/parent-reproduction.json`.
`listener-exclusion-before.json` independently repeats the defect on this project's
actual application listener: `/api/events` returns native 404 with no captured
request, while `/api/unknown-native-operation` returns 404 with two API events.
Supplied W3C request identities identify those native requests; they are not actors.

## Corrected boundary

`BOIntegration.attach_flask` now derives exclusions only from the actual Flask
static endpoint in `app.url_map`. For this application it is `/static/`. The observer
is a separate `HTTPServer` listener created by `BOIntegration.serve`, so the Flask
instrumentor has no observer routes to exclude. Public path names do not identify
a listener. Application requests to `/api/events`, `/api/view`, `/api/recordings`
and the other previously excluded names retain their native API error behavior
and receive upstream Flask request/response events.

No domain source, business UI, native state machine, policy, graph node identity
or saved personal configuration is changed. `listener-frozen-integrity.json`
compares the frozen inputs with the current graph and source bytes. The earlier
three accepted changes remain immutable under `.stategraph/`.

## Independent regression

`tests/listener_cases.py` uses the existing native Flask/WSGI response reader for
nine unknown paths, both GET and authenticated/CSRF-valid POST. Native HTTP 404,
`route_not_found` bodies, selected inputs, SDK trace/span identity and unchanged
storage are compared separately from the observer output. Protected mapping cases,
runtime probes and per-path whitebox assertions extend the existing gates without
removing earlier obligations.

The actual observer listener is exercised over HTTP for graph, view, export,
recordings and health. Its real event read is `/api/view.events`; GET `/api/events`
and GET `/api/bo/events` are native 404s on that listener. Those responses are kept
as observed, not renamed into successful endpoints. The read suite requires no new
producer events and no business storage changes. Static reads remain excluded.

A separate test application is configured with the former `/api/events` exclusion
using the real upstream SDK. It returns a real native 404 with no request events,
and the existing response comparison rejects it. The negative-control record is
`listener-exclusion-negative-control.json`; it is not accepted capture evidence.

## Verification status

`listener-exclusions-attempt-01` passed the complete scan, inspect, verify, accept
and check sequence. Mapping, state rules, business and project checks all passed.
The matrix contains 16 scenarios and 48 on/off/fault runs, with 122 independently
compared native HTTP responses. Thirteen project tests passed. Every normal run
reports zero probe/data errors and zero drops.

`listener-acceptance-summary.json` records the accepted build:
`17a3b812c21253fa465a9df5c2695bc81f0eb44703348e85a0f890b9b6ce7b2d`.
All 244 node IDs, the frozen domain/state/policy, 27 prior acceptance files and
138 copied canonical runtime files remain unchanged. All three personal configuration
file hashes matched at the acceptance checkpoint, before the parent UI exercise.

The joint service was restarted at application `http://127.0.0.1:50949` and graph
`http://127.0.0.1:50950/graph`. `listener-live-after.json` retains actual network
responses and raw API events for all nine application GET 404s: every request has
one real enter/return pair and matching framework status. Real observer reads and
application static reads add zero producer events, leave native storage unchanged,
and retain zero health errors. The running build and source binding match acceptance.

The parent conversation owns final real UI, recording, Timeline and 2D/3D inspection.
No browser tool is used in this continuation.

The parent has since started its independent `exercise_trial_ui.py` run. After
restart, `config/views/local.json` has a new UI save (revision 18); the interface
and design-focus files still match the frozen hashes. This correction issued no
preference write requests and did not restore over the new save. The observed
post-restart hashes and checkpoint distinction are retained in
`listener-post-restart-personal-state.json`.
