# Shared runtime control-context HTTP dispatch gap

## Observed failure

Normal upgrade changed exactly three managed runtime files and subsequent upgrade plan reports no changes or conflicts. The running project uses the new build `9c1d97e05955481ca1c1a46b1955bb9513a50893d6ecbe40fd1f79eb1b02af60` with current bindings.

`GET http://127.0.0.1:8983/api/vibelens/control/context` returns HTTP 404 with `{"error": "not found"}`. Installed `bo_control activate`, invoked with the exact current user message and actual host conversation ID, fails with `HTTP Error 404: Not Found`. No activation graph URL or applied receipt exists.

The real live view contains 10,000 retained events and is 12,363,566 bytes. This is genuine HTTP business activity with zero producer/adapter errors and drops. The fixed CLI budget remains 8,388,608 bytes. No raw event reset, budget increase, snapshot fallback or local managed-file patch was used.

## Cause and source parity

`observer_runtime/bo_observer/web/bo_web.py` recognizes `/api/vibelens/control/context`, and `GraphSession.control_context` provides the model-only query. However, `observer_runtime/bo_observer/service.py` delegates only the exact path `/api/vibelens/control` to `session.web.get`. The new `/context` path falls through to the static-resource 404. Installed service/CLI/session/Web files match the maintained source byte for byte; see `context-failure.json` for SHA256 receipts.

## Minimal reproduction

With the normal project launcher running:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 review/retest-20261101-03/context_failure.py
.\.venv\Scripts\python.exe -B -X utf8 review/retest-20261101-03/control_run.py activate
```

The first command asserts and records the actual 404; the second intentionally exits 1. `control_run.py` reads the preserved current message, and the installed CLI obtains the actual `CODEX_THREAD_ID`. Do not substitute another conversation ID to replay the activation claim.

## Evidence and boundary

- `context-failure.json`: repeated actual 404 responses, large-view size, zero observer-generated events, healthy settled producer and canonical parity.
- `control-activate.stdout.log`, `control-activate-invocation.json`: actual CLI failure and host/message identity.
- `browser-blocker.json`, `runtime-page-at-blocker.png`, `control-context-404.png`: loaded runtime page/current build plus real browser HTTP failure. This is read-only; no scoped view was applied.
- `verify-current.result.json`: current mapping/state_rules/business/project_checks passed. These gates do not cover this HTTP control dispatch path.
- `recording-evidence.json`: actual explicitly stopped recording `30b61daa723941319ce7655e764a3107`, 153 interval events, closed native calls and independent SQLite/parameter/state checks. Prior context retains its original 2,000-event truncation and ancestor gaps; the entire recording is not gap-free.

Repair the maintained runtime dispatch and add an end-to-end regression using the standard `make_server` HTTP listener. Then upgrade this project normally and rerun activation/inspect/plan/apply/scoped visibility and exact stopped-recording filtering. Do not replace baselines, install a custom route in the demo, use an offline snapshot to bypass activation or count a queued/unrun control as applied. No accept was executed.
