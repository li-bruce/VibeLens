# Shared control activation failure

## Actual reproduction
The current real `/api/view` returns HTTP 200, current source binding, 7597 retained events and 9,078,736 response bytes. Canonical `bo_control.py activate` fails with `Observer response exceeds the inspection budget`. Installed control CLI bytes match the maintained canonical CLI (SHA256 `9bfe2b5dfbea4d0e7c29b5db2dae69f1966b472336c880935d233aea96b03c75`).

```powershell
$projectPath = 'C:/Users/Lvi_P/Documents/Work/CF/平台软著/VibeLensTrials/execution-bands-dialogue-20261031-03'
& "$projectPath/.venv/Scripts/python.exe" -B -X utf8 "$projectPath/observer_runtime/bo_control.py" activate --root $projectPath --url http://127.0.0.1:8983 --message '$vibelens'
```

The final user instruction freezes this round; do not restart the application in this frozen trial. `final-view.json` and `control-budget-audit.json` retain the real large response/evidence. A later authorized conversation can reproduce after normal service startup and real retained-event accumulation.

## Cause and ownership
`observer_runtime/bo_observer/control/cli.py:27-32` enforces 8,388,608 bytes. Activation at lines 60-64 unconditionally loads the whole `/api/view` just to establish project identity. Non-activation commands also use this full view; the existing snapshot option does not apply to activation. Normal legal event accumulation therefore disables conversation control. This is a shared control-interface functional defect, separate from the application, recorder, renderer and corrected test-driver mistakes.

Do not clear events, fabricate a small live response, raise this trial's limit, call lower-level authorization directly, or modify managed files. Repair the canonical transport/metadata boundary with bounded reads and intact project/conversation validation; regress large normal views and wrong-project responses. Then use the normal upgrade interface in a newly authorized continuation.

## Evidence and acceptance boundary
- `activation-current.command.json`, `.stdout.log`, `.stderr.log`: exact real failure.
- `control-budget-audit.json`: actual response size/hash, current build/binding/health, canonical parity and zero observer-induced business events.
- `final-view.json`, `final-recordings.json`, `raw-recording-*.json`: retained runtime evidence.
- Current candidate `e519b732dc99889a0ec65ecb51e637c3492c510e1d688b050450df267731e77d`; runtime build `fc5642726c7ef64bc86c122afe3135de439e19b95d4ba2da65a34cc46b680538`.
- Four normal reports and business/Web checks pass within the coverage below. **No accept or final accepted check was executed.**
