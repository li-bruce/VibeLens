# Repair 19 — Recorded facts and native verification

P7 remains in progress. This repair follows `93ff0dd2`; it does not accept either
trial or authorize a public release.

## Failure

The Node repair18 full browser path completed two recordings (1,264 and 5,196
events), both normally stopped without gaps. The subsequent complete verification
failed with 1,358 diagnostics. The original command and failure breakdown are in
`first-failure/`. Hashes identify the private original archive and full report;
those original files remain unchanged in the trial workspace.

- 1,264 event errors: the trial inserted stored recording events directly into a
  strict native-wire validator. Stored `source_seq` and `stream_id` are collector
  metadata, not allowed wire fields.
- Six missing snapshots: recording frames retained a display projection but not
  the original admitted snapshot envelope needed by the independent reducer.
- One missing tracing backend: remote aggregate health omitted the producer's
  actual SDK backend report.
- 83 policy-identity errors: the live project bootstrap read a stale review hash,
  while native tests derived the current declaration hash.
- Four downstream failures: the project sensitivity check and dependent evidence
  checks could not pass the incomplete input.

Native business results and healthy recording transport do not establish complete
mapping acceptance. No failed event, declaration hash or snapshot was relabeled.

## Repair

`session.py` retains the original validated snapshot with its own receipt sequence
inside the existing bounded frame store. `runtime_frames.py` preserves and checks
this evidence alongside the display projection. Existing retention and payload
limits remain unchanged.

`recording_evidence.py` and `bo_trace.py evidence` explicitly restore native event
envelopes and snapshot receipt order. Unknown fields, bad identities, incomplete
settlement and duplicate receipts remain errors. Legacy frames cannot manufacture
missing snapshots. Export does not supply policy reports, native outcomes, or an
acceptance decision.

`CaptureBridge` retains allowlisted tracing metadata per producer. The telemetry
gate requires each participating span producer's own backend evidence. An
aggregate report from another producer cannot satisfy it.

`bo_policy.py fingerprint` resolves the current project declaration through the
same loader as validation. Skill guidance requires current policy identity for
both live and test startup, and a complete gate after browser evidence assembly.
The Node bootstrap still requires its ordinary project-side integration update;
changing the original cached hash or historical events is not a fix.

## Failure and retest history

- The first baseline harness unintentionally imported current modules through a
  shared fixture. Its two passing results are retained in `baseline.json` and do
  not prove old-package behavior. The corrected harness asserted the frozen
  installed provider path; both real collector counterexamples failed there.
- The maintained collector passed 85 targeted tests.
- The expanded test first failed because its Unicode CLI subprocess omitted
  Python's UTF-8 flag. The exact failure is retained; the corrected invocation
  passed all 38 tests, including the original policy cases.
- The first source check found formatter-width differences (88 vs the repository's
  100 columns). Formatting was corrected; the second complete source check passed.
- The first full run rejected stale generated runtime copies. After normal
  regeneration, the next run rejected the still-unreviewed example ownership
  seal. Both failures are retained. The ordinary example review/seal and
  verify/accept/check sequence must complete before the final full rerun.
- The first isolated npm install lacked a cached TypeScript archive. The same
  locked offline install succeeded using the existing host cache. No dependency
  version was changed.
- Full regression, clean installation/export and native trial retests are recorded
  below when completed. P7 remains open until the complete trial sequence passes.

## Completed repair gates

Full regression: 1293 reported tests in 116 unittest reports; 1 existing skip(s). Both managed examples passed review, verify, accept and check. The clean staged export passed without regeneration or reapproval. The fresh final installation has 463 matching owned files and passed the collector/export counterexamples. See `results.json`. These repair results do not close P7.
