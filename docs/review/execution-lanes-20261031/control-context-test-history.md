# Control-context repair evidence

- Trial 08 stopped before acceptance: ordinary business, recording and Web
  checks passed, but activation read a 9,078,736-byte live snapshot and hit the
  unchanged 8 MiB inspection limit. This is a shared interface failure, not a
  business-rule failure. The coordinating trial agent directed the freeze;
  business answers and trial instructions are simulated, not human usability
  evidence. See `dialogue-08/artifacts/shared-control-activation-gap.md`.
- `control-context-negative-01.log` reproduces the dependency through real HTTP.
  All four model-control commands fail with an unrelated 9 MiB runtime payload.
  This payload is transport-test data, not claimed application observations.
- `control-context-retest-01.log`: all 19 existing/new control tests pass. The
  four commands use the model-only route, preserve model/build identities and
  continue to reject an oversize response. Original scope, prefix, staleness,
  recording and source-edit restrictions remain in place.
- `control-context-session-retest-01.log`: all nine capture/session regressions
  pass. The actual standard session returns the full view's same model and
  manifest even when history, instance and runtime-health assembly are forbidden
  by the test. Returned display copies do not mutate the model.
- The initial control/design browser attempts could not start Chromium in the
  Windows sandbox. Their logs remain. The unchanged tests run on the host pass in
  `control-context-browser-host/result.json` and the design browser's evidence
  directory: scoped custom views, 2D/3D, reload, replay selection, unchanged
  original facts, and pre-code declaration controls.
- `source-quality-13.json` passes for 121 Python and 90 JavaScript modules.
  Both managed examples are verified and frozen in
  `control-context-20261101-verification.json`. Complete repository run 09 passes
  from 02:55:10 to 03:03:04 local time. These shared results do not accept the
  trial project; trial 09 performs the affected application controls and normal
  business iterations.
