# Independent browser review

All runs use the actual file input, rendered review/share forms and download
buttons. The browser supplies W3C trace IDs so native HTTP responses can be
matched by identity and path, without inferring ownership from timestamps.

| Attempt | Evidence | Result |
| --- | --- | --- |
| 01 | `dialogue-04-browser-v1-01`, corresponding log | Business UI passed. The harness read the recording dropdown before its asynchronous update, received an actual 400 payload and also inspected the cursor before seek completion. Both raw responses and the original source are retained. The recovered actual recording has 815 events, no gaps and nine exact native HTTP matches. |
| 02 | `dialogue-04-browser-v1-02`, corresponding log | Harness waited for cached 3D diagnostics to disappear. The viewer retains that diagnostic object after switching renderer. No business operation ran. Use the active mode button for this check. |
| 03 | `dialogue-04-browser-v1-03`, corresponding log | Real business actions, nine HTTP comparisons and the 2D/3D cursor passed: raw index 1054 in both modes. The recording has 1,053 events and no gaps. A later source-expansion check incorrectly requested a new current-code slice while still in saved replay. |
| 04 | `dialogue-04-browser-v1-04`, corresponding log | UI, HTTP, 2D/3D and live source expansion passed. The current projection has 957 nodes and 1,184 relationships. Its code projection retains unresolved static calls explicitly. The recording contains 1,291 new events, but the pre-recording history exceeds its 2,000-event window and reports incomplete earlier context. This is a UI result, not a complete-capture result. |
| v2-01 | `dialogue-04-browser-v2-final-01` | 4,564 events/18 native HTTP comparisons/zero gaps mechanically passed. Visual review found a false cross-instance final caption; retained as a product failure despite the mechanical result. Shared instance projection/comparison was repaired before another managed upgrade. |
| v2-02 | `dialogue-04-browser-v2-final-02` | Business actions passed. Continuing native page refresh left 1,141 producer envelopes pending at stop. The recording correctly remains interrupted with an explicit gap. |
| v2-03 | `dialogue-04-browser-v2-final-03` | Complete finite-flow capture: 6,608 events, zero gaps, drained producer. A new harness assertion passed raw protocol events directly to a function expecting canonical timeline items, causing a false zero-transition result. Raw recording and failure remain unchanged. |
| replay-04 | `dialogue-04-browser-v2-replay-final-04` | Correct canonical adapter presents seven actual transitions and no false final transition. Harness then incorrectly compared the lifecycle array to an integer; retained type error. |
| replay-05 | `dialogue-04-browser-v2-replay-final-05` | Same unchanged recording and source passed actual recorded-view, HTTP, state-instance, 2D/3D and live source-projection checks. 1,734 lifecycle intervals, 699 causal flows, 16 layer rows, raw cursor 6609 in both renderers, zero page errors. |

The corrected harness waits for saved recording selection, validates the HTTP
response/schema, waits for completed seeks and reads the current renderer's mode.
Current static expansion returns to live; saved replay retains its captured
projection. No viewer source was changed to make these harness checks pass.

The final iteration test additionally requires an empty recording gap list. The
pre-recording limit is a retained capture boundary, not a reason to fabricate
missing parents. Raw attempt 03 independently supplies complete initial-window
capture; attempt 04 supplies the live static projection. The final iteration
result must be assessed separately.

The final review uses the viewer's own `timeline(recording)` adapter before
`boFacts`; raw `bo-event` envelopes do not carry the display-only `kind: probe`.
The optional real-record regression was corrected likewise and positively checks
that identified new frames still show actual state transitions. Historical
ambiguous configurations do not justify invented transitions.

The retained all-layer screenshots show dense labels and an inherited camera
position. Their acceptance concerns actual content/cursor/state identity, not
an assertion of optimal visual layout at every zoom level.
