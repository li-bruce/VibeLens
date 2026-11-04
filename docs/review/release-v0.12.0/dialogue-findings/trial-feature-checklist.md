# Live conversation trial: feature acceptance

This is a checklist derived from the current viewer and service source, **not a
passed test report**. Run against the independently installed trial project after
its normal verification gates pass. Record the installed version/hash, build ID,
actual application/graph URLs, browser, and graph revision beside every result.
Use the application's confirmed file-sharing behavior; do not add business rules
to satisfy the checklist. Keep business outcomes and observation results separate.

For each row retain **pass / fail / not exercised**, the exact action, evidence
paths, and any repair/retest. API assertions complement real pointer/keyboard
interaction; directly assigning viewer internals is not UI acceptance.

## Capture, Graph and Timeline

| ID | Reproducible action | Required observation |
| --- | --- | --- |
| R1 — Live | Open the application and graph. Perform login, one authorized operation and one denied/error operation already in scope. | `/api/view` contains actual identities, selected values and request results. Graph highlights the corresponding nodes; declared state changes match the application's persisted state. Read-only graph polling, source inspection and preference saves add no business events. Capture actual HTTP response bodies/statuses separately. |
| R2 — Full recording | Select **All core events** (`#capture-mode=all`), Start, operate the application, Stop. | `/api/recordings` reports a stopped interval. `/api/recordings/{id}` retains actual start/end, selected fields and identities; a normal stop drains accepted work and has no unexplained gaps. Match submitted/completed/pending counters and the final application response. Repeated start must not create duplicate active recordings. |
| R3 — Focused recording | Select an observed operation/region, choose **Selected region only**, record it plus an unrelated real operation. Repeat with a source node that has an explicit capture binding. | The request is `POST /api/recordings/start` with `scope.mode=focused` and resolved root IDs. Saved capture scope matches; unrelated value payloads are absent while necessary boundary/parent context remains identified. Producer filtering is exercised before payload construction. An unbound static source node rejects capture instead of claiming it was observed. |
| R4 — Replay and values | Open the stopped full recording. Next/previous, drag the step slider, change Business/Functions views and Step detail, inspect Event data, then Locate. | Selected raw event identity remains consistent with Graph and Timeline. Each step shows its own before/after values and native state evidence, never future final values. Transfers reference witnessed events/calls/data rather than mere static adjacency. Exported raw recording and business database remain unchanged. |
| R5 — Durations and concurrency | Record two genuinely overlapping requests from different signed-in users plus their existing asynchronous work. Compare raw entry/exit facts with Timeline. | Business operations have measured intervals when their own boundaries exist; state residence follows real frames. One row per displayed layer in each execution band; overlapping roots get separate bands, sequential roots can reuse a band. Parent/child and async links retain actual identities. Horizontal same-layer and vertical cross-layer connectors match Graph evidence. `graphDebug.timeline` exposes `rows`, `executions`, `lifecycles`, `routes`, `transfers` and unassigned observations for numerical checks. If requests did not overlap, concurrency remains **not exercised**. |
| R6 — Timeline interaction | In live mode and saved replay: drag ruler, pan tracks, Ctrl/Command-wheel zoom, drag overview handles, resize/maximize, select bottom observation depth, choose Single layer, collapse/expand an execution band. Shift-drag a range and use Loop selection. | Cursor and graph selection agree. Each folded band retains its business row where present; hidden lower layers stay stored. Zoom preserves the selected time/identity, and short bars keep their measured duration. Range/loop operate on recorded events. A live timeline uses bounded live history; saved recording provides durable replay evidence. |
| R7 — Pause/skip/clear | Pause on a transfer step; open Steps, skip an intermediate step and loop a small range. Include all again; clear only one selected stopped recording. | Pause repeats only the current presentation. Skips do not erase facts or undo their effects in later frames. Loop stays within selected included steps. Clear removes the chosen stopped record; another recording and business data remain intact. Run with normal motion, then confirm reduced-motion suppresses animation without losing facts. |

API cross-checks: `GET /api/recordings`, `GET /api/recordings/{id}`,
`POST /api/recordings/start`, `/stop`, `/clear`; use the real service's same-origin
requirements. Save one full and one focused recording before any iteration.

## Graph navigation, identity and iteration

| ID | Reproducible action | Required observation |
| --- | --- | --- |
| G1 — Three models | Open Business, States and Rules presets. Inspect a real action → state event/transition → shared rule → implementation chain. | Each model has meaningful relations and explicit cross-model links. State values/guards match the executable definition; positive and negated guards remain distinguishable. Static/conceptual links do not acquire fabricated execution duration. The source-free design viewer has already been tested separately; it supplies no recording controls or runtime facts. |
| G2 — 2D/3D parity | In both modes expand/collapse; drag a node and an expanded region; pan/rotate; hide/reorder layers; change spacing; select straight/curve/polyline routes; Arrange → Fit. | Same canonical IDs, types/colors, nesting, counts and observations survive. Region dragging moves the intended group. 3D is genuinely rotatable and keeps populated layers at uniform selected spacing. Straight cross-layer edges remain straight; routes update after movement. Measure visible glyph/region bounds after Fit; retain screenshots and page/console errors. The repaired source-free Fit regression must remain covered. |
| G3 — Filters and saved views | Hide one concrete node and edge, then one type/layer; save a custom view. Use Delete on selected node/edge/layer. Finally choose All elements. | Explicit exclusions work in 2D/3D. All elements restores every exclusion while retaining intentional folding and positions. Inspect a dynamically projected hidden-layer relation: its original path/evidence is available and it is not mislabeled as a direct physical call. |
| G4 — Source and names | Open Project structure, Code structure, Functions and parameters; select a function/parameter, enable Local code, inspect Source. Toggle AI names and add a personal alias/note/core marker. | Project folders/files correspond to scanned in-scope sources, excluding dependency/generated/cache trees. Functions show actual call, parameter and binding relations. Full file loads on demand with the correct declaration/token highlighted; adapter-only payload fields show owner context without a false lexical highlight. IDs, bindings, event references and native values are identical across naming modes; unavailable explanations fall back honestly. |
| G5 — Persistence across iteration | Before the approved business change/refactor, save coordinates, pins, expansion, filters, per-view layers, notes and both mode cameras. Wait for server save, reload, then perform the normal recall/begin/scan/verify/accept iteration and reload again. | Surviving stable IDs keep personal configuration; changed source and affected concepts/API/storage structure update from real evidence. New nodes receive placement without resetting old ones. A same-build process restart keeps current recordings. A changed build leaves obsolete replay and removes old records from the current list; direct old-record reads reject. Check actual `/api/preferences` acknowledgements, not only browser memory. |

Inspect both the base graph and client-loaded optional code detail. A successful
base `/api/view` does not establish full code-layer replay coverage. Preserve the
recorded source/tree identity when opening old exported evidence independently.

## Conversation controls and independence

| ID | Reproducible action | Required observation |
| --- | --- | --- |
| C1 — Natural control | In the explicitly activated trial conversation: `/vibelens 只看上传到共享的业务操作和权限判断，保留相关状态`. Resolve the actual confirmed chain, inspect, plan and apply via `bo_control.py`. Then request a narrower replay of the exact stopped recording. | The viewer's scoped `vl_session` URL applies the intended IDs, original edges and layout. `status` must report applied, not merely queued. Requested nodes are visible after leaving a previous narrow preset. Replay filtering changes private selection, not original events/capture. The AI interprets language; the CLI validates the resolved specification. |
| C2 — Rejected controls | Test missing prefix, unsupported source-edit control, stale build plan, and a separate real conversation/project attempting the scoped control. | Clear rejection; no source, state definition, raw recording or another conversation's preferences changes. Do not manufacture a conversation identity to obtain authorization. If the host cannot provide a second real identity, use existing regression evidence and mark this trial case not exercised. |
| C3 — Optional Web | Run `bo_web.py mode hidden --root PROJECT`, then `mode disabled`, finally `mode visible`. Exercise a business operation and native state query in each mode. | Hidden removes an integrated entry while its direct graph URL remains usable. Disabled rejects graph/observer Web routes with `bo_web_disabled` while business execution and separately configured collection/native queries retain their behavior. Restore visible. Also run the project's existing observation-off/fault checks; Web visibility alone is not a probe-off test. |

## Current boundaries to report accurately

- **All core events** means connected allowlisted instrumentation, not every
  variable, source statement or possible static call. Focused capture cannot
  recover uncaptured outside payloads. Unfinished/missing boundaries stay explicit.
- Generic normal-return/exception-exit is observation, not business success or
  failure. Only declared, value-backed lifecycle meanings add those labels.
- Timeline bands are concurrency lanes, not an ever-growing band per sequential
  request. Static files/containment/source mappings do not establish lifetimes.
- The recording catalog filters obsolete builds and direct reads reject them;
  it **does not physically delete all old recording files**. Retention or explicit
  cleanup is separate. Do not report disk erasure from an empty current list.
- 2D/3D coordinates are separately saved; Arrange shares the layout solver, not
  a promise of identical saved camera/drag state. Dense relation layouts can still
  cross; synthetic performance checks are not a guarantee for every device.
- The shared native binding supports one primary bound state model. Generic
  multi-machine/DMN/external policy-engine support must not be inferred from a
  diagram. Keep unsupported project requirements visible rather than weakening
  definitions or tests.
- `/vibelens` is a Skill conversation convention, not a registered native Codex
  slash command or operating-system sandbox. Use `$vibelens /vibelens …` when the
  client intercepts unknown slash commands. Controls do not execute application
  business actions or edit the installed Skill.
- Hidden Web entry behavior requires the application to use the integration's
  entry rendering; an independent observer page has no application link to hide.
  Disabling Web does not uninstall files or disable probes. Packaging/removal, if
  tested, uses the existing architecture guard and an isolated exported copy.

## Source anchors

Canonical implementation reviewed: `assets/stategraph-viewer/index.html`,
`viewer.js`, `recording-timeline.js`, `trace-executions.js`, `source-view.js`,
`preferences.js`, `view-lifecycle.js`; `scripts/bo_observer/service.py`,
`observation/recording_session.py`, `web/bo_web.py`, and `control/cli.py` under
`skills/vibelens/`. Supporting references: `recorded-analysis.md`,
`lifecycles-and-representations.md`, `conversation-controls.md`,
`code-structure.md`, and `viewer-workflow.md`.
