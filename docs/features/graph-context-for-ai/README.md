# Graph context for an AI coding conversation

Status: proposed web feature, with the existing export foundations tested. This branch records the feature and its acceptance requirements; it does not add a browser export button.

## Developer experience

A developer finds an unexpected decision, selects the relevant nodes or relations at a replay step, and chooses **Copy context**. VibeLens previews a short explanation containing the observed values, original graph identities and source locations. The developer can paste it beside their own description in Codex or another coding tool. AI then changes the program through the usual coding conversation.

The context represents what the graph and recording establish at that moment. A compact Markdown copy serves conversation; an accompanying JSON export retains the complete selected evidence. User notes and display names remain distinct from original source identities. Copying context has no effect on the business program and does not send a message automatically.

## Current foundations and tested gaps

| Component | Current behavior | Required addition |
| --- | --- | --- |
| `graph/focus_graph.py` | Bounded neighborhoods, original relations, omitted boundaries, source bindings, build/run-scoped events and Mermaid/Markdown | Adapt the current viewer selection and exact replay cursor to this extractor |
| `layout.js: selectionContext` | Selected descendants, neighbors and regions for highlighting | Resolve displayed summaries back to original nodes/edges; distinguish selected elements from surrounding context |
| `conversation.js` | Confirmed conversation focus can enter the graph | A separate outbound context action, preview and copy/download controls |
| Run evidence | Build and producer-run filters exclude mismatched facts with explicit evidence gaps | Preserve recording identity and producer identities separately; support recordings containing several producers |
| Time scope | Existing extraction returns matching events from the selected run | Export only the chosen cursor/window and the matching calls, without including later outcomes |

Run the baseline from the repository root:

```powershell
python docs/features/graph-context-for-ai/check_baseline.py --output docs/features/graph-context-for-ai/baseline.json
```

[The retained result](baseline.json) checks the actual existing gallery captures. Build 1 exports three focused nodes and six events, including `allowed`. Build 2 exports three focused nodes and fourteen events, including `stale_review`, `forbidden` and `allowed`. Source bindings point to `policy.py`; Markdown contains the local Mermaid graph; included edges preserve their original IDs. Events from an incompatible build are excluded with an evidence gap.

An initial experiment passed `recording.run_id` as the producer run and returned no events. The corrected experiment uses the event producer's `run_id`. The recording's observer run and the business producer's run are different identities; the baseline retains this distinction. This is a discovery about the caller's required scope, not permission to relabel events.

The second capture also demonstrates the missing time filter: after the `stale_review` event at sequence 47, the whole-run export includes the later `allowed` result at sequence 117. A context copied at sequence 47 must not present that future result as already observed. The baseline reports the limitation explicitly and does not claim the complete web feature passes.

## Proposed snapshot contract

The following is a design outline, not a supported endpoint or finalized wire schema:

```json
{
  "schema": "vibelens.context.proposed.v1",
  "identity": {
    "build_id": "...",
    "model_revision": "...",
    "source_index_revision": "..."
  },
  "selection": {
    "node_ids": [],
    "edge_ids": [],
    "include_descendants": false
  },
  "time": {
    "recording_id": "...",
    "observer_run_id": "...",
    "producer_run_ids": [],
    "cursor_event_id": "...",
    "window": null
  },
  "graph": {"nodes": [], "edges": [], "boundaries": []},
  "facts": [],
  "source_bindings": [],
  "user_notes": [],
  "evidence_gaps": []
}
```

Source bindings retain path, symbol and available line/parameter location. A runtime operation field is identified as operation metadata when it is not a source variable. Summary edges carry their original members. An omitted dependency remains a named boundary; it is never rewritten into a direct connection. Static relationships, confirmed intent and runtime observations stay identifiable inside the same package.

For a selected return event, resolve input values from the enter event with the same producer/build/call identity. Use the recording's ordering and event identities for multiple producers; do not compare unrelated producer-local sequence numbers as a global clock. Missing frames or source revisions remain explicit gaps.

## Implementation sequence and acceptance

1. Define a selection adapter and snapshot validator independent of clipboard/UI code. Reuse the current extractor and model protocol.
2. Resolve original members, omitted boundaries, source references and exact cursor/window facts. Add tests before exposing an export control.
3. Add a node/edge/region context-menu action, preview, Markdown copy and JSON download in both 2D and 3D. Both renderers use the same snapshot service.
4. Exercise the full browser path on a real recorded example, then use the copied context beside a developer's issue description in a coding conversation.

Required checks cover collapsed regions and virtual edges; static-only selections; matching call inputs/outputs; stale builds and sources; missing frames; multiple producers; Python and Node.js bindings; custom names/notes; exclusion of observer operations; and zero business side effects. Cursor tests must reject future facts. Browser acceptance must inspect the copied text and downloaded JSON, rather than only asserting that a button was clicked.

The current [Pages review](../../review/guided-conversation/README.md) demonstrates the developer describing the problem and key values manually. A future presentation update can show this export action after the complete chain passes these checks.
