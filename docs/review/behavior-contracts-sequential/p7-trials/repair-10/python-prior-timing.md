# Repair09 timed diagnostic: recording remains interrupted

The single authorized timed recording retained 1,006 events and 12 runtime frames. All eight actual native journal transitions have matching commit events and frames. Recording acceptance still fails: the fixed producer prefix did not drain, four same-revision read snapshots were explicitly rejected, and two invocations remain unclosed in the original recording. No historical event or frame was filled in. Final accept has not run.

This report concerns recording `f82c4c28398f4b0ba1275fd61d0eb336`, produced on 2026-11-20. It does not retrospectively explain the earlier 79-event repair09 failure. That attempt lacked request-level traces; its exception types, individual attempt durations and response bodies remain unknown.

## Scope and identity

- Selected external provider: `../admission-candidate-skills/vibelens`.
- Actual app and observer build: `a9619082819c74adb57dff9918835beae65a9ad8dfffcdadff3629ec2da6521b`.
- Normal external plan/apply/check and strict verify passed before this diagnostic. Strict verify ran 132/132 independent assertions, 13 business tests, five HTTP tests, and both strict documentation/API checks. The seven managed adapters match the selected provider.
- Syntax and load-only validation passed before the timed launch. The actual app, observer, independent on/off/fault runs and reader used the same selected provider; no unexpected external provider origin was found.
- The provider's before/after byte snapshot contains 2,770 files, including assets/resources and excluding `__pycache__`; none changed. This count is not the maintainer's narrower maintained-source count.
- Timing hooks are project-owned diagnostic launch wrappers. Original arguments, response objects, exceptions, request bodies, headers, source checks, locks, retries, capture scope and deadlines were not replaced. No line profiler or stack dumper was used. Timing overhead was not measured.
- The host launch began at 06:18:53.645 UTC; services were ready at 06:18:59.809. The browser diagnostic completed and closed. Owned services were stopped at 06:21:59.793 UTC, releasing ports 8875/8876. No restart, new runtime operation or final accept follows this report.

## Measured transport failures

All three client failures are actual `TimeoutError` exceptions opening `POST /api/bo/events/batch`, with the original `timeout=0.5` argument. Native event IDs were retained when the SDK fell back to individual delivery. All 16, 19 and 15 corresponding fallback requests completed with HTTP 200.

| Native source sequences | Client request / server request | Client exception elapsed (ms) | Server HTTP elapsed (ms), status | Binding calls (ms) | Ingestion entry to first binding entry (ms) |
|---|---|---:|---|---|---:|
| 280–295 | 1112 / 1751 | 519.8573 | 490.4778, 200 | 459.0603 + 21.1411 | 6.2021 |
| 807–825 | 1304 / 2147 | 535.9990 | 523.9186, 200 | 487.9414 + 19.3931 | 7.5847 |
| 1217–1231 | 1410 / 2421 | 527.9674 | 548.4448, 200 | 83.8764 + 275.0890 | 186.0427 |

The first and third joins are unique socket tuple/path/request-index matches. A reused port initially left two candidates for the second request. Exact batch first/last native event IDs and the entire source-sequence list resolve it uniquely to server request 2147. This refinement is in `flush-and-boundary-analysis.json`; the earlier `timing-analysis.json` preserves the initial ambiguity.

The first failure overlaps a 672.375 ms `DataWatch.tick`; the second overlaps a 767.3162 ms tick and a 541.3657 ms view. The third overlaps view calls lasting 156.4784, 317.4678 and 488.3238 ms. These are measured temporal overlaps and elapsed regions. They do not identify a unique lock owner or establish a GIL duration. Server status 200 does not mean the timed-out client received that response.

The installed `bo_probe.py` explains the health distinction. In `bo_drain`, a batch exception triggers individual delivery of the original envelopes. The batch exception itself is not counted by `bo_transport_error` if those deliveries succeed. Also, `bo_send_one` reads an HTTP-200 snapshot response without requiring its `accepted` field to be true. Thus the observed `errors=0` is compatible with both three batch timeouts and four rejected snapshots. It establishes neither successful flush nor accepted state evidence.

## Stop command, ACK and the remaining prefix

UTC times below are from the actual timed processes on the same host.

| Boundary | Time | Evidence |
|---|---|---|
| Stop HTTP dispatch | 06:19:58.860074 | Server request 2154 |
| Flush command reply starts | 06:19:58.969475 | Server request 2155; actual command `timeout_ms=4000` |
| Client finishes reading command | 06:19:58.969982 | Client request 1308 |
| First flush ACK request starts | 06:20:02.980373 | Client request 1407; errors=0, dropped=0, completed=1216, target=1247, submitted=1263, pending=47 |
| Server receives first ACK | 06:20:02.987937 | Server request 2411; reply ends 06:20:03.003947 |
| Later scope-reset ACK starts | 06:20:03.329911 | Client request 1416; completed=1232, target=1247, submitted=1263, pending=31 |
| Stop HTTP reply ends | 06:20:03.356777 | Server request 2154; 4496.6892 ms |

The interval from command read completion to first ACK request is 4010.3914 ms. ACK request 1407 is joined by socket/path/index and server dispatch inside the actual client request lifetime, excluding port reuse outside that interval. It is not selected by nearest timestamp.

The original recording settlement remains `flushed=false, target=1247, completed=1216, submitted=1263, pending=47`. The target has 31 unfinished queue items; another 16 submissions lie after the fixed target. The later `pending=31` is a different sample: 15 target items plus 16 later items. Neither number means 31 missing recorded events.

The single transport thread's first native attempts are contiguous from source sequence 1 through 1703, with 16 snapshot barriers. De-duplicating original IDs on fallback reconstructs queue positions. Positions 1217–1247 correspond to native event source sequences 1201–1231; all 31 are events, with no snapshot in this tail. Queue positions are reconstructed from actual first-attempt FIFO, not separately instrumented enqueue/completion mutations.

| Remaining queue positions | Native source sequences | Actual transport and recording result |
|---|---|---|
| 1217–1232 | 1201–1216 | Client request 1406 began 06:20:02.967325; server request 2408 ended 06:20:03.054729; client read completed 06:20:03.054962. All 16 are present in the original recording, although sender completion was still 1216 in the earlier ACK. |
| 1233–1247 | 1217–1231 | Client request 1410 began 06:20:03.055653 and timed out at 06:20:03.583630. Server request 2421 ended at 06:20:03.622469. All 15 are absent from the original recording; their original individual fallback attempts later completed with HTTP 200. They were not appended to that recording. |

Snapshot barrier queue positions and their evidence-event source sequences are: `377/376, 387/385, 459/456, 469/465, 625/620, 635/629, 728/721, 739/731, 750/741, 759/749, 923/912, 933/921, 1077/1064, 1087/1073, 1168/1153, 1178/1162`. The JSON supplement retains all 31 full event IDs, selected node/phase metadata, the complete barrier list and timing groups.

The original closure check fails at API `GET /` enter event 1165 and `view_file` enter event 1166. The missing tail contains `view_file` return event 1217 and API return event 1227. Timing metadata for those returns does not retain their native call IDs, so node/phase alone is insufficient for an exact call-identity closure proof. The original closure failure is retained.

## Four rejected same-revision read snapshots

All IDs in the next table use the full prefix `d21d255779d7477280b77e85c79f1ffb:c36ae3aa1be1431994c37611f39d459d:`. The JSON supplement stores complete IDs without abbreviation.

| New read / prior accepted commit | Model and native instance | Revision / state | Prior event and guards | Actual snapshot server feedback |
|---|---|---|---|---|
| 721 / 629 | download-job / `bb734b188ac74b219e6e0380b0b66268` | 1 / queued | request; `{"may_request":true}` | request 2078, HTTP 200, accepted=false |
| 741 / 731 | same download-job | 2 / preparing | start; `{"may_start":true}` | request 2102, HTTP 200, accepted=false |
| 1064 / 921 | announcement / `193dbae7460b4ec6841a8895227b5e84` | 1 / published | publish; `{"may_publish":true}` | request 2341, HTTP 200, accepted=false |
| 1153 / 1073 | same announcement | 2 / published | edit; `{"may_manage_own":true}` | request 2385, HTTP 200, accepted=false |

For each pair, actual native read-point state equals the prior accepted frame state and context equals `{"allowed":true}`. Both project call sites omit configuration; the unchanged installed `BOProbe.snapshot` default is `None`. Configuration equality is therefore source-backed reconstruction, not a captured HTTP-body comparison.

The differing observed fields are:

- `evidence_id`: the prior commit event ID versus the new read event ID shown above.
- `event`: prior request/start/publish/edit versus the read call's default `None`.
- `guards`: the prior guard maps in the table versus the read call's default `None`.
- `payload`: prior `{}` versus the read call's default `None`.

Prior guard maps come from the actual independent native journal, joined by model, instance, revision and transaction ID, and the unchanged `bo_transition` call. They were not selected into `state_commit` event outputs and are not represented as captured wire bodies. Native journal sequences are 27, 28, 30 and 31.

The installed `scripts/bo_stategraph.py:292` compares the whole observed dictionary when `revision <= previous revision`, including evidence_id/event/guards/payload. The same revision and different evidence ID necessarily differ under that comparison. Its fixed failure text is `old or conflicting revision`. Original logs directly establish HTTP 200 and accepted=false; the original response body/error string was **not saved**. Attribution to that fixed message is a source-backed inference, not a captured response quotation. These are rejected snapshots, not accepted duplicates. This clarifies the earlier analysis file's imprecise duplicate-branch limitation.

The application was not changed to invent a new revision, alter its native transition, suppress the rejection or manufacture a frame. Core state equality does not by itself mean the entire supplied snapshot object meets the old provider's equality contract. The upstream handling of same-revision read evidence remains separate from this app's unchanged native state.

## Preferences HTTP 400

The actual `GET /api/preferences` request 1570 ran at 06:19:50.332317–06:19:50.334172 UTC and returned 400, before recording start at 06:19:51.789356. The original HTTP response body was **not saved**; no original error text is claimed.

The pre-run saved preferences use schema 1, project ID `python-retest-file-sharing-v1`. The current observer project ID is `python-retest-file-sharing`. Applying the same selected provider's pure `Preferences.validate` to that saved object, read-only, reproduces:

`ValueError: View preferences belong to another project or an unsupported version`

This is an offline reproduced error, not the missing original HTTP body. `service.py` routes this endpoint to the preferences reader, whose default instance uses the current project ID; the saved identity mismatch is consistent with that reader's validation failure. It is a separate persisted-view identity issue. It is not a BO ingestion route or evidence that a business authorization changed. The preferences file was not rewritten.

## Evidence, preservation and limits

- Raw data: `client.jsonl` (9,449 valid lines), `observer.jsonl` (11,099 valid lines), `launch-receipt.json`, `stop-receipt.json`.
- Original browser report/recording: `../../browser/timed09-recording-20261120T061947/`. The genuine harness exited 0 with findings and closed the browser. No 18-view loop was repeated.
- Initial analysis: `timing-analysis.json`. Refined joins, FIFO tail, exact snapshot comparisons and preferences reproduction: `flush-and-boundary-analysis.json`.
- Earlier original failures remain in `../../browser/candidate-viewer-20261120T052442/` and `../../browser/repair09-recording-20261120T055038/`.
- Both trace files contain no current collector token or known synthetic account passwords. Headers and raw request/response bodies were not logged. The evidence package excludes collector configuration, private database and credential-bearing UI harness source.
- No invalid JSON lines or unclosed selected-method starts were observed in saved traces. Forced service cleanup has no final writer-drain acknowledgement; an unwritten diagnostic queue tail remains unknown. Bounded-wrapper overhead is not a controlled performance result.
- Native data remained equal across the post-stop read-only inspection. No viewer-driven business write was inferred from delayed reception.
- The coordinating user subsequently reported upstream same-revision/read-receipt fixes with focused tests and full gates pending. This diagnostic has not installed or tested those follow-up changes. Services remain closed pending the next candidate instruction.

No timeouts, capture scope, health checks, source checks or business requirements were weakened. Final accept remains held.
