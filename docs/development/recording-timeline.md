# Recording timeline

The execution timeline presents live observation, active capture and saved recordings. It shares the
graph's event IDs, replay cursor, state reconstruction, playback speed and loop
selection. Dragging the ruler or selecting a mark seeks the graph; playing the
graph advances the same cursor in the timeline.

## Reading and interaction

- Rows group observed nodes by the graph's semantic layers and layer order.
  **Current view** follows visible graph nodes; **Recorded nodes** includes the
  recording's available graph inventory. Expand a layer to inspect its nodes.
- Filled bars join a recorded entry and completion of the same invocation.
  Diamonds mark decisions, changes, commits and parameter reads. An unfinished
  entry has an open end. Hollow marks locate a declared source mapping; they do
  not claim that an uninstrumented function ran.
- Select a mark to inspect its inputs, outputs and timestamp beside the timeline.
  The graph's existing changes panel shows the corresponding state/value delta.
  **Locate** focuses its graph node. Visible causal chains use recorded parent
  calls and dependencies; the graph's existing transfer validator still decides
  which graph edges animate.
- Drag the ruler to scrub. Drag empty tracks to pan; wheel to scroll rows and
  Ctrl/Command-wheel to zoom around the pointer. The overview window supports
  dragging and resizing. Shift-drag selects a playback range; **Loop selection**
  sends its event IDs to the existing replay selection. Arrow keys seek, +/- zoom,
  Home/End select the first/last visible event, and Escape clears a range.
- **Observation depth** retains a contiguous prefix of the chosen graph-layer order. **Single layer** isolates one layer; selecting **All layers** restores the combined view. Lower links disappear without shortcuts or data deletion.
- The dock can be hidden and resized. Visibility, height, row expansion and scope
  are project preferences; event selection and viewport reset for another recording.

## Evidence and module boundaries

`trace-context.js` clips already-open witnessed scopes at the observation boundary and preserves their original entry IDs. It does not replay completed pre-recording work.
`trace-session.js` owns the bounded live baseline and retained event window.
`trace-lifecycles.js` pairs invocation boundaries; `graph-activation.js` exposes
persistent running/waiting/completed/failed states and concurrent counts.
`trace-residencies.js` follows actual native state/activity frames, including
active ancestors and waits. It does not infer lifetimes from static containment.
`trace-flows.js` indexes causal geometry and omits hidden endpoints without
manufactured shortcut calls. Explicit semantic parameter mappings resolve in
`code_graph/query.py` through exact AST identities and never become runtime flows.

`trace-evidence.js` owns invocation identity and parent-call lookup, shared by
graph transfers and timeline indexing. `trace-index.js` builds immutable bars,
marks, layer/node rows and causal references. `trace-viewport.js` owns bounded
pan/zoom/search arithmetic. `trace-paint.js` draws only visible rows/time ranges.
`recording-timeline.js` owns DOM, pointer/keyboard interactions and cleanup.
`viewer.js` supplies the graph inventory and replay plan, calls `seek`, and supplies
the exact graph transfer IDs. No additional replay timer or business API is added.

Pairing includes build, run, producer/stream, entity, attempt, node and call ID.
Repeated sequential IDs form separate invocations; overlapping reuse is marked
ambiguous. Missing/reversed timestamps switch the axis to event order. Wall-clock
durations are shown only for ordered timestamps in one producer clock domain;
cross-producer positioning never asserts synchronized clocks. Recording gaps and
focused capture remain visible. Static declarations without runtime evidence do
not acquire durations. The recording and its exact native state frames remain
unchanged.

The existing native data adapters finish a transform with `phase: change` and
`outputs.status: transformed`. Only a node declared as a data transform treats that
pair as completion; an ordinary business value with the same text stays an instant.
Genuinely unfinished/ambiguous intervals use faint dashed outlines.

Canvas drawing uses device-pixel-ratio limits, visible-row culling and time-range
indexes. Scrubbing is coalesced into animation frames and only changed replay
ordinals invoke state reconstruction. Event details use text nodes, not HTML.
The component disconnects its observer, handlers and queued frames on disposal.

The design borrows duration slices, instants and causal flows from
[Perfetto track events](https://perfetto.dev/docs/instrumentation/track-events),
and chronological navigation from the
[Chrome Performance panel](https://developer.chrome.com/docs/devtools/performance/reference).
The implementation uses the existing VibeLens recording protocol and Canvas API.

## Acceptance

Verify overlapping calls, reused IDs, missing/invalid clocks, open calls, gaps,
cross-producer references, exact state/value changes and static projections.
In an actual recording, scrub/click/play/range/loop/skip must agree with graph
event IDs and transfer IDs in both 2D and 3D. Exercise pointer, keyboard, touch,
resize, zoom, scope changes, English/Chinese and a large recording. Compare the
recording bytes and business event count before and after presentation actions.
Retain failed runs, fixes and retests separately. Run the existing replay suite,
managed-example acceptance, formatting/lint and exported-package checks.

## Lifecycle extension

Portable probes expose nested spans with `lifecycle: "span"`. Only real return or
error closes an explicit span; intermediate commits and decisions keep it active.
Legacy commit-only records remain readable. Begin the recording timestamp before
reading its initial snapshot so concurrent delivery cannot move the first event
before the start boundary. Historical boundary metadata is visually bounded by
actual event times with a note; raw timestamps are unchanged. Invalid or reversed
producer timestamps still use event order. Windows replacement sharing failures
have four attempts and a 35 ms sleep budget, then retain the existing interruption
and gap behavior.

See [the capture and identity contract](../../skills/vibelens/references/lifecycles-and-representations.md)
and [this iteration's evidence](../review/timeline-lifecycle/README.md).
