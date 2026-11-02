# Tracing integration decision

Status: implemented integration decision, 2026-11-01. Runtime and dialogue
acceptance are recorded separately in the review index.

## Boundaries

VibeLens retains its business/state declarations, drive/observe development guidance,
independent observer, source inventory, stable graph identities and cross-layer mappings.
The native application still owns authorization, state execution and business effects.
Tracing is a replaceable observation facility, not a state engine.

## Questions and decisions

| Question | Finding and decision |
| --- | --- |
| Does OTel reduce development? | Yes for trace/span IDs, task context, W3C propagation and supported library instrumentation. It does not supply confirmed business meaning, state declarations, source completeness or selected business values. Reuse its API/SDK behind the existing probe interface. |
| How does live observation work? | Keep the bounded VibeLens start/change/end event stream and recording barriers. Add standard trace identity to those same events. Ordinary exporters send finished spans; waiting for them would hide long-running activity. A registered SpanProcessor may bridge supported technical spans at start/end without blocking on network I/O. |
| How does coding know what to instrument? | Persist the selected backend and explicit node/source/instrumentation registrations in the observation module. Recall them before coding; scan independently; require positive, denied, exception and relevant async cases after changes. Technical HTTP entries map to API nodes, then explicit implementation relations connect user actions. |
| Is AI understanding difficult? | OTel removes custom propagation code, but business attribution is still semantic work. Small registration interfaces, source anchors and strict cross-checks reduce the burden. Neither labels nor matching file IDs establish causal ownership. |
| Must this follow OTel rules? | OTel SpanContext and W3C headers must follow their standards. Use SDK-created IDs and propagators. VibeLens JSON remains its own protocol, with optional trace and provenance metadata; do not label that JSON as OTLP. OTLP export uses upstream exporters if configured. |
| Is there a more mature alternative? | OTel is the chosen interoperability/instrumentation base. AppMap is relevant for detailed calls/source recordings, Jaeger for trace storage/query, and the Collector for routing/batching. They solve different parts; none replaces the VibeLens state network. Do not introduce multiple default recorders for the same calls. |

The maintenance benefit is an architectural expectation, not measured token or
code-volume savings. This compatibility release adds code because the native
backend remains available and standard metadata needs validation and adapters.
It reduces the tracing mechanisms VibeLens must invent as more runtimes are
integrated. It does not eliminate selected business probes, source scans or
independent implementation tests. No production overhead claim is made from
these local correctness tests.

## Alternatives

A later specification check found that [exception span-event conventions](https://opentelemetry.io/docs/specs/semconv/exceptions/exceptions-spans/)
are deprecated in favor of [exception logs](https://opentelemetry.io/docs/specs/semconv/exceptions/exceptions-logs/).
The pinned upstream instrumentors still supply those events by default; the
adapter reads them as compatibility input. VibeLens's own physical exception
facts use its live JSON protocol and annotate SDK `error.type`/technical status
according to [recording errors](https://opentelemetry.io/docs/specs/semconv/general/recording-errors/).
It adds no new legacy exception span events. A generic log-only exception bridge
is outside this trace adapter's implemented scope; it must be explicitly added
and tested before claiming that signal as captured.

- [OpenTelemetry API/SDK](https://opentelemetry.io/docs/specs/otel/trace/api/):
  standard context, spans and links across languages. Processor callbacks must be short;
  sampling, limits and transport loss remain observable acceptance concerns.
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/): optional external
  receive/process/export service. It is not necessary for the local live graph.
- [Jaeger](https://www.jaegertracing.io/docs/2.22/architecture/): mature trace storage and
  queries built on Collector components. Useful downstream, not a business/source model.
- [AppMap Python](https://appmap.io/docs/reference/appmap-python.html) and
  [Node](https://appmap.io/docs/reference/appmap-node.html): automatic detailed call,
  parameter, SQL and source recordings. Import-time instrumentation and documented
  version/framework limits need separate compatibility/performance testing. Preserve as
  a future recorder adapter rather than enabling it together with OTel by default.

## Internal integration

1. Optional Python and Node OTel bindings implement the existing probe's task-context
   interface. Without the optional package, the existing native observer still works.
2. The SDK creates spans and owns propagation. VibeLens preserves call/event identities
   and attaches trace IDs, span IDs, parent IDs and links to its live events.
3. Explicit registrations bridge automatic technical spans only to existing, source-bound
   nodes. Observer operations and VibeLens-created spans are excluded from that bridge.
4. A causal child may outlive its parent. A point fact still needs its own active call or
   a currently valid witnessed owner; an ended parent is not an unlimited lifetime.
5. Producers retain bounded queues, flush/health, capture scope and loss accounting.
   OTel presence is not evidence of complete capture or business correctness.

HTTP registration follows the application's actual routes, including HTML form
commands, page loaders and downloads. A handler return may precede the framework's
response; its interval alone cannot establish a 303 redirect, denial or 500 status.
The supported upstream framework instrumentor supplies that boundary. Test native
responses independently and exclude observer/static traffic explicitly. Trial 03
exposed an API-prefix-only integration gap; the raw browser evidence is retained.

## Concept clarification using PROV and OCEL

This adds metadata to observed facts, not graph layers or a new modeling mode.

| Existing or additional identity | Meaning |
| --- | --- |
| Model node/edge | Stable business, state, rule, API, data or source definition. |
| State-machine instance | One native machine's identity and its witnessed configuration; several machines may share one caller attempt. |
| Workflow/operation reference | A business process instance that may span several requests/traces. |
| Trace/span | One technical execution and its actual causal parent/links. |
| Event | One witnessed lifecycle boundary or selected change. |
| Object reference and qualifier | A file, share, job or user involved as input/output/subject, optionally versioned. One event may refer to several. |
| Actor | A business-authenticated principal supplied by native application code. Trace headers never authenticate it. |

[PROV-O](https://www.w3.org/TR/prov-o/) distinguishes activities, entities and agents;
[OCEL](https://www.ocel-standard.org/) supports multiple objects and qualified
relationships for an event. Reuse those distinctions without claiming full OWL reasoning
or full OCEL format conformance. Missing references remain unknown; do not infer causality
from time proximity, object equality or a static call edge. A standalone export can
project the explicitly captured object references and causal edges.

## Compatibility and acceptance

The original state-machine and core executable contract files remain unchanged.
Old JSON recordings remain readable. New optional metadata is strictly validated.
Python/Node SDK versions are locked for the tested runtimes; existing application-owned
TracerProviders are accepted without global replacement. No trace status is interpreted
as business approval or success. Existing mapping/closure and business test categories
remain separate.

Required evidence includes real sync/async operations, ended-parent children, concurrent
requests, cross-producer propagation, linked jobs/batches, multiple object roles, errors,
invalid metadata, observation exclusion, focused recording and a normal source iteration.
