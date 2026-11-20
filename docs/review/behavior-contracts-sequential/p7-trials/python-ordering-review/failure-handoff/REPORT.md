# Repair23 first ordinary recording: execution-order analysis

The observed business result is correct for the committed order. The existing test did not establish revoke-before-admission. Capture finalization passed for this executed prefix; the full original scenario failed and remains incomplete.

Recording: `5b14eefae26b4fee923137191a16014d`. File: `c03b32f619934133ab2f82132962b0d5`. Job: `38db43d2d37946f8acbc5d84ddc7c252`. Requester: `bob`. All times below are source-observed UTC+08:00, not independent wall-clock proof; native SQL journal order supplies the committed ordering.

| Native journal | Operation/state | Application transaction | Commit event source_seq | Native DB commit observation |
|---|---|---|---|---|
| 119 | request: not_requested -> queued | `ebad64130ecf4028ab4457a6c6b7cdc3` | 1123 | 2026-11-20T20:50:27.172726+00:00 |
| 120 | start: queued -> preparing | `d3070086f6af4fdcbc619a461f9ce458` | 1323 | 2026-11-20T20:50:27.386652+00:00 |
| 121 | complete: preparing -> ready | `df283ca93929429aa12cf3342d99cb35` | 1345 | 2026-11-20T20:50:27.411160+00:00 |
| 122 | revoke: active -> inactive | `b86b483df57d4390936f785464fe0c78` | 1376 | 2026-11-20T20:50:27.449766+00:00 |

Worker entry is source_seq `1287`. It reads the matching grant in DB transaction `e94dae1e1ea14d50bb0eee04bc4dd8bd`. The grant SELECT return is source_seq 1295; actual policy facts 1300-1309 share business read basis `d3070086f6af4fdcbc619a461f9ce458` and DB scope parent 1288: actor/recipient Bob, owner Alice, is_owner false, grant_active true, grant_fresh true, preparation_access true. Admission entry 1310 names this job; state-before 1313 is queued/revision 1 with current allowed=true and stored context=true; native completion 1316 and DB commit 1322 lead to the independently persisted start journal 120. Complete DB commit 1344 precedes revoke service entry 1348; revoke DB commit is 1375. See `sql-policy-and-transaction-original-event-extracts.json` and `verified-commit-order.json` for full original event IDs, transaction IDs and native journal rows.

The native backup has this job ready/revision 3/admitted=1, requested against grant revision 1. The grant is inactive/revision 2 only after revoke journal 122. Store uses BEGIN IMMEDIATE and commits the row change and journal atomically (`app/storage.py:55`). Admission re-reads File and Grant for job.requester_id in that transaction (`app/service.py:294`). No permission denial preceded this admission.

The unchanged harness reads a queued SQL snapshot, then locates and clicks the owner revoke control, then expects rejection (`review/repair23-original-recording-once.py:127`). There is no synchronization preventing the default 1-second worker from admitting between the read and the click. The first queued check passed, but its ordering assumption did not. This run timed out at the original 20000 ms expectation after four checks; the rest of the twenty checks did not run. No application or expected-result change is justified by this observation.

Captured driver SELECT statements identify tables/conditions and transaction scope, but parameters are empty and returned rows are not captured (rows_known=false). Exact object identity/value is established by source-bound ORM selection, same-scope policy facts, native SQL backup/journal and state/transaction joins together; it is not claimed from the SQL trace alone.

Mapping/recording: 1580 actual events, six native commits plus six versioned reads, all twelve exact identity/state/context/build frames matched to the frozen native SQL/journal. The producer prefix is continuous and canonical invocation closure passes. No gaps or ownership gaps. Ordinary browser cleanup Stop returned HTTP 200 and fully drained target/completed/submitted 1760 with pending 0, errors 0, dropped 0 and retries 0. This is capture finalization evidence for the actual prefix only; it does not pass the full ordinary scenario or substitute for the previous full-load failure.

Earlier passed checks: all five native gate reports, 162/162 business assertions, 21 business tests, six HTTP tests, the missing-completion negative, eight native concurrency trials, original controlled browser 12 checks, cancellation controlled browser 38 checks at 390/768/1440. Their immutable receipts remain in this phase. No full post-verify ran after the recording failure. No retry, application edit, deadline/capacity change, original-record backfill or accept occurred. Both ordinary services remain idle for evidence diagnosis; independent main UI has not begun.
