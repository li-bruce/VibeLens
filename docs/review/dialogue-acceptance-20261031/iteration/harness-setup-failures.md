# Harness setup failures

These failures concern the independent test harness, not a passing application check.

- The first evidence-negative-control launch imported `BOStateGraph` from
  `bo_observer.bo_stategraph` and exited with `ModuleNotFoundError` before running
  cases. The public standalone entrypoint is `bo_stategraph`. The harness now
  imports that module; no application source, checker, or expectation was changed.
- The first negative-control preflight read an old `review/runtime-observations.json`
  sidecar. It correctly refused to run cases because those observations had an old
  build and no required witnesses. The accepted gate used a newer command result.
  The harness and snapshot utility now read the exact stdout retained in the active
  accepted change's `checks/observations.json`; they require its successful exit.
  The rejected preflight is retained in `original-v1-negatives-01/negative-controls.json`.
- A proposed historical API-index check forced `selectOption("api")` even though
  the saved-recording viewer disables project/code/API options. The handler
  correctly refused to load a current source index into historical facts, and the
  forced test timed out. `timeline-byte-identity-copy-02/` retains this attempt.
  The harness now verifies those controls are disabled and reports this feature as
  unavailable. It does not claim historical API-index replay passed; live API
  navigation is covered separately by the actual viewer tests.
- The first saved-view seed assumed a direct login-to-upload flow edge. The
  accepted model represents login through its authentication/implementation
  mappings and has no such direct flow edge. The seed now selects the existing,
  unchanged `flow_upload_share` relation. The failed setup remains in
  `original-v1-ready-01/saved-view.json`; the model was not changed to satisfy it.
- The first post-iteration structure check incorrectly required the generic
  `app/policy.py` evaluator source to change. The iteration reuses that evaluator
  and adds three operations to the policy declaration. The corrected check requires
  changed application source, the actual new policy branches, valid roots, retained
  shared rule identities and every old policy case. The rejected attempt remains in
  `original-v2-structure-01/structure-and-data-update.json`. No project rule or
  protected expectation was changed for this harness correction.
- The next structure attempt treated catalog fields as plain names; the protocol
  supplies typed field objects. The corrected check reads their `name` attributes
  from the **observed catalogs**, checks both new columns and the native state
  constraint, and excludes declaration-only data from that comparison. The
  `TypeError` receipt remains in `original-v2-structure-02/`.
- The third structure attempt passed the metadata and native constraint assertions,
  then failed to remove its own temporary SQLite copy on Windows. A SQLite
  connection context commits or rolls back but does not close the connection.
  The harness now uses `contextlib.closing` for both connections. The failed
  cleanup receipt remains in `original-v2-structure-03/`; the original database
  was opened read-only and was not modified by these assertions.
- The first personal-view check expected the selected view from before the whole
  dialogue to remain selected. The intervening confirmed design preview had
  intentionally switched to overview (visible in its original screenshot). Saved
  filters, pins, expansion, annotation and hidden relation all survived. The retest
  checks the actual selection at navigation, chooses the retained custom view
  through the native control, waits for server acknowledgement and reloads again.
  It still requires the exact original positions and settings. The failed first
  assertion remains in `original-v2-view-01/view-update.json`.
- The first bounded-sink copy launch still read native facts from the original
  project's fixed database path. Its new share correctly did not exist there.
  The harness now accepts an explicit `BO_DIALOGUE_TRIAL_ROOT` for an owned copy;
  the original project remains the default. The failed setup is retained in
  `operations-batch-sink-copy-01/`; no recording had started.
- The listener regression's first run after the connection fix reached all asset
  and zero-sequence assertions, then compared the `EventHistory` container itself
  with a list. The assertion now reads its public `snapshot()`; the expected empty
  history is unchanged. Both results remain in `viewer-transport-after.log` and
  `viewer-transport-after-02.log`. The pre-fix ten-connection timeout remains in
  `viewer-transport-before.log`.
- Review found that the new export-link tests had replaced five existing exporter
  tests. The original file was restored byte for byte from `HEAD`; the three new
  tests now live in `test_trial_dialogue_links.py`. All eight pass, including the
  original checks for reasoning exclusion, delivered prompts and token metadata.
- The extra screenshot helper initially assumed raw call routes were available
  immediately after selecting a recording. It first read zero routes, then timed
  out after waiting for routes while still using the prior coarse replay grain.
  The corrected helper waits for the exact recording ID and selects the native
  raw-event control, just as the full timeline tests do. Those existing tests and
  their same/cross-layer assertions were retained. Both earlier helper versions
  remain in `experiments/visual-proof/`; these were screenshot setup failures.
- The later screenshot deliberately saved a state-level timeline cutoff. The next
  generic timeline run inherited it and correctly showed no deeper-layer handoffs;
  its initial cross-layer assertion failed. The final harness explicitly restores
  all layers and expands tracks through native controls before that assertion,
  then tests the cutoff again later. The assertion itself is retained. The failed
  setup and current backend-health diagnosis remain in
  `timeline-viewer-mime-copy-timeline-04/results.json`.
- The final original-project scope test exceeded the recorder's documented
  2,000-event **pre-recording context** bound. The four selected interval events
  were complete and health was clean; the earlier test expected no context notice.
  `original-v2-final-02/results.json` retains that failure. The retention-aware
  retest independently compares the saved context with the actual last 2,000
  source events (then applies the captured scope), permits only that exact notice,
  and adds consecutive interval sequence/count plus zero-error/drop/pending checks.
  It still requires four real review events, approval state and restored full
  HTTP/data capture. No recorder requirement or timeout changed.
