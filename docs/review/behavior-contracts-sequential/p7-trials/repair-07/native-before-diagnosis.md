# Node observe transport diagnosis — 20 November 2026

**Both compared recordings remain interrupted. This is fault comparison, not final acceptance.**
The application build stays `58c9af03b415b0cf60b7ccf696c633741498e844be4409a74069513a82aa730c`. Business, UI and project observation source bytes match the sealed old-provider files. Canonical plan/apply/check for the candidate returned valid with zero managed dependency changes; all eight JavaScript adapter files also match byte for byte. No installed package, validator, projector, timeout, required capture or failed recording was edited.

## Preserved failures and process ownership

The original transport-failed recording is `9893c26c801f4c4387668768827f6e04`; its native health retained `TimeoutError` and its status remains interrupted. It did not retain a per-request audit, so its exact original failed request cannot be reconstructed retrospectively.
The later `ERR_CONNECTION_REFUSED` in `browser-acceptance-command.log` was a separate startup/readiness failure. It must not be used to explain the original in-recording timeout.
Every compared case was subsequently owned by `tooling/unified_browser_run.py`: the same parent starts viewer, app and browser/trial processes, waits for actual HTTP readiness, runs the case and cleans up only its child process trees. Completed cases show all services still alive immediately before intentional cleanup. A cleanup exit code from taskkill is labeled separately from a service exiting before cleanup.

## Workload, defaults and load limits

The compared real UI sequence is login, create one preparation task, display its ready link, return to files, refresh once, wait up to 30 seconds for the native queue to settle, then click the real viewer Stop control. The graph stays open. App/viewer/browser share one owning process tree. There are no fabricated business events.
`BOProbe` keeps its default 1000 ms HTTP attempt deadline and two attempts per queued item. Capture-control RPC keeps its own unchanged 2000 ms deadline. Queue submission/completion, failed attempts and stop settlement are distinct measurements.
The raw load_context string was based on an earlier coordination message and is inaccurate for these runs. Separate `load-context-correction.json` files preserve the later clarification that repair06 regression was concurrent. Host samples and local monitoring are not an isolated benchmark. At least one candidate host-CPU sample exceeds 100%; those samples are invalid and are not used to prove load or a product defect. No raw sample is clamped or rewritten.
The file inventories differ by one real newly seeded fixture, and task/session counts also increase through actual operations. This is the same action sequence, not an identical-data latency benchmark.

## Results: backlog versus failed HTTP attempts

| Cohort / run | Files/tasks/sessions before UI | Failed native HTTP attempts | Native errors after stop | Native pending after stop | Stop target/completed/pending | Status |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Old frozen provider / 1795146229 | 10/11/31 | 2 | 0 | 135 | 586/448/138 | interrupted |
| View-lock candidate / 1795146438 | 11/12/33 | 5 | 2 | 153 | 636/479/157 | interrupted |

A failed first HTTP attempt may recover on retry and therefore does not necessarily increment BOProbe.errors. Both failed attempts for the same observation increment the item-level transport error once. `queue_completed` also advances after a failed item; zero pending would not by itself prove success. Recording-boundary aggregate health and the subsequent native health query are retained separately because the queue continues moving.

## Actual timed-out requests

| Cohort | Observation node / phase / producer seq | Attempt elapsed ms | Endpoint | Request audit ID |
| --- | --- | ---: | --- | --- |
| Old frozen provider | `api_login` / `enter` / 34 | 1002.40 | `http://127.0.0.1:8926/api/bo/events` | `bfc650ee-4307-4b00-8e7e-e637d803e4d2` |
| Old frozen provider | `data_read` / `enter` / 236 | 1001.41 | `http://127.0.0.1:8926/api/bo/events` | `be5cc376-d010-4d41-a31e-3c6567d6bc81` |
| View-lock candidate | `api_request` / `return` / 244 | 1004.69 | `http://127.0.0.1:8926/api/bo/events` | `8684822b-e604-4f4b-b91b-b3a7541033f0` |
| View-lock candidate | `api_request` / `return` / 244 | 1013.84 | `http://127.0.0.1:8926/api/bo/events` | `938b2988-88e3-4f8e-8fc3-8df1246770ae` |
| View-lock candidate | `data_read` / `return` / 440 | 1004.90 | `http://127.0.0.1:8926/api/bo/events` | `0807fd69-9e16-4625-b070-6633e813fcbc` |
| View-lock candidate | `data_read` / `return` / 460 | 1001.76 | `http://127.0.0.1:8926/api/bo/events` | `fbd76eca-fa4c-470b-8a2f-8d40b530bcf6` |
| View-lock candidate | `data_read` / `return` / 460 | 1007.26 | `http://127.0.0.1:8926/api/bo/events` | `3f0f1f21-e14d-4570-89a8-bd1ab24ad01e` |

The earlier unprofiled single-parent run `unified-1795145145` separately recorded three timed-out attempts: `list_tasks/return/227` once, and `policy:is_owner/decision/428` twice. Its raw request audit and interrupted recording `a616123956f741a3a994c98f682e1f09` are preserved. The initially reported zero failures was an intermediate read; the complete log established all three.

## Measured calls and lock boundaries

Times below come from completed calls in process-local Python 3.13 monitoring. Canonical functions are executed unchanged. They are diagnostic wall times with monitoring and concurrent load, not isolated speed claims.

| Function | Old calls / median / max ms | Candidate calls / median / max ms |
| --- | --- | --- |
| `GraphSession.event` | 471 / 40.66 / 1593.68 | 493 / 36.69 / 1561.02 |
| `GraphSession.snapshot` | 8 / 36.33 / 74.34 | 8 / 36.74 / 66.46 |
| `GraphSession.binding` | 539 / 38.02 / 1931.35 | 560 / 34.62 / 1404.69 |
| `CodeGraph.refresh` | 5 / 5870.24 / 10117.40 | 5 / 5604.63 / 6989.62 |
| `overlay_model` | 36 / 85.90 / 458.86 | 34 / 81.36 / 457.01 |
| `read_names` | 36 / 49.97 / 338.46 | 34 / 46.66 / 395.86 |
| `BehaviorContext.view` | 5 / 3.01 / 4.17 | 5 / 8.08 / 45.66 |
| `BehaviorContext.last_verification` | 5 / 1.62 / 2.45 | 5 / 3.38 / 8.27 |

**Old frozen provider:** longest captured event lock wait 876.84 ms; longest captured event lock hold 1592.91 ms.

**View-lock candidate:** longest captured event lock wait 1089.36 ms; longest captured event lock hold 1521.04 ms.

The candidate still has long `GraphSession.binding` and event critical sections. In its seq 244 and seq 460 timeout windows, the trace contains event critical sections of about 1521 ms and 1261 ms respectively, with overlapping binding calls of about 1405 ms and 1174 ms. These are temporal overlaps, not a fabricated one-to-one request attribution.
The completed server trace did not capture payload event IDs correctly (`observation_id` is null). It has thread/frame/path/time boundaries, while the native audit has exact event/request IDs. Therefore `temporal_event_calls` and `overlapping_lock_holds` in transport-analysis.json are explicitly candidate overlaps; they do not uniquely identify the server frame for each failed request. The external monitor has since been corrected to read event/snapshot arguments directly for a future targeted run, but it has not been rerun blindly and does not backfill old logs.
The main repair conversation independently reported a deterministic delayed-reader/session-lock reproduction. That establishes a general concurrency defect, but is not substituted for the original recording’s missing per-request identity.

## Source scanning: invocation count and trigger


**Old frozen provider / 1795146229:**
- `CodeGraph.refresh`: 1 completed calls attributed to `/api/recordings/start`.
- `CodeGraph.refresh`: 4 completed calls attributed to `/api/view`.
- `scan`: 14 completed calls attributed to `/api/recordings/start`.
- `scan`: 58 completed calls attributed to `/api/view`.
- `scan`: 1 completed calls attributed to `startup/background (no HTTP ancestor captured)`.

**View-lock candidate / 1795146438:**
- `CodeGraph.refresh`: 1 completed calls attributed to `/api/recordings/start`.
- `CodeGraph.refresh`: 4 completed calls attributed to `/api/view`.
- `scan`: 14 completed calls attributed to `/api/recordings/start`.
- `scan`: 59 completed calls attributed to `/api/view`.
- `scan`: 1 completed calls attributed to `startup/background (no HTTP ancestor captured)`.

`scan` is the selected `sources.scan` callable (its concrete source file is retained in each trace row). A scan invocation is not proof that every unchanged file was reparsed. The observed HTTP triggers are live `/api/view` projection and the recording start’s initial static context; source-tree timing is not conflated with a session-lock hold. Recording checkpoints have their own no-HTTP-ancestor view calls.

## Reproduction and evidence files

From this app directory, with all four intended trial ports free, the diagnostic command is:

```powershell
$env:BO_DIAGNOSTIC_SKILL = '<selected external frozen provider>'
& '<supplied Python>' -B tooling/unified_browser_run.py --transport-repro --profile-viewer
```

Do not rerun the same workload blindly while repair regression is competing for resources. Each run folder contains lifecycle/readiness/cleanup records, an exact copy and hashes of diagnostic source, native-fetch.jsonl, browser-network.jsonl, viewer-calls.jsonl, raw recording.json, transport-result.json, transport-analysis.json and screenshots. Tokens, passwords and arbitrary request bodies are excluded from the request audit.

Old evidence seals:
- `old-provider-transport-20261120.zip`, SHA256 `5483150f3167a02c4e754c1ac7c2e441ab60f4ae1a10a67e95bb7ffded003570`.
- `old-provider-local-monitor-1795146229.zip`, SHA256 `8595d82ed45f5f29bc152cc07a6aa52fd0774ced415364cae437a3f3ecd25f2c`.

Earlier failed diagnostic setup is separate: `unified-1795145021` failed before app readiness due to the audit loader’s Windows path form; `unified-1795145365` did not enter the recorded case before its UI-ready wait ended; `unified-1795145807` held a read-only sqlite3 connection open and caused the login persistence operation to fail. The diagnostic connection is now explicitly closed before browser operations. None of these are presented as framework transport reproductions or app business regressions.

## Independent native/business boundary

The original HTTP/SQLite/disk business suite passed 13 tests. The single-parent native UI run `unified-1795144920` passed on/off/fault preparation and identical file hashes, real upload/named sharing, recipient restrictions, revocation hiding files while preserving repeated collection, editor file independence, and board publish/edit/read/delete. Its recording_validation is explicitly not_run. These successes do not override failed recording, mapping or final acceptance gates.

Final recording/mapping acceptance remains pending. No `change_sync accept` has been issued on the strength of this candidate comparison.
