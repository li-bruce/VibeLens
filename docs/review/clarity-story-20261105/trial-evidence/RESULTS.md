# Public v0.12.1 patch and first implementation results

The confirmed business scope is unchanged. C04 confirms one declaration-driven `file_review` machine; session and sharing are independently identified native objects with actual observation. Requirement dialogue is user-authorized anthropomorphic simulation. Browser evidence below is actual agent-driven interaction, not independent human testing.

Application: <http://127.0.0.1:8897/>. Graph: <http://127.0.0.1:8898/graph>.

Build ID: `81adf90426f8377a755ae057109e35911cda01c416eb89c6cb04d6167e5b09b9`.

Stopped browser recording ID: `19e46d43c79a49cf8e8805fc51751872`.

Current-index supplemental real HTTP recording ID: `b476da792d4d4026a501500eda6a8472` (381 events, 6 state frames). It is stopped, has the same build ID, and its captured/current API-index revisions match. It independently repeats the two missing pre-review frame gaps. Start was idempotent and stop drained target/completed/submitted 1480 with pending 0. See `current-recording-summary.json` and `current-recording-receipts.json`.

**This recording is stopped and drained, but is not gap-free:** 1,073 actual events, 10 state frames, and two missing frames for pre-review reads. No event loss or producer error was reported. Do not replace this statement with a full recording-acceptance claim.

## Results by layer

| Check | Actual result | Evidence |
| --- | --- | --- |
| v0.12.0 freeze | Passed; 980 archived files and per-file readback verification | `v0.12.0-before-v0.12.1/manifest.json` |
| Original install integrity | Passed; all 349 files unchanged | `delivery-integrity.json` |
| Public patch SHA-256 | Passed; exact user-specified digest | `v0.12.1-download.json` |
| Patch installation integrity | Passed; all 351 extracted files unchanged | `v0.12.1-installation.json`, `delivery-integrity.json` |
| Managed upgrade | Passed; 23 changes, zero conflicts, zero changes in the post-apply plan | `v0.12.1-plan.json`, `v0.12.1-apply.json`, `v0.12.1-post-plan.json` |
| Confirmation and native concept binding | Passed for confirmed one-machine scope | `verify-delivery.json`, concepts report |
| Earlier three-machine capability rejection | Still rejected by unchanged v0.12.1 checker; retained as a negative capability result | `multiple-state-retest.json` |
| Business assertions | Passed, 93/93 configured assertions over on/off/fault modes; 14 business scenarios in each mode | `observations.json`, `runtime-assessment.json` |
| Independent native instance and field mapping | Passed | `runtime-assessment.json` |
| Source-bound implementation and required values | Passed in the independent canonical runtime assessor | `runtime-assessment.json` |
| Policy evaluations and concept runtime associations | Passed | `runtime-assessment.json` |
| Invocation closure and actual HTTP telemetry | Passed | `runtime-assessment.json` |
| Normal observation health | Passed; 755 events, 16 submitted snapshots, zero errors and drops | `observations.json` |
| Observer unavailable | Native business passed with capture off and with 771 deliberately failed transports | `observations.json` |
| Queue pressure | Native business passed; actual capacity-one queue reported 683 dropped envelopes, pending zero; loss is not an observation pass | `queue-limited.json` |
| Strict documentation and API registration | Passed; both commands are in the project verification entrypoint | `docs-final.json`, `api-final.json`, `sync.json` |
| Database structure and runtime mapping | Passed within SQLite/SQLAlchemy collector coverage | `database-final.json`, `runtime-assessment.json` |
| Actual schema mutation negative | Detected a renamed column in a separate disposable SQLite database | `schema-change-negative.json` |
| Missing transition, missing instance, wrong revision negatives | All detected in isolated payload copies | `runtime-assessment.json`, negative_checks |
| Unsynchronized source negative | Current -> stale detected in an isolated source copy | `source-freshness-negative.json` |
| Static architecture and managed file integrity | Passed; canonical dynamic core resolver remains an explicitly documented static-analysis limit | `architecture-final.json`, `ownership.json` |
| Export without observer and viewer | Passed actual HTTP login/upload/denied-share/approve/share/download/revoke/old-link-denial | `core-package.json`, `core-http.json` |
| Actual browser business flow | Passed upload, review, sharing, message, byte-identical download, revocation and old-link rejection | `../browser/implementation-01/browser-v0121-steps.json` |
| Browser negative cases | Passed unapproved share, self approve, self reject, unrelated account download, revoked recipient download | `browser-audit.json` and browser screenshots |
| Rejected-file history | Passed; reupload is a distinct ID, prior rejection and record retained | `browser-audit.json` |
| User-requested observation distinctions | Passed 13 independent browser-recording checks, including both review transaction chains | `browser-audit.json` |
| Viewer/recording controls and replay | No business events or database writes during the audited control interval; original recorded source retained | `browser-audit.json` |
| Formal verify / accept / check | **Failed** at the immutable coverage baseline gate; downstream runtime/project sections are not run by that formal command | `verify-delivery.json`, `accept-delivery.json`, `check-delivery.json` |
| Complete recording frames | **Failed** for two actual pre-review reads; producer flush itself passed | `browser-recording.json`, `browser-audit.json` |
| Old-recording catalog vs viewer version | **Failed consistency check**: after source inventory changed the API-index revision, the old record remained listed but viewer reopening was rejected | `replay-version-diagnostic.json` |

Independent assessors were invoked unchanged. They are diagnostic results and do not override formal change acceptance. A later availability GET emitted two legitimate `api:health` events after the audited replay interval; it is outside the stopped recording and is not a viewer-control event.

## Formal acceptance failure

The first implementation baseline incorrectly used `policy: redacted` for the `password` argument's derived output `authenticated`. Current implementation captures only a Boolean and truthfully declares `policy: derived`. The canonical protected-coverage check rejects replacement of the old parameter record as `weakened_feature_coverage`. The baseline's feature did not contain the requirement linkage needed by the supported requirement-change exception.

The original baseline bytes, confirmed discovery, lock and independent acceptance expectations still match the frozen v0.12.0 archive. No validator was patched, baseline reset, fake confirmation inserted, or obsolete redaction claim restored to turn the result green. The `accept` / `check` diagnostics include follow-on failed/stale verification messages because formal verification stopped at this gate.

## Recording frame failure

The two missing event IDs end in `:166` and `:925` within run `adb758d4d57f4d0f84bad70ca19c7b2e`, producer `e4c7facb960442d1b7e1d86a40adc8d8`. They are actual `transition/read` observations before approving file `83c895a75de944f2b270ddf97e309d1e` and rejecting file `c69acabc2fff4af9b6598644a73d3c41`, both at native revision 1.

The unchanged `observer_runtime/bo_observer/observation/session.py` calls `graph.bo_observe`; when the same revision is accepted as a duplicate it skips creating a frame for the new evidence ID. Recording finalization correctly exposes the missing frames. The values and transactions are present, but the missing historical state must remain unknown. The producer settlement was flushed with target/completed/submitted all 1089 and pending 0. Nothing was filtered, rewritten, or backfilled to hide this failure.

## Viewer patch retests

- The isolated source-free graph at port 8896 rendered actual nodes after upgrade; its browser error log was empty. The model still omits `presentation`, so the old absence-only reproduction must not be interpreted as a new browser failure: the viewer now handles that design response.
- Each approve/reject effect pair changed from two displayed edges to one, retaining both original assertion IDs in `equivalent_relations`. See `delivery-integrity.json`.
- Actual 2D/3D switching, Fit, message and revocation values, Timeline, play/pause and recorded-source opening were exercised. Screenshots and AX records are under `review/browser/implementation-01/`.
- Readability remains limited when the Timeline occupies much of the viewport: the graph and source panel are small, and labels are abbreviated. A Fit screenshot is evidence for that viewport, not a general layout or performance proof. One historical draft title still says it awaits confirmation; C04 is the authoritative confirmation record.
- Exhaustive drag/pin/custom-filter combinations, forced save failure, abnormal process exit recovery and every old-recording migration combination were not independently accepted in this trial.

The earlier browser recording was successfully played and inspected before final source inventory changed its API-index revision. The backend catalog identifies recordings by build/model hash, while the browser also compares API/concept structure revisions. This explains the stale listed entry and does not make the old recording a current-index replay. Its exact source and raw JSON are preserved. The supplemental real HTTP recording was taken only after authored files and the source index were settled; no framework check was bypassed.

## Reproducible commands and preserved first version

Use the root README for launch and check commands. `tooling/audit_browser_recording.py` reproduces comparisons against the local native database and saved recording. `tooling/assess_runtime.py` runs the original runtime assessors on saved real on/off/fault runs. Original failures and retests are retained under `review/implementation-01/`, `review/round-03/`, and the frozen pre-upgrade archive. The public patch files remain under a separate vendor directory.

The v0.12.0 archive SHA-256 is `71933ad645784896723cabeefe3445f42077e5f21f65e591d7fff38ef4f7cd28`. The public v0.12.1 package SHA-256 is `8f2304403c91a6b6934ac9c168f06350c9115cf29b616a443f6d836bb38ea80e`.
