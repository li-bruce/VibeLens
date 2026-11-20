# Native behavior bindings

Use this reference when a project pins `bo-behavior/v1` in its `bo-project/v2`
envelope. Application state machines, policy functions and effects remain
authoritative. The Python observer checks selected facts and renders them.

## Bind the confirmed scope

Read the complete model inventory, including independent models and shared rule
consumers. Add `model.behavior_bindings` with schema `bo-behavior-bindings/v1`.
Pin the current semantic `definition_sha256` from `bo_behavior.py validate`.

For every variable, identify actual writer functions, an independent native reader,
an observed field and relevant cases. Read-only values can have no writers. Bind
each action's entry, actual completion, parameters and applicable return,
exception, cancel and rollback boundaries. An action may commit and subsequently
throw; retain both facts when that is the expected case.

Every value witness declares:

- Documented reader/writer sources (`path`, `symbol`). Readers may be test support
  functions; their values must come from native data independently of observations.
- A capture site: `node`, `phase`, selected JSON `path` and optional explicit `when`.
  Collect required fields only, following existing redaction rules.
- A native result collection and value path in the observation-test payload.
- Keys on both sides: model, instance, invocation, attempt and build. Repeated
  reads also need sample/revision identity. Use existing object provenance and
  call context; event `scope` is a string, not a model descriptor.
- Independent acceptance case IDs, with independently defined business outcomes.

An inner commit has its own event/call identity. Use its actual parent call when
the independently read result belongs to the enclosing action. Keep the inner
identity intact.

## State context and operation inputs

Classify each selected value before writing a state binding. A snapshot's
`context` belongs to the complete native state version: its values must be read
at that version's actual boundary. A freshly evaluated permission, request
argument or external response usually belongs to the current event's typed
`payload` and rule evidence. Bind the native guard to that input. A stored last
decision may be context, but a new decision cannot silently replace it at the
same revision. Independently changing state requires its own native version or
an explicit jointly versioned snapshot; observation must not invent revisions.

Test a changed input while the source state remains unchanged, followed by the
actual allowed/denied transition. Keep both the pre-state read and the evaluated
input. The collector validates the complete context, not just the state label.

## Cross-model boundaries

| Declaration | Native facts |
|---|---|
| Handoff | Send/receive correlation and payload; acknowledgement when declared |
| Shared read | Selected value; explicit joint-read group and revision or transaction when required |
| Resource | Resource, holder and acquisition identity on acquire/release |
| Join | Invocation correlation, arrivals and joined member identities |
| Transaction | Member operations and actual commit with native transaction identity |

Each selected field has an independent value witness. Reuse OpenTelemetry,
ContextVar/AsyncLocalStorage or explicit causal references at queue, thread and
callback boundaries. Equal values and nearby timestamps do not establish delivery.
A pending job or held resource is not automatically a business failure. Cases and
native state/activity checks establish required progress, capacity and release.
These witnesses do not prove distributed atomicity or exactly-once delivery.

## Coding and checking

Keep probes in isolated `bo_` wiring. Observation off, unavailable, failing and
queue-limited must preserve native business effects. Observer/viewer/analysis
operations stay excluded. Supply concise English docstrings/JSDoc on mapped
functions and important parameters. Locale overlays preserve IDs and meaning.

The existing workflow checks bindings during inspection and actual values during
verification. Independent source inventory, native machine/policy checks,
protected mapping plans, probe health, mode parity and business tests remain
required. New source files cannot disappear behind an unchanged graph.

Focused read-only diagnosis uses the pinned project and existing sync config:

```text
python SKILL/scripts/bo_behavior.py bindings --root PROJECT --sync-config sync.json
python SKILL/scripts/bo_behavior.py runtime --root PROJECT --sync-config sync.json --observations checks/native.json
```

These commands do not accept a batch. Continue through the existing
`recall → begin → scan → inspect → verify → accept → check` workflow.
Use [behavior iteration evidence](behavior-iterations.md) to review changed meaning,
refresh bindings and interpret the separate coverage results.

Report definition, intent, mapping, capture, native rules and business results
separately. Faithfully captured invalid application values remain visible.
Analysis-only bounds never clamp production values; diagnostics distinguish
`outside_analysis_domain` from `outside_application_domain`.

Value correspondence does not prove property-preserving abstraction. Refinement
preservation and optional formal analysis need their separate evidence.
