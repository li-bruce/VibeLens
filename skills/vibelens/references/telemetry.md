# Standard tracing, existing state network

OpenTelemetry is an optional native tracing backend. Business/state declarations,
drive/observe selection, native execution and the independent Python observer keep
their existing roles. Use it for new supported projects; retain the native backend
where dependencies or deployment requirements prevent adoption.

## Integration contract

Keep wiring in an isolated `bo_` observation module. Install
`requirements-telemetry.txt` in the Python application environment, or use the
application's compatible OTel provider. Do not replace a global provider.

```python
from opentelemetry.sdk.trace import TracerProvider
from bo_observer.adapters.python.bo_otel import BOOpenTelemetry

bo_provider = TracerProvider()
bo_tracing = bo_probe.bo_bind_tracing(
    BOOpenTelemetry(bo_provider.get_tracer("vibelens"))
)
```

Native BOProbe spans, selected values, state snapshots and database adapters keep
their existing interfaces. Their events now carry SDK-created `trace` metadata.
The live graph receives entry/change/end immediately through its original bounded
transport; optional standard exporters receive finished spans. VibeLens JSON is
not OTLP. Use upstream OTLP exporters/Collector for external trace pipelines.
Automatic technical spans provide start/end boundaries and registered attributes.
Changes to business values during a long-running operation still use the existing
selected point/state probes; the SDK does not observe arbitrary variable assignments.

Physical exceptions carry `exception: {"type": "ValueError"}` independently of
optional business output fields. Native span catches and actual upstream SDK
exception events supply this class; messages and stacks are not copied by
VibeLens. SDK ERROR status alone does not manufacture an exception or business
failure. The exception is visible in event details and Timeline hover, excluded
from unselected context headers, and can be compared through a protected
`context_fields` path such as `["exception", "type"]`. Keep the original native
exception behavior and HTTP response unchanged.

Native escaping exceptions annotate SDK `error.type` and the technical span
status; this does not set a business state. Existing upstream exception span
events are read for compatibility with the pinned instrumentation. Current OTel
conventions prefer exception logs. This trace adapter does not ingest arbitrary
log-only exception sources; keep selected native exception probes or explicitly
add a tested log adapter before claiming that source is observed. VibeLens does
not emit new deprecated exception span events or claim to implement all OTel signals.

Node uses `bo_otel.mjs` with `@opentelemetry/api`, `@opentelemetry/core` and an
application-owned tracer. The tested lock uses API 1.9 and consolidated
`@opentelemetry/sdk-trace` 2.12 on Node >=20.6. Configure the SDK's task context
manager (for example `AsyncLocalStorageContextManager`) once in the application
bootstrap, reusing existing setup. `bo_probe.bo_bind_tracing(new
BOOpenTelemetry(bo_tracer))` replaces the probe's custom task-context backend.
React/Vue use the same native event protocol; tracing async browser work requires
an appropriate upstream browser context manager and is a separate runtime check.

## Automatic technical instrumentation

Use upstream library instrumentation where it supports the chosen framework.
Register only selected spans against existing source-bound API, function or data
nodes in `bo_stategraph/telemetry.json`:

```json
{
  "protocol": "bo-telemetry/v1",
  "backend": "opentelemetry",
  "registrations": [{
    "node": "api:list_files",
    "source": {"path": "server.py", "symbol": "list_files"},
    "match": {"name": "GET /files"},
    "capture": {"out": {"status": "http.response.status_code"}}
  }]
}
```

Add this JSON file to `model.source_files` so registration changes invalidate the
running build; iteration snapshots also track it automatically. Fields must exist
in that node's capture declaration. Register `BOOpenTelemetryProcessor` on the
same provider after binding the probe; Node supplies it in the provider's
`spanProcessors` configuration. Selectors must be available at span start. A
framework that supplies route names only at the end needs a native entry hook or
a stable initial selector, verified against that framework's actual behavior.
Do not claim zero-code capture merely because a registration exists.

The processor excludes observer activity and VibeLens-created spans, avoiding
duplicate capture. It does not map generic HTTP activity to business nodes.
For example, **Share file** is business; its HTTP route is API; its permission
predicate, write operation and implementation function retain their own nodes
and explicit mappings. Automatic spans supplement selected business anchors.

## Async and object references

Use SDK task context within a process. A causal child may continue after its
parent ends; give the child its own observed invocation. For HTTP, extract/inject
W3C headers through the SDK. Headers establish tracing context, not an actor.

For an application-owned queue, `bo_tracing.inject()` returns standard headers
plus a bounded VibeLens identity envelope. A worker uses
`with bo_tracing.receive(carrier, trusted=True): ...`; use `link=True` for a
distinct job trace related to its trigger. Node's equivalent is
`bo_tracing.receive(carrier, callback, {trusted: true, link: true})`.
`trusted` refers to the application's internal envelope, never to user privilege.
Do not accept this envelope from a browser as business identity. Set the actor
from native authenticated application state; it is not propagated as authority.
Invalid runtime carriers increment capture errors and let native work continue
with a fresh context; `strict=True` (Node `strict: true`) is available for protocol
tests. Business exceptions are propagated unchanged. Several queue messages can
use `bo_tracing.linked(carriers)` (Node adds a callback) to start a fan-in trace;
set its business instance and object roles explicitly rather than merging senders.

A valid application-owned carrier from an earlier build is a version boundary,
not permission to reuse old graph ownership. The receiver keeps its W3C cause as
an independent Span Link with `source_build_id`, drops old graph call/entity/
workflow references, and requires the worker's current native facts. Its health
reports `external_build_contexts` without claiming capture loss. Strict mode
still rejects cross-build ownership; malformed or foreign private envelopes
remain errors. Old recordings are not imported into the current graph.

Automatic technical calls use the full trace/span pair as identity. A span ID
reused in a different trace must not overwrite a live call or its parent entry.

An observed call may specify `provenance`:

```json
{
  "workflow_id": "share-request-42",
  "actor": {"id": "alice", "kind": "user"},
  "objects": [
    {"type": "File", "id": "file-7", "version": "3", "role": "input"},
    {"type": "Share", "id": "share-9", "role": "output"},
    {"type": "User", "id": "ben", "role": "recipient"}
  ]
}
```

An actor is the application's authenticated principal at that event, not the
username submitted in a login form. Before authentication, record `actor: null`
when native state confirms that absence. Omit the field only when it was not
observed. Keep the claimed account in selected input fields. A service worker
records its own service identity; a triggering user is linked through the actual
source event or an explicit native job reference.

Identity and newly created objects may become known after entry. In Python or
Node, the activation's `result(builder)` can supply `provenance` beside `outputs`:

```python
with bo_probe.span("sign_in", provenance={"actor": None}) as bo_call:
    native_user = authenticate_credentials(username, password)
    bo_call.result(lambda: {
        "outputs": {"user_id": native_user.id},
        "provenance": {"actor": {"id": native_user.id, "kind": "user"}}
    })
```

This shows the observation boundary only; credential verification and creation
remain native application operations. Evaluate the completion builder only after
their actual result exists. A failed login keeps the observed absent principal;
never synthesize a session/workflow ID from the submitted account name. Use a
workflow reference only for a process the implementation actually identifies.
Generated file/share/message IDs belong to completion or commit facts, not an
entry that ran before they existed. Builders do not change node, call or event IDs.

These PROV/OCEL-inspired distinctions are optional facts on the same graph.
Model node IDs, call/event IDs, trace/span IDs, business instance IDs and object
IDs stay distinct. Shared objects do not merge executions or prove causality.
Business/state lifecycle declarations remain authoritative for their meanings;
an OTel error/status is not a business outcome. There is no added ontology layer
or claim of OWL reasoning/full OCEL conformance.

## Coding and acceptance

Every batch recalls the backend/registrations, independently scans affected
sources, refreshes mappings and runs existing checks. `scan`, `inspect` and
`verify` reject stale registrations. The latter also requires actual backend
health and trace identity when configured. Static registration alone cannot
replace a real execution witness. Preserve original mapping, state, business,
on/off/fault, denied/error and architecture checks.

Record independent native context comparisons in the existing protected
`bo-mapping/v1` plan's `context_fields`. At least the recorded `actor`,
`workflow_id` and `objects` components need native comparisons per exercised
case, node and phase when present; verification rejects unplanned metadata.
Include login before/after
verification and generated-object outcomes when relevant. Read expected values
from native session/storage/SDK facts, never from the graph or probe output.

```json
{
  "id": "login-entry-principal",
  "node": "sign_in",
  "phase": "enter",
  "case": "invalid_credentials",
  "source": "Native request session before authentication",
  "actual": ["observations", "principal_before_authentication"],
  "mapped": ["provenance", "actor"]
}
```

Add this row to `context_fields` alongside the existing state/revision/build
mapping fields and protected cases. A missing actor is not the same as explicit
null. Both paths must exist; mismatches fail the mapping report even if the HTTP
response and business assertions pass. Keep these rows across later iterations.

For repeated or concurrent calls with different native facts, retain the complete
scenario and join independent native records to events by explicit identity:

```json
{
  "id": "review-call-principals",
  "node": "review_file",
  "phase": "enter",
  "case": "self_review_then_other_admin",
  "source": "Native function arguments and current SDK context at entry",
  "each": {
    "collection": ["native_calls", "review_file", "enter"],
    "actual_key": [["trace_id"], ["span_id"]],
    "mapped_key": [["trace", "trace_id"], ["trace", "span_id"]]
  },
  "actual": ["actor"],
  "mapped": ["provenance", "actor"]
}
```

`collection` addresses a native-record list in that scenario. `actual` is then
relative to each record. Key paths on both sides identify the same execution;
read SDK identity directly at the native boundary and business values from native
arguments, session or storage. Do not copy values from observation events. Both
trace and span IDs are needed for an SDK key. Arrival order, labels and timestamps
do not establish a match. Duplicate native keys, unmatched records/events and
incorrect values fail. Every observed context component remains covered. Keep
full caller facts in complete acceptance; minimal headers belong to focused
recording tests and cannot substitute for a complete run.

Use native facts at the same boundary as the observed field. For example, a
logout function can return before its HTTP caller clears the session; a final
logged-out session cannot justify an absent actor at that earlier function exit.
Likewise, a handler can throw before the framework creates its actual 500
response. Prefer supported upstream HTTP instrumentation around the complete
framework response; verify its normal, denied and unexpected-exception paths.
Do not guess a status code or rewrite an existing observation to match the end.

Derive HTTP coverage from the native route inventory and the actual frontend
actions. HTML forms, page loaders and download routes are entrypoints too; an
`/api/` prefix is not a coverage boundary. Exercise the real browser command paths
and compare native responses, including redirects, with their recorded status.
A manually observed handler return does not establish the framework's response
status. Keep observer routes, assets and export traffic excluded; retain domain
exceptions separately when the framework handles them and returns a redirect.

Capture entry fields at entry. Some framework request hooks run after SDK span
processors; their later attributes cannot justify an earlier event. If native
route arguments need enrichment, use isolated adapter code registered before the
graph processor while the native request context is available. Compare those
arguments independently and report enrichment errors in collection health. Keep
previously emitted facts immutable.

Identify observer traffic by its actual service/listener and registered routes.
Common names such as `/api/events`, `/api/view` or `/api/recordings` can belong
to the application. A separate observer listener usually needs no exclusion in
the application's framework instrumentor. Verify both actual observer requests
and application requests with similar path names, including native 404s.

Authentication endpoints can also run inside an already authenticated session.
Exercise login on a fresh session, reauthentication on the same session and a
rejected credential attempt while a principal is present. Read the native
principal at entry and completion; entering a login function does not establish
anonymous identity. Keep caller identity separate from the newly authenticated
result. A handler may clear or update the session before calling a domain
function: request-entry identity cannot justify a later function-entry fact.
Read each node's exact native boundary through the observation adapter, without
adding observer-only domain parameters or causing the reader itself to emit
business events. Observation checks preserve existing session behavior; they
do not prescribe whether rejected reauthentication keeps a previous login.

One caller attempt can contain several native state-machine instances. Preserve
the snapshot protocol's instance identity in live views and saved frames, separate
from caller/entity/object labels. Include an interleaved multi-instance case when
checking state replay. Compare only the same known instance; ambiguous historical
labels do not establish a transition.

For relevant changes, exercise concurrent calls, detached children, cross-worker
carriers, linked jobs, selected object roles, capture focus, recorder stop/flush,
and observer exclusion. Keep unresolved parents or external spans explicit;
require captured owners in complete acceptance. Sampling and dropped events are
still capture gaps. Verify business behavior independently of telemetry.

```text
python observer_runtime/bo_trace.py check --root PROJECT
python observer_runtime/bo_trace.py export --recording recording.json --out review/provenance.json
```

The export retains raw events, trace checks and qualified event/object relations.
It is `bo-provenance/v1`, not an OCEL serialization. Web advanced event details
show the same trace/object data; graph and Timeline share causal spans and links.

Repository verification also installs `requirements-telemetry-test.txt`, which
tests real upstream Flask/urllib instrumentation and observer-transport suppression.
It is not the application's dependency list. Use batched upstream exporters for
external network export; keep processor callbacks bounded and nonblocking.
