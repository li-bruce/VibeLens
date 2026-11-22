# P7 UI follow-up: replay space and resource diagnostics

## Diagnosed before implementation

| ID | Actual failure | Cause and owner | Planned correction | Regression |
| --- | --- | --- | --- | --- |
| R30-01 | At 1600 x 1000 the replay bar occupies x=360, y=100, width=880, height=86 inside a canvas starting at y=96: 75,680 square pixels overlap. | The shared viewer stylesheet overrides normal flow with an absolute position and a fixed top offset. Expanding step filters also consumes canvas space. Both renderers share this DOM. | Reserve a compact replay dock outside the graph; bound expanded filters; keep controls usable with the Timeline. | Measure control/canvas bounds, hit targets and render sizes in 2D/3D, English/Chinese, with Timeline and filters open/closed; exercise playback and return to live. |
| R30-02 | Chromium requests `http://127.0.0.1:8925/favicon.ico`, which returns 404. The viewer at port 8926 has no failed resource response. | The trial application's HTML declares no icon, and its Express static directory contains no default icon. The previous smoke retained only the console message, losing its resource URL. | Supply the missing application-owned static icon. Capture request URL, response status, resource type and console location in reusable browser checks. | A fresh browser context loads the real app without 404; unrelated missing resources must still return 404. Check viewer assets and lazy 3D resources separately. |

The existing app, recording and chats are reused. No new trial conversation is
created. Old P7 receipts and immutable installed providers remain unchanged. UI
regressions do not replace the existing native/business acceptance or claim a new
business implementation has been accepted.

Initial browser reconnaissance using network-idle did not finish because these
pages maintain background traffic. It was interrupted without a product result.
The diagnostic retry waits for actual DOM/recording readiness and records each
page separately. `before/diagnosis.json` and screenshots preserve the observed
failures, including the precise favicon response and replay geometry.

## Repair and retest

Both issues are resolved in the maintained source. The installed repair29
provider remains frozen; the viewer regression serves the maintained assets with
unchanged recordings through the existing read-only recording fixture.

- **R30-01:** one normal-flow replay dock serves both renderers. The main controls
  share a compact row; the optional step list scrolls within a bounded area. The
  Timeline yields space when filters open. Its maximized position follows the
  measured dock height. The resize observer is disconnected with the viewer.
- **R30-02:** the application now serves its own `public/favicon.ico` through its
  existing Express static route. No business source or observer route changed.
  `application/build_icon.py` reproduces the included icon using the Python
  standard library. The retained live app at port 8925 serves this exact asset.
- `tools/browser_resource_diagnostics.mjs` captures Chromium network responses,
  failed requests, console locations and page exceptions. It explicitly waits
  for CDP delivery: completion of a page fetch can precede its diagnostic event.
- Skill iteration guidance now requires specific resource evidence, lazy 3D
  checks, unobscured replay controls and actual page readiness. CI runs the new
  replay workspace regression and retains its artifacts.

| Check | Result | Receipt |
| --- | --- | --- |
| Same layout regression against frozen repair29 assets | Fails with 75,680 square pixels of overlap | `layout-before/result.json` |
| Real app before the static icon | Fails on `/favicon.ico`, HTTP 404 | `resource-before/result.json` |
| First patched workspace run | All 32 layout cases pass; the diagnostic negative-control assertion races CDP delivery | `fixture-first/result.json` |
| Workspace after subscribing to the response before fetching | 32 cases pass, including expected missing-asset detection | `layout-after/result.json` |
| Actual P7 recording, 9,882 events | Same 32 cases pass, recording hash unchanged, zero business writes | `trial-recording-after/result.json` |
| Real app after the icon | Browser favicon HTTP 200; no failed initial resources or page exceptions; an unrelated missing file still returns 404 | `resource-after/result.json` |
| Existing Timeline regression | 12 groups pass: seek, keyboard, playback, held step, range/loop, transfer animation, persistence and return to live | `timeline-existing/result.json` |
| Existing changes-panel regression | 4 groups pass: English/Chinese, 2D/3D, drag/disclosure/locate | `changes-existing/result.json` |
| Maintained-source syntax and lint | Pass | `source-check.json` |
| Original P7 acceptance evidence | All 13 referenced receipts retain their recorded hashes; native source binding remains current | `integrity.json` |

The layout matrix covers 1600 x 1000 and 1280 x 720 desktop windows, English and
Chinese, 2D and 3D, Timeline open/closed and step filters open/closed. It checks
actual bounding boxes, pointer hit targets, horizontal overflow, maximum Timeline
placement, next-step and timed playback. The smallest remaining graph height is
184.61 px with both optional panels open. Closing filters restores graph space.

All original JSON results and screenshots are in `evidence.zip`; selected images
are also available under `screenshots/`. `results.json` records checksums and the
scope of this repair. Old failed runs are retained, including the test-harness
race; none was overwritten with a passing result. No new dialogue was created,
and no complete native business trial was rerun for these static UI/asset fixes.

## Repeat the targeted checks

```powershell
$env:BO_BROWSER_EXECUTABLE = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:BO_REPLAY_WORKSPACE_EVIDENCE = '.validation/replay-workspace'
node tools/test_replay_workspace_browser.mjs

# Optional: point the same check at an existing real recording.
$env:BO_REPLAY_WORKSPACE_RECORDING = '<project>/bo_stategraph/data/recordings/<id>.json'
$env:BO_REPLAY_WORKSPACE_EVIDENCE = '.validation/replay-workspace-real'
node tools/test_replay_workspace_browser.mjs

node tools/test_trial_resources_browser.mjs http://127.0.0.1:8925/ .validation/app-resources '#login-form'
```

The application resource check is intentionally for pages using the browser's
default `/favicon.ico` request. The viewer already declares its own inline icon;
its resource checks live in the replay workspace regression. Missing-file negative
controls are separate from the clean initial-load results.
