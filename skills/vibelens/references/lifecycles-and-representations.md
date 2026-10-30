# Lifecycles and independent representations

## Capture actual operation boundaries

An operation may span several functions, decisions, queries and waits. Its entry
starts its lifetime; its actual return or exception ends it. The graph retains
running, waiting, normal-return, exception-exit or unknown observations. These do
not determine business success or failure. The timeline uses the same
invocation evidence to draw duration bars and nested calls/returns. State nodes
also have occupancy intervals established by captured native state changes, including active ancestors. Native activity frames supply running/waiting intervals without invented function calls. Intervals already active at the recording boundary show a minimum observed duration (`≥`); they do not claim an unseen start.
Static files, source mappings and containment do not establish execution lifetimes.

## Register meanings when constructing nodes

Use the project's existing lifecycle vocabulary when the user or implementation
defines it. Bind each state to a real event or a captured scalar value. Clarify
uncertain business meaning in conversation and reconcile implementation details
within coding. Omit `lifecycle` for the generic observation vocabulary; never
invent success/failure, waiting, cancellation or recovery requirements.

For example, a node that already captures the boolean `allowed` output can name
its observed rejection without reclassifying every normal return as success:

```json
{
  "lifecycle": {
    "states": [
      { "id": "checking", "label": "Checking access", "kind": "active" },
      { "id": "rejected", "label": "Rejected", "kind": "ended" }
    ],
    "bindings": [
      { "phase": "enter", "boundary": "start", "state": "checking" },
      {
        "phase": "return", "boundary": "end", "state": "rejected",
        "when": { "direction": "out", "field": "allowed", "equals": false }
      }
    ]
  }
}
```

Each state has a stable `id`, short `label` and timing `kind`: `active`, `waiting`
or `ended`. Bindings select `phase`, optional exact `when` and `boundary`:
`start`, `update` or `end`. Unmatched events on directly observed operations use
generic boundaries. An exception remains an exception even if the caller later
recovers. Missing completion evidence stays unknown. The declaration observes
events; it never executes guards, transitions the application or changes results.
Use one captured entity/attempt/call identity for each occurrence. A long-lived
conceptual operation needs its own observation identity rather than unrelated
function-call IDs. Emit an error boundary for an actual error exit; a false
business result remains a value or an explicitly registered project state.

A semantic node using `event_node` or `referenceOf` may register its own value
history. Only matching registered bindings establish its intervals; the owner's
function entry does not invent a parameter call. Its ID remains independent.
Native state residency continues to follow the actual state machine's frames.

Graph validation rejects malformed or overlapping bindings, unknown states,
uncollected fields and type mismatches. During each affected iteration, preserve
or update these declarations and exercise their important bindings with actual
event/value cases. Verify generic returns, exceptions and registered outcomes
separately. Source/AI labels remain overlays over node and event identities.

## Probe a real operation

Python's portable probe supplies a context manager:

```python
with bo_probe.span("share", lambda: {"inputs": {"file_id": file_id}},
                   entity=file_id, attempt=request_id) as bo_operation:
    with bo_probe.span("check") as bo_check:
        allowed = check_access(actor, file_id)
        bo_check.result(lambda: {"outputs": {"allowed": allowed}})
    bo_operation.record("wait", lambda: {})
    await resource.acquire()
    bo_operation.record("read", lambda: {})
    await save_share(file_id)
    bo_operation.result(lambda: {"outputs": {"shared": True}})
```

Declare every selected field in the model's capture allowlist. Nested spans
inherit this probe's producer/entity/attempt scope. Contexts work across `await`;
business results and the original exception remain with the application.
Observation builder/queue/transport failures stay isolated. Detached/background
work owns its own lifetime and must not be represented as an awaited child.

JavaScript uses explicit scopes, including browser-compatible async parentage:

```javascript
await bo_probe.span("share", async (bo_operation) => {
  await bo_operation.child("check", async () => checkAccess(actor, fileId), {
    outputs: (allowed) => ({ allowed }),
  });
  await saveShare(fileId);
  return true;
}, { entity: fileId, attempt: requestId, outputs: (shared) => ({ shared }) });
```

For a synchronous JavaScript boundary, use `startSpan`, then `finish` or `fail`
exactly once. Do not turn every event into a new call ID inside the same scope.
Do not finish a business scope at an intermediate decision or database commit.
Span helpers set `lifecycle: "span"` on their events. An intermediate decision, commit or transformation inside such a span never closes it. Legacy commit-only records remain readable. An entry without completion stays open; overlapping ID reuse is ambiguous.
Invalid timestamps use event order. Multiple producer clocks remain qualified.
No static ancestor is assigned the union of its children's execution by guess.

## Keep semantic and physical identities separate

A source parameter has one deterministic AST identity (path, function symbol,
parameter name). A semantic representation has its own stable node ID:

```json
{
  "id": "sharing-status",
  "kind": "data",
  "semantic_role": "state_parameter",
  "label": "Sharing status",
  "summary": "The current state argument of share_file",
  "represents": {"path": "sharing.py", "symbol": "share_file", "parameter": "state"}
}
```

The code index resolves this declaration to one existing parameter node and emits
an edge with `mapping_role: "equivalent"`. It preserves both endpoint IDs and
the exact source reference. Renaming/deleting the parameter fails source mapping
validation until the declaration is reconciled. Maintenance checks these mappings
even if the optional full code view has not been opened. A state parameter is a
value representation; it does not add a new enum state or weaken the statechart's
strict state projection.

Equivalence is static mapping metadata. It is not a call, return, value-copy or
authorization witness and has no transfer animation. Source/explained display
names remain overlays. Existing `referenceOf` entries still mean a layout/group
reference to one identity; they do not implement independent semantic facets.

## Verify a coding batch

- Test parent entry, child start/completion, waiting/resuming and parent return;
  compare graph statuses and bars at the same exact event IDs in 2D and 3D.
- Exercise failure, overlapping IDs, detached work and missing boundaries. Keep
  open/unknown evidence visible; do not synthesize completion to make a bar fit.
- Check native state occupancy and exact frames separately from call lifetimes.
- Re-run a source-parameter rename/removal negative test. Preserve node IDs when
  editing labels and avoid creating a second physical parameter with a new label.
- Test live, active recording and saved replay, interval selection, bottom depth,
  single-layer mode and zoom. Viewer actions must produce zero business events.

The live inspector begins at its first snapshot. Earlier events stay in baseline
context and are not replayed against that later state. Live history is bounded
at 20,000 events; reaching the limit is explicit. A graph build change resets it.
Persist a recording for a retained operation interval. Missing native frames stay
unknown, including when the service has evicted older bounded snapshots.

An invocation already open in retained pre-recording context appears left-clipped
at the observation boundary. Its original entry ID remains available; it is not
replayed as a new operation. Completed earlier operations create no new bars. An
explicit dependency on an earlier fact can have a hollow boundary marker. Missing
entry evidence remains missing; static containment does not supply it.

Child helpers inherit entity, attempt, scope and basis only. A parent's native
state revision and direct dependency list do not automatically belong to its
child. Specify the child's own state snapshot or inputs at their real boundary.

The scope exposes its queued entry event as `entry_id` (Python) or `entryId`
(JavaScript). Use that exact event ID for explicit cross-producer dependencies;
`parent_call_id` stays within one producer/entity scope. A failed enqueue returns
no entry ID and must not become a fabricated dependency.
