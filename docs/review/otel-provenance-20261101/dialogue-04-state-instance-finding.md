# State-instance replay finding

Visual review of `dialogue-04-browser-v2-final-01/05-recorded-2d.png` and
`06-recorded-3d.png` found a false final caption: `revoked_share → approved`.
The native file remained approved and the independent share remained revoked.
Actual recipient downloads returned 403 and administrator downloads retained their
independent authority. Business behavior passed; the observer summary did not.

The snapshot protocol already carried each native `instance_id`. The session's
viewer projection dropped it and replay compared configurations by caller
`attempt`. All four native instances used the caller label `application`.
The final comparison therefore paired unrelated instances.

The shared observer now projects `snapshot_instance` (run-qualified identity) and
`native_instance_id`, separately from caller entity/attempt. Native configuration
objects and state engines remain unchanged. Replay retains the last witnessed
configuration of each instance across partial frames and compares only matching
identities. Duplicate legacy attempt IDs are treated as ambiguous. A legacy frame
can use its event's explicit snapshot identity if present; missing identity is not
reconstructed from order, labels, time or the final state.

Regression: `tests/test_snapshot_identity.py` checks live view, event-bound frames,
saved recording, caller identity and native-input preservation. The first test
incorrectly expected snapshot metadata on an already-delivered immutable event;
the assertion was corrected to join the actual frame with event run ID and native
instance ID. `tools/test_runtime_instances.mjs` covers interleaved partial frames,
legacy ambiguity and the unchanged 4,564-event recording. It must produce no
invented final transition. The original mechanical browser result is retained,
but it is not counted as complete semantic acceptance.

Managed runtime/viewer upgrades, project revalidation and another independent
browser capture are required before closing this finding.

Closed by the managed `instance-frame-identity` upgrade and 16-case/48-run project
acceptance. The unchanged final 6,608-event recording presents seven expected
same-instance transitions, four distinct final instances and zero invented End
changes; see `dialogue-04-browser-v2-replay-final-05/result.json`. A test-only raw
event/timeline-item adapter error was corrected and retained separately. Original
engines, domain sources and previous acceptance inputs remain unchanged.
