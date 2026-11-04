# Implementation follow-up before browser acceptance

The four findings from the [preliminary audit](preliminary-implementation-audit.md)
have source corrections and corresponding real request evidence in the trial's
`review/implementation-01/observations-corrected.json`. This remains an
**in-progress, pre-browser review**, not final acceptance of the trial.

The independent reviewer read saved artifacts and source, then applied the
installed pure evidence validators. No application was executed, no request was
sent, no browser was operated, and no pending approval action was resumed.
[Evidence identities and results](implementation-followup-evidence.json) record
the exact SHA-256 values, build ID, original event IDs and request checks. The
[read-only checker](implementation-followup-readonly.py) reproduces this review.

The [checkpoint archive](implementation-checkpoint-02.zip) preserves the original
event/check JSON, the earlier failed verification, and 40 allowlisted project
source, declaration, test and provenance files. Its [path and SHA-256 inventory](implementation-checkpoint-02.inventory.json)
allows review without relying on the trial's changing working tree. The ZIP
SHA-256 is `9a4c858f33b2ac248f567a92b2a9fca33c93dcfcf46608353e4f352108f9a4a7`.
All original bytes are retained. Managed runtime/viewer code, vendor files,
virtual environments, business databases and uploaded contents are excluded.
The recorded accounts and runtime identities are synthetic trial data.

Extract this archive and the [public v0.12.0 release](https://github.com/li-bruce/VibeLens/releases/tag/v0.12.0)
separately. The release dependency's SHA-256 is
`9955b650113c41e79c2039dc78ae52d2690f318de87b341bb9af9009869035da`.
The following command only checks the retained observations; it does not run the
application or browser:

```text
python -B implementation-followup-readonly.py <checkpoint>/project --runtime <release>/vibelens/scripts
```

This checkpoint is review material from work in progress, not an accepted
application bundle. The prior failing verification retains its original stage;
it is not presented as a result for the corrected source.
The [portable read-only validation](implementation-checkpoint-02.validation.json)
used extracted copies of the checkpoint and public release. It reproduced every
audit result except the expected review-time and local-path differences, and
verified all 40 retained file hashes without reading the live trial project.

## Four findings revisited

Source locations below are relative to the trial project and refer to the hashes
in the evidence file, not a future version of its working files.

| Finding | Correction and actual evidence | Result within tested scope |
|---|---|---|
| A stylesheet was attributed to a framework-error handler | `bo_integration.py:166` excludes Flask's static endpoint. `tests/scenarios.py:118` records the actual stylesheet HTTP 200 and an empty event window. The real `/missing-route` request still has one `api:framework_error` entry/return pair, with HTTP 404 and the same request/call identity. | The tested successful static request is excluded and the tested framework error remains observed. This does not establish the correct attribution of every possible future custom fallback. |
| Review-effect completion had no invocation | `service.py:246` begins the effect before inserting the review record; line 250 completes it only after leaving the native transaction. `FileService.transaction` commits SQLite before emitting its commit at line 66. All three review records have `effect enter → transaction commit → effect commit`, matching review ID/call ID, file identity, request attempt and transaction ID. The test also compares actual SQLite review rows at `tests/scenarios.py:183`. | The missing invocation is fixed for the observed approval/rejection paths. Pure conceptual ownership/completion and invocation-closure checks now return no errors. The earlier failure remains retained. |
| An ordinary denial could stand for revoked-link denial | `service.py:321–326` emits `deny_old_link` only inside the actual download denial branch when the current actor is the stored recipient and the grant is inactive. The event carries the real file/grant/actor/recipient and reason. The saved request windows contain no such event for unapproved sharing, either self-review denial or another account's download denial; the revoked recipient request has the matching event and HTTP 403. | Conditional meaning is represented by actual branch observations. No fictitious denial function or elapsed span was introduced. |
| An uploader's empty dashboard could count as a received message | `service.py:354–365` observes each actual persisted message returned for the current authenticated account. The uploader's empty dashboard has no `notify` event; the recipient's inbox request has one event with the actual message, file, grant and matching actor/recipient IDs. | The business result is tied to the specific received message, rather than every dashboard invocation. |

The eight request-local positive/negative witnesses and three effect-order
witnesses were independently checked against the original event objects, not
only their claimed `observed_nodes` lists. Source review confirms that the request
windows are drained before and after each sequential request
(`tests/scenarios.py:89–103`). These windows are suitable for this sequence; they
are not a concurrent-request isolation test.

## Evidence and remaining boundary

- The corrected build ID matches its manifest, and every source file listed in
  that manifest still matches its recorded hash at review time.
- The on-run contains **755 distinct events**, three effect entries, three effect
  completions, one received-message fact and two revoked-link denial facts.
  Producer, integration and database error counts are zero; pending and dropped
  counts are zero.
- The unchanged installed conceptual runtime validator returns no errors.
  Invocation closure is valid. Its `closed_calls: 558` includes the effect case
  referencing the same full-workflow events; it is not 558 independent calls or
  separate executions.
- The saved on/off/fault runs each report the same 14 expected business outcomes.
  Each records 23 native-fact comparisons with independent SQLite reads. The
  injected fault run reports transport errors and no collected events while
  retaining the business results, as intended for the failure-isolation test.
- The saved corrected API, source-documentation and database checks pass within
  their declared scopes. The database report explicitly excludes triggers and
  stored routines from its coverage.

The newest full verification artifact visible at this review is still
`verify-initial.json`, produced **before** these corrections and marked failed.
No corrected full verify/accept or completed browser evidence is present in this
stage. Their absence is pending work, not a claim that the four corrections
failed. UI presentation, recording controls, graph/timeline rendering, a further
code iteration and final acceptance still need their own evidence.

These corrections preserve the existing native state/permission authority. The
earlier failures were detected or exposed by the existing checks plus focused
semantic counterexamples. This review does not change the frozen framework or
weaken a gate, and does not infer general semantic completeness from source
bindings or a successful HTTP response alone.
