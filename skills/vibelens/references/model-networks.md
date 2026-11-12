# Models, subnetworks and instances

A layer is a presentation category. A model defines behavior or structure. An
instance is a particular application object or invocation. These are separate
identities. An application may be several disconnected networks, with explicit
connections where its actual business requires them.

## Declarations

New runtime models use `model.machines`, an object keyed by stable model IDs.
Each value has the existing strict statechart contract: engine/version, states,
values, initial, typed context/events, guards and transitions. An empty registry
is permitted when no state machine applies. `machine` and `machines` are mutually
exclusive; the old `machine` declaration keeps its existing IDs and validation.

Every native state node in a registry declares `state_model_id`. State values
such as `ready` may repeat in different models; node IDs remain globally unique.
Every declared state must have its own matching node. Unknown references,
incomplete state coverage and unsupported engine semantics fail validation.

`model.networks` is optional presentation membership for **any layer**:

```json
{
  "id": "review-lifecycle",
  "layer": "state",
  "label": "Review lifecycle",
  "state_model_id": "review",
  "nodes": ["review:waiting", "review:approved"],
  "edges": ["review:approve"]
}
```

Members and edges must already exist. Multiple memberships are allowed: shared
functions and predicates keep one physical ID. Membership is neither containment
nor a runtime call. Cross-network relations remain ordinary typed edges in the
complete graph. Do not add fictitious edges to make independent components look
connected. Source scans still describe actual folders, files and symbols; those
physical structures need no business dialogue to exist.

Discovery retains plural business `networks`, plural `state_models`, and shared
rule operation roots. Design projection publishes membership for each business
network, state model and rule operation with its dependency closure. Shared
predicates can belong to several rule networks. The viewer offers these networks
through the normal view menu, filters and layout pipeline in both 2D and 3D.

## Bind every confirmed model

Use `bo-concept-bindings/v2` with `state_models`, a map from each confirmed
conceptual state-model ID to its native machine ID. There is no primary slot.
Two independent models cannot bind to the same native definition. Each binding
retains object identity, full state/guard/event/effect semantics, actual source
anchors, crosslinks and independent cases. Missing models fail the gate.

Legacy bindings v1 continue to bind the legacy single `machine`. Migrating them
means explicitly creating the registry, adding state-node ownership, replacing
`primary_state_model` with `state_models`, and updating producers/mapping plans.
Keep node IDs and user layouts. Preserve old recordings as their original protocol;
do not infer model IDs from repeated state names.

## Execute and observe

`BOExecutors` in Python/JavaScript registers multiple strict `bo.fsm/1` executors.
Call `step(model_id, state, event, context, payload)`; the application still owns
each object's state, guards and side effects. Registration does not introduce a
distributed transaction or run inter-model messages automatically.

Python `BOStateGraph.bo_definition()` returns `{"machines": ...}` for a registry;
`bo_definition(model_id)` returns one declaration. `bo_candidates` and
`bo_observe` require `state_model_id` for registries, including one-model registries.
Queries, validation and full exports retain all registered models.

The Python probe takes `snapshot(..., state_model_id="review")`; the JavaScript
probe uses the `stateModelId` option. Both send `bo-snapshot/v2`. The collector
identifies the object by `(state_model_id, run_id, instance_id)`, verifies its
producer/evidence/revision and retains exact state frames. Local instance ID `1`
can exist in several models. A shared caller/attempt never merges these objects.

An operation affecting two models supplies separate state-change events and
snapshots, linked through real causal/transaction evidence. Simultaneous state
changes cannot be reconstructed from timing alone. Shared resource declarations
need one execution owner; other models reference that owner's actual facts.

## Iteration and verification

`bo-mapping/v2` adds `state_models` and an `actual_model_id` JSON path to the
independent application reader. Fields may be scoped by `state_model_id`.
Every registered model must cover state, revision, build, model identity and all
declared context/configuration. Required cases exercise every model in each
required observation mode. Removing coverage fails the existing protected-plan
gate. Mapping fidelity and business correctness remain separate reports.

Test repeated local state/instance names, independent transitions, real cross-model
effects, missing/invalid bindings, capture gaps, exact replay, and a subsequent
source/model iteration. The portable executors remain flat; supported native
adapters supply hierarchy/concurrency semantics. The observer does not create a
second execution authority or claim untested cross-model invariant verification.
